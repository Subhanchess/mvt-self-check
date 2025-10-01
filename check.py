from __future__ import annotations

import csv
import os
import re
from pathlib import Path
from typing import Callable, Iterable, List, Optional, Tuple

import requests
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

EMAIL_TO = os.getenv("EMAIL_TO")
MAILGUN_DOMAIN = os.getenv("MAILGUN_DOMAIN")
MAILGUN_KEY = os.getenv("MAILGUN_KEY")

STATUS_KEYWORDS = [
    "application open",
    "applications open",
    "application closed",
    "applications closed",
    "başvuru açık",
    "başvurular açık",
    "başvuru kapandı",
    "başvurular kapandı",
]

CSV_FIELDS = ["url", "selector_or_hint", "last_seen"]

MONTHS = {
    # tr
    "ocak": 1, "subat": 2, "şubat": 2, "mart": 3, "nisan": 4, "mayis": 5, "mayıs": 5,
    "haziran": 6, "temmuz": 7, "agustos": 8, "ağustos": 8, "eylul": 9, "eylül": 9,
    "ekim": 10, "kasim": 11, "kasım": 11, "aralik": 12, "aralık": 12,
    # en
    "jan": 1, "january": 1, "feb": 2, "february": 2, "mar": 3, "march": 3,
    "apr": 4, "april": 4, "may": 5, "jun": 6, "june": 6, "jul": 7, "july": 7,
    "aug": 8, "august": 8, "sep": 9, "sept": 9, "september": 9,
    "oct": 10, "october": 10, "nov": 11, "november": 11, "dec": 12, "december": 12,
}

NUMERIC_DATE_RE = re.compile(r"\b([0-3]?\d)[.\-/](0?[1-9]|1[0-2])[.\-/](\d{4})\b")
NAME_DATE_RE = re.compile(
    r"\b([0-3]?\d)\s+([A-Za-zÇĞİÖŞÜçğıöşüÂâÎîÛû]+)\s+(\d{4})\b", re.IGNORECASE
)

HINT_WINDOW_BEFORE = 60
HINT_WINDOW_AFTER = 200


def _session() -> requests.Session:
    s = requests.Session()
    s.headers.update({"User-Agent": "mvt-self-check/1.0 (+github)"})
    retry = Retry(
        total=3, backoff_factor=0.5,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=("GET",),
    )
    s.mount("http://", HTTPAdapter(max_retries=retry))
    s.mount("https://", HTTPAdapter(max_retries=retry))
    return s


def _zero2(n: int) -> str:
    return f"{n:02d}"


def _normalize_name_date(day: str, mon: str, year: str) -> Optional[str]:
    key = mon.strip().lower().replace("ı", "i").replace("ş", "s").replace("ğ", "g").replace("ç", "c").replace("ö", "o").replace("ü", "u")
    mnum = MONTHS.get(key)
    if not mnum:
        # bazı İngilizce kısaltmalar noktalı gelebilir: "Sept."
        key = key.strip(".")
        mnum = MONTHS.get(key)
    if not mnum:
        return None
    d = int(day)
    return f"{_zero2(d)}.{_zero2(mnum)}.{year}"


def _find_dates(text: str) -> List[str]:
    found: List[str] = []
    for d, m, y in NUMERIC_DATE_RE.findall(text):
        found.append(f"{_zero2(int(d))}.{_zero2(int(m))}.{y}")
    for d, name, y in NAME_DATE_RE.findall(text):
        norm = _normalize_name_date(d, name, y)
        if norm:
            found.append(norm)
    return found


def _looks_like_selector(candidate: str) -> bool:
    c = (candidate or "").strip()
    if not c:
        return False
    # Kasıtlı: basit tag adları regular modda selector sayılmasın.
    return any(ch in c for ch in "#.>[:") and not c.isspace()


def _safe_select(soup: BeautifulSoup, selector: str) -> List[str]:
    sel = (selector or "").strip()
    if not sel:
        return []
    try:
        return [el.get_text(" ", strip=True) for el in soup.select(sel)]
    except Exception:
        return []


