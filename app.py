"""Simple Flask UI for managing tracked grant links.

The web interface wraps the CSV-based workflow used by ``check.py``.
It allows operators to add/remove URLs without touching the CSV by hand
and to trigger manual scans when needed.
"""

from __future__ import annotations

from pathlib import Path
from typing import List

from flask import Flask, flash, redirect, render_template, request, url_for

from check import fetch_candidate, load_links, save_links, scan_links

app = Flask(__name__)
app.config["SECRET_KEY"] = "change-this-key"
CSV_PATH = Path("links.csv")


def _ensure_csv_exists() -> None:
    if not CSV_PATH.exists():
        save_links([], CSV_PATH)


@app.route("/")
def index():
    _ensure_csv_exists()
    links = load_links(CSV_PATH)
    return render_template("links.html", links=links)


@app.post("/add")
def add_link():
    _ensure_csv_exists()
    url = (request.form.get("url") or "").strip()
    hint = (request.form.get("selector_or_hint") or "").strip()
    if not url:
        flash("Lütfen bir URL girin.", "error")
        return redirect(url_for("index"))

    links = load_links(CSV_PATH)
    if any(link.get("url") == url for link in links):
        flash("Bu URL zaten takip ediliyor.", "warning")
        return redirect(url_for("index"))

    last_seen = ""
    try:
        last_seen = fetch_candidate(url, hint)
        if last_seen:
            flash("Link eklendi ve mevcut deadline bilgisi kaydedildi.", "success")
        else:
            flash(
                "Link eklendi fakat deadline bilgisi bulunamadı. Yine de takip edilecek.",
                "warning",
            )
    except RuntimeError as exc:
        flash(f"Link kaydedildi ancak içerik alınamadı: {exc}", "error")

    links.append({"url": url, "selector_or_hint": hint, "last_seen": last_seen})
    save_links(links, CSV_PATH)
    return redirect(url_for("index"))


@app.post("/delete")
def delete_link():
    _ensure_csv_exists()
    url = (request.form.get("url") or "").strip()
    links = load_links(CSV_PATH)
    filtered: List[dict] = [link for link in links if link.get("url") != url]
    if len(filtered) == len(links):
        flash("Silinecek link bulunamadı.", "error")
    else:
        save_links(filtered, CSV_PATH)
        flash("Link silindi.", "success")
    return redirect(url_for("index"))


@app.post("/scan")
def manual_scan():
    _ensure_csv_exists()
    links = load_links(CSV_PATH)
    if not links:
        flash("Takip edilen link yok.", "warning")
        return redirect(url_for("index"))

    updated, changed = scan_links(links)
    save_links(updated, CSV_PATH)
    if changed:
        flash(
            "Tarama tamamlandı, değişiklik bulunan linkler için e-posta gönderildi.",
            "success",
        )
    else:
        flash("Tarama tamamlandı, değişiklik bulunamadı.", "info")
    return redirect(url_for("index"))


if __name__ == "__main__":
    app.run(debug=True)
