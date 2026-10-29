"""Turn data/reviews.csv and the hand codes in data/codes.csv into results/summary.json and the charts.

Writes:
  results/summary.json        every number the README quotes
  docs/figures/themes.png     themes of the 1-3 star reviews (matplotlib, for the README)
  docs/index.html             the same charts plus monthly volume, interactive (plotly)
"""
import csv
import json
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import plotly.graph_objects as go  # noqa: E402
from plotly.subplots import make_subplots  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from review_study.summarize import monthly_counts, notification_sources, rating_counts, theme_counts  # noqa: E402
from review_study.themes import check_coverage, read_codes  # noqa: E402

LABELS = {
    "notifications": "Notifications and promotion",
    "navigation": "Confusing or overwhelming",
    "connectivity": "Connection, VPN or live-feature failures",
    "agenda": "Finding and tracking sessions",
    "access": "Getting into the event",
    "platforms": "Missing or blocked platform",
    "privacy": "Privacy and permissions",
    "accessibility": "Text size and display",
    "other": "One-off requests",
    "none": "No reason given",
}


def main():
    with open(ROOT / "data" / "reviews.csv", newline="", encoding="utf-8") as fh:
        reviews = list(csv.DictReader(fh))
    codes = read_codes(ROOT / "data" / "codes.csv")
    check_coverage(reviews, codes)
    manifest = json.loads((ROOT / "data" / "MANIFEST.json").read_text(encoding="utf-8"))

    summary = {
        "fetched_at_utc": manifest["fetched_at_utc"],
        "reviews": len(reviews),
        "first_review": min(r["updated"] for r in reviews),
        "last_review": max(r["updated"] for r in reviews),
        "ratings": rating_counts(reviews),
        "coded_reviews_rated_1_to_3": len(codes),
        "themes": theme_counts(codes),
        "notification_sources": notification_sources(codes),
        "reviews_per_month": monthly_counts(reviews),
    }
    (ROOT / "results").mkdir(exist_ok=True)
    (ROOT / "results" / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")

    themes = [(t, n) for t, n in summary["themes"].items() if n > 0]
    names = [LABELS[t] for t, _ in themes][::-1]
    values = [n for _, n in themes][::-1]

    figures = ROOT / "docs" / "figures"
    figures.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(8, 4.2))
    ax.barh(names, values, color="#4c72b0")
    for y, v in enumerate(values):
        ax.text(v + 0.2, y, str(v), va="center", fontsize=9)
    ax.set_xlabel(f"reviews (of {len(codes)} rated 1-3 stars; a review can carry more than one theme)")
    ax.set_title(f"What the 1-3 star reviews among the newest {len(reviews)} are about")
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    fig.savefig(figures / "themes.png", dpi=150)
    plt.close(fig)

    months = summary["reviews_per_month"]
    sources = summary["notification_sources"]
    page = make_subplots(
        rows=3, cols=1, vertical_spacing=0.12,
        subplot_titles=(
            f"Themes of the {len(codes)} reviews rated 1-3 stars",
            "Who sent the unwanted messages, in the reviews coded notifications",
            f"All {len(reviews)} reviews, per month (US Pacific)",
        ),
    )
    page.add_trace(go.Bar(x=values, y=names, orientation="h", text=values, textposition="outside"), row=1, col=1)
    page.add_trace(go.Bar(x=list(sources.values()), y=[f"{k}" for k in sources], orientation="h",
                          text=list(sources.values()), textposition="outside"), row=2, col=1)
    page.add_trace(go.Bar(x=list(months), y=list(months.values())), row=3, col=1)
    page.update_layout(height=1100, showlegend=False, template="simple_white",
                       title=f"Whova App Store reviews, fetched {manifest['fetched_at_utc'][:10]}")
    (ROOT / "docs").mkdir(exist_ok=True)
    page.write_html(ROOT / "docs" / "index.html", include_plotlyjs="cdn", full_html=True)

    print(json.dumps({k: summary[k] for k in ("reviews", "ratings", "themes", "notification_sources")}, indent=2))


if __name__ == "__main__":
    main()
