"""The codebook for the 1-3 star reviews, and the checks that keep the hand codes honest.

A review can carry more than one theme. Every theme is defined by what the reviewer says, not by
what I think caused it.
"""
import csv

CODEBOOK = {
    "notifications": "the volume, timing or source of push notifications, in-app messages, emails or promotion",
    "navigation": "the app is confusing, overwhelming or hard to find one's way around in, without a single feature named",
    "agenda": "finding, filtering or keeping track of sessions in the event's agenda",
    "connectivity": "the app will not connect, breaks behind a VPN, loses data or a live feature fails",
    "access": "getting into an event: invitation codes, linking a registration to an account, finding the event",
    "platforms": "the app is missing or blocked on a device: macOS, the web app on an iPad, the web without the app",
    "privacy": "what the app does with personal data or why it asks for a permission",
    "accessibility": "text size, contrast or display settings",
    "other": "a single specific request that fits no theme above",
    "none": "no reason given, or text that praises the app under a low rating",
}

# Who sent the unwanted messages, for reviews coded "notifications".
SOURCES = {
    "whova": "the reviewer says the messages come from Whova itself (tips on using the app, app promotion, marketing)",
    "unspecified": "the reviewer does not say who sent them, or names someone other than Whova",
}


def read_codes(path):
    """Read data/codes.csv and check every theme and source against the codebook."""
    with open(path, newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    seen = set()
    for row in rows:
        rid = row["review_id"]
        if rid in seen:
            raise ValueError(f"review {rid} is coded twice")
        seen.add(rid)
        themes = [t.strip() for t in row["themes"].split(";") if t.strip()]
        if not themes:
            raise ValueError(f"review {rid} has no theme")
        unknown = [t for t in themes if t not in CODEBOOK]
        if unknown:
            raise ValueError(f"review {rid}: theme(s) not in the codebook: {unknown}")
        if "none" in themes and len(themes) > 1:
            raise ValueError(f"review {rid}: 'none' cannot be combined with another theme")
        source = row.get("notification_source", "").strip()
        if "notifications" in themes and source not in SOURCES:
            raise ValueError(f"review {rid}: a notifications code needs a source in {sorted(SOURCES)}")
        if "notifications" not in themes and source:
            raise ValueError(f"review {rid}: a source is set but the review is not coded notifications")
        row["themes"] = themes
        row["notification_source"] = source
    return rows


def check_coverage(reviews, codes, max_rating=3):
    """Every review rated max_rating or lower has exactly one code row, and no code row points elsewhere."""
    low_ids = {r["review_id"] for r in reviews if int(r["rating"]) <= max_rating}
    coded_ids = {c["review_id"] for c in codes}
    missing = sorted(low_ids - coded_ids)
    extra = sorted(coded_ids - low_ids)
    if missing or extra:
        raise ValueError(f"codes do not match the low-rated reviews: missing {missing}, extra {extra}")
    rating = {r["review_id"]: int(r["rating"]) for r in reviews}
    wrong = sorted(c["review_id"] for c in codes if int(c["rating"]) != rating[c["review_id"]])
    if wrong:
        raise ValueError(f"the rating in the codes differs from the feed for {wrong}")
