import csv
import os
import re
import sys
import time

import requests
from bs4 import BeautifulSoup

EMAIL_TO = os.getenv("EMAIL_TO")
MAILGUN_DOMAIN = os.getenv("MAILGUN_DOMAIN")
MAILGUN_KEY = os.getenv("MAILGUN_KEY")

DATE_RE = re.compile(
    r"\b(3[01]|[12][0-9]|0?[1-9])[\.\-\/\s](1[0-2]|0?[1-9]|ocak|şubat|mart|nisan|mayıs|haziran|temmuz|ağustos|eylül|ekim|kasım|aralık|jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[\.\-\/\s](20\d{2})\b|\b(20\d{2})[\.\-\/\s](1[0-2]|0?[1-9])[\.\-\/\s](3[01]|[12][0-9]|0?[1-9])\b",
    re.I,
)

def extract_candidate(html, selector_or_hint):
    soup = BeautifulSoup(html, "lxml")
    text = soup.get_text("\n", strip=True)
    if selector_or_hint and any(c in selector_or_hint for c in ".#[]:>"):
        try:
            nodes = soup.select(selector_or_hint)
            for n in nodes:
                m = DATE_RE.search(n.get_text(" ", strip=True))
                if m:
                    return m.group(0)
        except Exception:
            pass
    hint = (selector_or_hint or "").lower()
    lines = text.lower().splitlines()
    for line in lines:
        if (hint and hint in line) or ("deadline" in line) or ("son başvuru" in line) or (
            "application closes" in line
        ):
            m = DATE_RE.search(line)
            if m:
                return m.group(0)
    m = DATE_RE.search(text)
    return m.group(0) if m else ""

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
            sel = row.get("selector_or_hint", "").strip()
            last = row.get("last_seen", "").strip()
            try:
                r = requests.get(url, timeout=30, headers={"User-Agent": "Mozilla/5.0"})
                html = r.text
            except Exception as e:
                print(f"[ERR] {url}: {e}", file=sys.stderr)
                rows.append(row)
                continue
            cand = extract_candidate(html, sel)
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
