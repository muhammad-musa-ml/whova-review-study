"""Read pages of Apple's public customer-review feed into one row per review."""
import json


def parse_page(text):
    """Return the reviews on one feed page as dicts. The app's own entry carries no rating and is skipped."""
    feed = json.loads(text).get("feed", {})
    entries = feed.get("entry", [])
    if isinstance(entries, dict):  # a page holding a single entry
        entries = [entries]
    rows = []
    for e in entries:
        if "im:rating" not in e:
            continue
        rows.append({
            "review_id": e["id"]["label"],
            "updated": e["updated"]["label"],
            "version": e["im:version"]["label"],
            "rating": int(e["im:rating"]["label"]),
            "title": e["title"]["label"],
            "content": e["content"]["label"],
        })
    return rows


def merge_pages(pages):
    """Join parsed pages, keeping the first copy of any review that shows up on two pages."""
    seen = set()
    rows = []
    for page in pages:
        for row in page:
            if row["review_id"] in seen:
                continue
            seen.add(row["review_id"])
            rows.append(row)
    return rows
