import json

import pytest

from review_study.feed import merge_pages, parse_page
from review_study.summarize import monthly_counts, notification_sources, rating_counts, theme_counts
from review_study.themes import check_coverage, read_codes


def entry(rid, rating, updated="2026-10-01T10:00:00-07:00", version="12.8.0"):
    return {
        "id": {"label": rid},
        "updated": {"label": updated},
        "im:version": {"label": version},
        "im:rating": {"label": str(rating)},
        "title": {"label": "t"},
        "content": {"label": "some words here"},
    }


APP_ENTRY = {"id": {"label": "716979741"}, "title": {"label": "Whova"}}


def test_parse_page_skips_the_app_entry():
    text = json.dumps({"feed": {"entry": [APP_ENTRY, entry("1", 5), entry("2", 1)]}})
    rows = parse_page(text)
    assert [r["review_id"] for r in rows] == ["1", "2"]
    assert rows[1]["rating"] == 1


def test_parse_page_accepts_a_single_entry_object():
    text = json.dumps({"feed": {"entry": entry("9", 3)}})
    assert [r["review_id"] for r in parse_page(text)] == ["9"]


def test_parse_page_with_no_entries():
    assert parse_page(json.dumps({"feed": {}})) == []


def test_merge_pages_drops_a_review_seen_on_an_earlier_page():
    page1 = parse_page(json.dumps({"feed": {"entry": [entry("1", 5), entry("2", 4)]}}))
    page2 = parse_page(json.dumps({"feed": {"entry": [entry("2", 4), entry("3", 1)]}}))
    assert [r["review_id"] for r in merge_pages([page1, page2])] == ["1", "2", "3"]


def write_codes(tmp_path, rows):
    path = tmp_path / "codes.csv"
    lines = ["review_id,rating,themes,notification_source,summary"] + rows
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def test_read_codes_splits_themes(tmp_path):
    codes = read_codes(write_codes(tmp_path, ["1,1,notifications;agenda,whova,x", "2,3,navigation,,y"]))
    assert codes[0]["themes"] == ["notifications", "agenda"]
    assert codes[1]["notification_source"] == ""


@pytest.mark.parametrize("row, message", [
    ("1,1,spam,,x", "not in the codebook"),
    ("1,1,,,x", "no theme"),
    ("1,1,none;agenda,,x", "cannot be combined"),
    ("1,1,notifications,,x", "needs a source"),
    ("1,1,agenda,whova,x", "not coded notifications"),
])
def test_read_codes_refuses_a_bad_row(tmp_path, row, message):
    with pytest.raises(ValueError, match=message):
        read_codes(write_codes(tmp_path, [row]))


def test_read_codes_refuses_a_duplicate(tmp_path):
    with pytest.raises(ValueError, match="coded twice"):
        read_codes(write_codes(tmp_path, ["1,1,agenda,,x", "1,1,agenda,,x"]))


REVIEWS = [
    {"review_id": "1", "rating": "1", "updated": "2026-09-30T23:00:00-07:00"},
    {"review_id": "2", "rating": "3", "updated": "2026-10-01T08:00:00-07:00"},
    {"review_id": "3", "rating": "5", "updated": "2026-10-02T08:00:00-07:00"},
]


def test_check_coverage_passes_when_every_low_review_is_coded(tmp_path):
    codes = read_codes(write_codes(tmp_path, ["1,1,agenda,,x", "2,3,navigation,,y"]))
    check_coverage(REVIEWS, codes)


def test_check_coverage_names_a_missing_review(tmp_path):
    codes = read_codes(write_codes(tmp_path, ["1,1,agenda,,x"]))
    with pytest.raises(ValueError, match=r"missing \['2'\]"):
        check_coverage(REVIEWS, codes)


def test_check_coverage_names_a_code_for_a_high_rated_review(tmp_path):
    codes = read_codes(write_codes(tmp_path, ["1,1,agenda,,x", "2,3,navigation,,y", "3,5,agenda,,z"]))
    with pytest.raises(ValueError, match=r"extra \['3'\]"):
        check_coverage(REVIEWS, codes)


def test_check_coverage_catches_a_wrong_rating(tmp_path):
    codes = read_codes(write_codes(tmp_path, ["1,2,agenda,,x", "2,3,navigation,,y"]))
    with pytest.raises(ValueError, match="differs from the feed"):
        check_coverage(REVIEWS, codes)


def test_counts(tmp_path):
    codes = read_codes(write_codes(tmp_path, [
        "1,1,notifications;agenda,whova,x",
        "2,3,notifications,unspecified,y",
    ]))
    assert rating_counts(REVIEWS) == {1: 1, 2: 0, 3: 1, 4: 0, 5: 1}
    themes = theme_counts(codes)
    assert list(themes.items())[:2] == [("notifications", 2), ("agenda", 1)]
    assert themes["privacy"] == 0
    assert notification_sources(codes) == {"unspecified": 1, "whova": 1}


def test_monthly_counts_use_the_feed_timestamp_month():
    # 23:00 Pacific on 30 September is already 1 October in UTC; the feed's own month is kept.
    assert monthly_counts(REVIEWS) == {"2026-09": 1, "2026-10": 2}
