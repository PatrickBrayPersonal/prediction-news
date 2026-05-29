import time
from unittest.mock import MagicMock, patch

from prediction_news.articles.rss import fetch_articles


def _make_entry(title: str, link: str, summary: str = "", published: bool = True) -> dict:
    entry = {"title": title, "link": link, "summary": summary}
    if published:
        entry["published_parsed"] = time.gmtime()
    return entry


def _make_old_entry(title: str, link: str, summary: str = "") -> dict:
    import calendar
    from datetime import datetime, timedelta, timezone

    old_dt = datetime.now(timezone.utc) - timedelta(hours=72)
    return {
        "title": title,
        "link": link,
        "summary": summary,
        "published_parsed": time.gmtime(calendar.timegm(old_dt.timetuple())),
    }


def _mock_parse(entries: list[dict]) -> MagicMock:
    feed = MagicMock()
    feed.get.return_value = entries
    return feed


def test_fetch_articles_returns_source_objects():
    entry = _make_entry("Democrats lead in polls", "https://reuters.com/1", "Poll shows Democrats ahead.")
    with patch("prediction_news.articles.rss.feedparser.parse", return_value=_mock_parse([entry])):
        results = fetch_articles(["democrats"], "politics")
    assert len(results) == 1
    assert results[0].type == "rss"
    assert results[0].title == "Democrats lead in polls"
    assert results[0].url == "https://reuters.com/1"


def test_fetch_articles_keyword_match_in_title():
    entry = _make_entry("Election results certified", "https://reuters.com/2", "No relevant summary.")
    with patch("prediction_news.articles.rss.feedparser.parse", return_value=_mock_parse([entry])):
        results = fetch_articles(["election"], "politics")
    assert len(results) == 1


def test_fetch_articles_keyword_match_in_summary():
    entry = _make_entry("Breaking news", "https://reuters.com/3", "Election results are in.")
    with patch("prediction_news.articles.rss.feedparser.parse", return_value=_mock_parse([entry])):
        results = fetch_articles(["election"], "politics")
    assert len(results) == 1


def test_fetch_articles_excludes_non_matching_entries():
    entry = _make_entry("Sports update", "https://reuters.com/4", "Football scores announced.")
    with patch("prediction_news.articles.rss.feedparser.parse", return_value=_mock_parse([entry])):
        results = fetch_articles(["election"], "politics")
    assert results == []


def test_fetch_articles_excludes_old_entries():
    entry = _make_old_entry("Old election news", "https://reuters.com/5", "Election results from last week.")
    with patch("prediction_news.articles.rss.feedparser.parse", return_value=_mock_parse([entry])):
        results = fetch_articles(["election"], "politics", since_hours=48)
    assert results == []


def test_fetch_articles_keeps_entries_without_published():
    entry = {"title": "Election coverage", "link": "https://reuters.com/6", "summary": "Election updates."}
    with patch("prediction_news.articles.rss.feedparser.parse", return_value=_mock_parse([entry])):
        results = fetch_articles(["election"], "politics")
    assert len(results) == 1


def test_fetch_articles_empty_domain_returns_empty():
    with patch("prediction_news.articles.rss.feedparser.parse", return_value=_mock_parse([])) as mock_parse:
        results = fetch_articles(["election"], "unknown_domain")
    mock_parse.assert_not_called()
    assert results == []


def test_fetch_articles_deduplicates_by_url():
    url = "https://reuters.com/7"
    entry = _make_entry("Election update", url, "Election results confirmed.")
    with patch("prediction_news.articles.rss.feedparser.parse", return_value=_mock_parse([entry])):
        results = fetch_articles(["election"], "politics")
    assert len(results) == 1
    assert results[0].url == url
