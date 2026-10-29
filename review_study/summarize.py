"""The counts behind every number in the README."""
from collections import Counter

from review_study.themes import CODEBOOK


def rating_counts(reviews):
    counts = Counter(int(r["rating"]) for r in reviews)
    return {stars: counts.get(stars, 0) for stars in range(1, 6)}


def theme_counts(codes):
    """Reviews per theme, largest first; a review with two themes counts once in each."""
    counts = Counter(t for c in codes for t in c["themes"])
    return dict(sorted(((t, counts.get(t, 0)) for t in CODEBOOK), key=lambda kv: (-kv[1], kv[0])))


def notification_sources(codes):
    counts = Counter(c["notification_source"] for c in codes if "notifications" in c["themes"])
    return dict(sorted(counts.items()))


def monthly_counts(reviews):
    """Reviews per calendar month in the time zone the feed's timestamps carry (US Pacific)."""
    counts = Counter(r["updated"][:7] for r in reviews)
    return dict(sorted(counts.items()))