def extract_candidate(html: str, selector_or_hint: str, snapshot_mode: bool = False) -> str:
    """Sayfadan tarih veya durum metni çıkarır; yoksa boş döner."""
    soup = BeautifulSoup(html or "", "lxml")

    if snapshot_mode:
        # Neden: snapshot'ta düz tag adları CSS olarak kabul edilsin.
        chunks = _safe_select(soup, selector_or_hint) or [soup.get_text(" ", strip=True)]
        for chunk in chunks:
            dates = _find_dates(chunk)
            if dates:
                return dates[0]
        return ""

    # Regular mod
    text = soup.get_text(" ", strip=True)
    hay = text
    hint = (selector_or_hint or "").strip()

    if _looks_like_selector(hint):
        chunks = _safe_select(soup, hint)
        for chunk in chunks:
            dates = _find_dates(chunk)
            if dates:
                return dates[0]
    else:
        idx = hay.lower().find(hint.lower()) if hint else -1
        if idx != -1:
            start = max(0, idx - HINT_WINDOW_BEFORE)
            end = min(len(hay), idx + len(hint) + HINT_WINDOW_AFTER)
            window = hay[start:end]
            dates = _find_dates(window)
            if dates:
                return dates[0]

    # Son çare: tüm metinde ara
    dates = _find_dates(hay)
    if dates:
        return dates[0]

    # Hiç tarih yoksa status keyword yakala
    lower = hay.lower()
    for kw in STATUS_KEYWORDS:
        if kw in lower:
            return kw
    return ""


def fetch_candidate(url: str, selector_or_hint: str = "", snapshot_mode: bool = False) -> str:
    with _session() as s:
        r = s.get(url, timeout=20)
        if r.status_code != 200:
            raise RuntimeError(f"http {r.status_code}")
        return extract_candidate(r.text, selector_or_hint, snapshot_mode=snapshot_mode)


def load_links(path: str | Path = "links.csv") -> List[dict]:
    p = Path(path)
    if not p.exists():
        return []
    out: List[dict] = []
    with p.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            out.append({k: (row.get(k, "") or "").strip() for k in CSV_FIELDS})
    return out


def save_links(rows: Iterable[dict], path: str | Path = "links.csv") -> None:
    p = Path(path)
    with p.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDS)
        writer.writeheader()
        for r in rows:
            writer.writerow({k: (r.get(k, "") or "") for k in CSV_FIELDS})


def notify(url: str, old: str, new: str) -> None:
    """Mailgun varsa gönder; aksi halde sessiz geç."""
    if not (EMAIL_TO and MAILGUN_DOMAIN and MAILGUN_KEY):
        return
    data = {
        "from": f"MVT Self-Check <bot@{MAILGUN_DOMAIN}>",
        "to": EMAIL_TO,
        "subject": "Takip değişikliği",
        "text": f"{url}\nold: {old}\nnew: {new}",
    }
    requests.post(
        f"https://api.mailgun.net/v3/{MAILGUN_DOMAIN}/messages",
        auth=("api", MAILGUN_KEY),
        data=data,
        timeout=20,
    )


def scan_links(links: List[dict], on_change: Callable[[str, str, str], None] | None = None) -> Tuple[int, List[dict]]:
    changed = 0
    changed_rows: List[dict] = []
    for row in links:
        url = row.get("url", "")
        hint = row.get("selector_or_hint", "")
        try:
            latest = fetch_candidate(url, hint)
        except Exception as exc:
            latest = f"ERROR: {exc}"
        old = row.get("last_seen", "")
        if latest and latest != old:
            row["last_seen"] = latest
            changed += 1
            changed_rows.append(row)
            if on_change:
                on_change(url, old, latest)
    return changed, changed_rows


def main() -> None:
    rows = load_links("links.csv")
    if not rows:
        print("no links.csv entries")
        return
    changed, _ = scan_links(rows, on_change=notify)
    if changed:
        save_links(rows, "links.csv")
    print(f"checked {len(rows)} link(s), changed: {changed}")


if __name__ == "__main__":
    main()
