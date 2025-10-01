import csv
import os
import re
import sys
from typing import Callable, Iterable, List, Tuple

import requests
from bs4 import BeautifulSoup

EMAIL_TO = os.getenv("EMAIL_TO")
MAILGUN_DOMAIN = os.getenv("MAILGUN_DOMAIN")
MAILGUN_KEY = os.getenv("MAILGUN_KEY")

DATE_RE = re.compile(
    r"\b(3[01]|[12][0-9]|0?[1-9])[\.\-\/\s](1[0-2]|0?[1-9]|ocak|şubat|mart|nisan|mayıs|haziran|temmuz|ağustos|eylül|ekim|kasım|aralık|jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[\.\-\/\s](20\d{2})\b|\b(20\d{2})[\.\-\/\s](1[0-2]|0?[1-9])[\.\-\/\s](3[01]|[12][0-9]|0?[1-9])\b",
    re.I,
)


def _looks_like_selector(candidate):
    candidate = (candidate or "").strip()
    if not candidate:
        return False
    return any(c in candidate for c in ".#[]:>")


def _safe_select(soup, selector):
    selector = (selector or "").strip()
    if not selector:
        return []
    try:
        return soup.select(selector)
    except Exception:
        return []


STATUS_KEYWORDS = [
    "application closed",
    "applications closed",
    "application open",
    "applications open",
    "başvuru kapandı",
    "başvurular kapandı",
    "başvuru açık",
    "başvurular açık",
]

CSV_FIELDS = ["url", "selector_or_hint", "last_seen"]


def load_links(path: str = "links.csv") -> List[dict]:
    """Read tracked links from disk.

    The CSV file is optional; an empty list is returned when it does not
    exist. Every row contains the expected keys defined in ``CSV_FIELDS``.
    """

    if not os.path.exists(path):
        return []
    rows: List[dict] = []
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for raw in reader:
            row = {field: (raw.get(field, "") or "").strip() for field in CSV_FIELDS}
            rows.append(row)
    return rows


def save_links(rows: Iterable[dict], path: str = "links.csv") -> None:
    """Persist the given rows to disk."""

    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDS)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in CSV_FIELDS})


def extract_candidate(html, selector_or_hint, snapshot_mode=False):
    soup = BeautifulSoup(html, "lxml")
    text = soup.get_text("\n", strip=True)
    selector = (selector_or_hint or "").strip()
    if selector and (_looks_like_selector(selector) or snapshot_mode):
        nodes = _safe_select(soup, selector)
        for n in nodes:
            m = DATE_RE.search(n.get_text(" ", strip=True))
            if m:
                return m.group(0)
    hint = (selector_or_hint or "").lower()
    lines = text.lower().splitlines()
    for line in lines:
        if (hint and hint in line) or ("deadline" in line) or ("son başvuru" in line) or (
            "application closes" in line
        ):
            m = DATE_RE.search(line)
            if m:
                return m.group(0)
            for keyword in STATUS_KEYWORDS:
                if keyword in line:
                    return keyword
    m = DATE_RE.search(text)
    if m:
        return m.group(0)
    lower_text = text.lower()
    for keyword in STATUS_KEYWORDS:
        if keyword in lower_text:
            return keyword
    return ""


def fetch_candidate(url: str, selector_or_hint: str, *, snapshot_mode: bool = False) -> str:
    """Download ``url`` and extract the best matching deadline candidate.

    A ``RuntimeError`` is raised when the network request fails so callers can
    decide how to surface the problem (log, flash message, etc.).
    """

    try:
        response = requests.get(
            url,
            timeout=30,
            headers={"User-Agent": "Mozilla/5.0"},
        )
        html = response.text
    except Exception as exc:  # pragma: no cover - exercised via integration
        raise RuntimeError(str(exc)) from exc
    return extract_candidate(html, selector_or_hint, snapshot_mode=snapshot_mode)

def notify(url, old, new):
    subject = f"DEADLINE GÜNCELLENDİ: {url}"
    body = f"Bağlantı: {url}\nEski: {old or '(yok)'}\nYeni: {new or '(yok)'}\n"
    if MAILGUN_KEY and MAILGUN_DOMAIN and EMAIL_TO:
        requests.post(
            f"https://api.mailgun.net/v3/{MAILGUN_DOMAIN}/messages",
            auth=("api", MAILGUN_KEY),
            data={
                "from": f"Deadline Bot <bot@{MAILGUN_DOMAIN}>",
                "to": [EMAIL_TO],
                "subject": subject,
                "text": body,
            },
        )
    else:
        print("[WARN] Mail ayarı yok; stdout:")
        print(subject)
        print(body)


def scan_links(
    rows: Iterable[dict],
    *,
    snapshot_mode: bool = False,
    notifier: Callable[[str, str, str], None] = notify,
) -> Tuple[List[dict], bool]:
    """Return updated rows after scanning and whether anything changed."""

    updated_rows: List[dict] = []
    changed = False
    for row in rows:
        url = (row.get("url") or "").strip()
        sel = (row.get("selector_or_hint") or "").strip()
        last = (row.get("last_seen") or "").strip()
        try:
            cand = fetch_candidate(url, sel, snapshot_mode=snapshot_mode)
        except RuntimeError as exc:
            print(f"[ERR] {url}: {exc}", file=sys.stderr)
            updated_rows.append(dict(row))
            continue
        if cand != last:
            notifier(url, last, cand)
            row = dict(row)
            row["last_seen"] = cand
            changed = True
        updated_rows.append(dict(row))
    return updated_rows, changed

def main():
    rows = load_links()
    updated, changed = scan_links(rows)
    save_links(updated)
    print("[OK] scan done; changed=", changed)


if __name__ == "__main__":
    main()
