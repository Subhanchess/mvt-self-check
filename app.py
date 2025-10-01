"""Simple Flask UI for managing tracked links."""
from __future__ import annotations

import os
from pathlib import Path

from flask import Flask, flash, redirect, render_template, request, url_for

from check import fetch_candidate, load_links, save_links, scan_links

app = Flask(__name__)
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "change-this-key")

CSV_PATH = Path(os.getenv("CSV_PATH", "links.csv"))


def _ensure_csv() -> None:
    if not CSV_PATH.exists():
        save_links([], CSV_PATH)  # why: create file on first run


@app.route("/")
def index():
    _ensure_csv()
    links = load_links(CSV_PATH)
    return render_template("links.html", links=links)


@app.post("/add")
def add_link():
    _ensure_csv()
    url = (request.form.get("url") or "").strip()
    hint = (request.form.get("selector_or_hint") or "").strip()
    if not url:
        flash("Lütfen bir URL girin.", "error")
        return redirect(url_for("index"))

    last_seen = ""
    try:
        last_seen = fetch_candidate(url, hint) if hint else fetch_candidate(url, "")
        if last_seen:
            flash("Link eklendi ve mevcut bilgi kaydedildi.", "success")
        else:
            flash("Link eklendi fakat tarih/durum bulunamadı.", "warning")
    except Exception as exc:  # noqa: BLE001 - surfacing to user
        flash(f"Link kaydedildi ancak içerik alınamadı: {exc}", "error")

    links = load_links(CSV_PATH)
    links.append({"url": url, "selector_or_hint": hint, "last_seen": last_seen})
    save_links(links, CSV_PATH)
    return redirect(url_for("index"))


@app.post("/delete")
def delete_link():
    _ensure_csv()
    url = (request.form.get("url") or "").strip()
    links = [r for r in load_links(CSV_PATH) if r.get("url") != url]
    save_links(links, CSV_PATH)
    flash("Silindi.", "ok")
    return redirect(url_for("index"))


@app.post("/scan")
def scan():
    _ensure_csv()
    links = load_links(CSV_PATH)
    changed, rows = scan_links(links)
    if changed:
        save_links(links, CSV_PATH)
        flash(f"{changed} kayıt güncellendi.", "ok")
    else:
        flash("Değişiklik yok.", "ok")
    return redirect(url_for("index"))


if __name__ == "__main__":
    app.run(debug=True)
