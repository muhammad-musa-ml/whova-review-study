"""Download the newest App Store reviews of the Whova app from Apple's public review feed.

Apple serves at most 10 pages of 50 reviews per country, newest first, with no account needed.
Writes:
  data/raw/page<N>.json   the pages as served (git-ignored: they hold review text and nicknames)
  data/raw/to_code.txt    the 1-3 star reviews in full, for reading and coding by hand (git-ignored)
  data/reviews.csv        one row per review: id, date, app version, rating, title and text length
  data/MANIFEST.json      when it ran, what came back, and a hash of every page
"""
import csv
import hashlib
import json
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from review_study.feed import merge_pages, parse_page  # noqa: E402

APP_ID = "716979741"  # Whova - Event & Conference App, US App Store
COUNTRY = "us"
PAGES = 10
URL = "https://itunes.apple.com/{country}/rss/customerreviews/page={page}/id={app}/sortby=mostrecent/json"

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"


def fetch(page):
    url = URL.format(country=COUNTRY, page=page, app=APP_ID)
    req = urllib.request.Request(url, headers={"User-Agent": "whova-review-study"})
    with urllib.request.urlopen(req, timeout=30) as r:
        if r.status != 200:
            raise RuntimeError(f"page {page}: HTTP {r.status}")
        return r.read()


def main():
    RAW.mkdir(parents=True, exist_ok=True)
    fetched_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    pages, hashes = [], {}
    for page in range(1, PAGES + 1):
        body = fetch(page)
        (RAW / f"page{page}.json").write_bytes(body)
        hashes[f"page{page}"] = hashlib.sha256(body).hexdigest()
        pages.append(parse_page(body.decode("utf-8")))
    rows = merge_pages(pages)
    if not rows:
        raise SystemExit("the feed returned no reviews")

    with open(ROOT / "data" / "reviews.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["review_id", "updated", "version", "rating", "title_words", "text_words"])
        for r in rows:
            w.writerow([r["review_id"], r["updated"], r["version"], r["rating"],
                        len(r["title"].split()), len(r["content"].split())])

    low = sorted((r for r in rows if r["rating"] <= 3), key=lambda r: r["updated"], reverse=True)
    with open(RAW / "to_code.txt", "w", encoding="utf-8") as fh:
        for r in low:
            fh.write(f"{r['review_id']} | {r['rating']} stars | v{r['version']} | {r['updated'][:10]}\n")
            fh.write(f"{r['title']}\n{r['content']}\n\n")

    manifest = {
        "source": URL.format(country=COUNTRY, page="<1-10>", app=APP_ID),
        "fetched_at_utc": fetched_at,
        "reviews": len(rows),
        "reviews_rated_1_to_3": len(low),
        "first_review": min(r["updated"] for r in rows),
        "last_review": max(r["updated"] for r in rows),
        "page_sha256": hashes,
    }
    (ROOT / "data" / "MANIFEST.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"{len(rows)} reviews ({len(low)} rated 1-3), {manifest['first_review']} to {manifest['last_review']}")


if __name__ == "__main__":
    main()
