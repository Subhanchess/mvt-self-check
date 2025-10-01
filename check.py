import csv
import hashlib
import os
import re
import sys
import time
from typing import Iterable, Tuple

import requests
from bs4 import BeautifulSoup

EMAIL_TO = os.getenv("EMAIL_TO")
MAILGUN_DOMAIN = os.getenv("MAILGUN_DOMAIN")
MAILGUN_KEY = os.getenv("MAILGUN_KEY")

DATE_RE = re.compile(
    r"\b(3[01]|[12][0-9]|0?[1-9])[\.\-\/\s](1[0-2]|0?[1-9]|ocak|şubat|mart|nisan|mayıs|haziran|temmuz|ağustos|eylül|ekim|kasım|aralık|jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[\.\-\/\s](20\d{2})\b|\b(20\d{2})[\.\-\/\s](1[0-2]|0?[1-9])[\.\-\/\s](3[01]|[12][0-9]|0?[1-9])\b",
    re.I,
)

SELECTOR_HINT_CHARS = ".#[]:>"


def _looks_like_selector(text_hint: str) -> bool:
    return any(c in text_hint for c in SELECTOR_HINT_CHARS)


def _safe_select(soup: BeautifulSoup, selector: str):
    try:
        return soup.select(selector)
    except Exception:
        return []


def _hash_snapshot(text: str) -> str:
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
    return f"snapshot:sha256:{digest}"


def _normalize_whitespace(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def _node_texts(nodes: Iterable) -> Tuple[str, str]:
    extracted = [n.get_text("\n", strip=True) for n in nodes]
    joined = "\n".join(extracted)
    return joined, joined.lower()


def _search_date(text: str) -> str:
    match = DATE_RE.search(text)
    return match.group(0) if match else ""


def extract_candidate(html, selector_or_hint, snapshot_mode=False):
    soup = BeautifulSoup(html, "lxml")
    page_text = soup.get_text("\n", strip=True)
    nodes = []

    if selector_or_hint and _looks_like_selector(selector_or_hint):
        nodes = _safe_select(soup, selector_or_hint)
        for node in nodes:
            node_text = node.get_text(" ", strip=True)
            found = _search_date(node_text)
            if found:
                return found

    hint = (selector_or_hint or "").lower()
    lowered_page = page_text.lower()
    lines = lowered_page.splitlines()

    for line in lines:
        if (
            (hint and hint in line)
            or ("deadline" in line)
            or ("son başvuru" in line)
            or ("application closes" in line)
        ):
            found = _search_date(line)
            if found:
                return found

    found = _search_date(page_text)
    if found:
        return found

    if snapshot_mode:
        snapshot_text = ""
        if nodes:
            snapshot_text, _ = _node_texts(nodes)
        if not snapshot_text:
            snapshot_text = page_text
        normalized = _normalize_whitespace(snapshot_text)
        if normalized:
            return _hash_snapshot(normalized)

    return ""

def notify(url, old, new):
    subject = f"DEADLINE GÜNCELLENDİ: {url}"
    body = f"Bağlantı: {url}\nEski: {old or '(yok)'}\nYeni: {new}\n"
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

def main():
    rows = []
    changed = False
    with open("links.csv", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            url = row["url"].strip()
            sel_raw = row.get("selector_or_hint", "").strip()
            sel_lower = sel_raw.lower()
            snapshot_mode = False
            if sel_lower.startswith("snapshot:"):
                snapshot_mode = True
                sel = sel_raw[len("snapshot:") :].strip()
            elif sel_lower == "snapshot":
                snapshot_mode = True
                sel = ""
            else:
                sel = sel_raw
            last = row.get("last_seen", "").strip()
            try:
                r = requests.get(url, timeout=30, headers={"User-Agent": "Mozilla/5.0"})
                html = r.text
            except Exception as e:
                print(f"[ERR] {url}: {e}", file=sys.stderr)
                rows.append(row)
                continue
            cand = extract_candidate(html, sel, snapshot_mode=snapshot_mode)
            if cand and cand != last:
                notify(url, last, cand)
                row["last_seen"] = cand
                changed = True
            rows.append(row)
    with open("links.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["url", "selector_or_hint", "last_seen"])
        writer.writeheader()
        writer.writerows(rows)
    print("[OK] scan done; changed=", changed)


if __name__ == "__main__":
    main()
