from datetime import datetime, timedelta, timezone

import feedparser

from prediction_news.config import settings
from prediction_news.models import Source

RSS_FEEDS: dict[str, list[str]] = {
    "politics": [
        "https://feeds.reuters.com/reuters/politicsNews",
        "https://rss.nytimes.com/services/xml/rss/nyt/Politics.xml",
        "https://rss.nytimes.com/services/xml/rss/nyt/Business.xml",
        "https://rss.nytimes.com/services/xml/rss/nyt/Technology.xml",
        "https://feeds.washingtonpost.com/rss/politics",
        "https://feeds.bloomberg.com/markets/news.rss",
        "https://feeds.bloomberg.com/technology/news.rss",
        "https://feeds.marketwatch.com/marketwatch/topstories/",
        "https://feeds.marketwatch.com/marketwatch/realtimeheadlines/",
        "https://www.ft.com/rss/home",
        "https://www.ft.com/markets?format=rss",
    ],
    "world": [
        "https://feeds.reuters.com/reuters/worldNews",
        "https://rss.nytimes.com/services/xml/rss/nyt/World.xml",
        "https://feeds.bbci.co.uk/news/world/rss.xml",
    ],
    "sports": [
        "https://www.espn.com/espn/rss/news",
        "https://sports.yahoo.com/rss/",
    ],
}


def _is_within_window(entry: dict, change_at: datetime) -> bool:
    published = entry.get("published_parsed")
    if published is None:
        return True
    pub_dt = datetime(*published[:6], tzinfo=timezone.utc)
    window_start = change_at - timedelta(hours=settings.article_window_before_hours)
    window_end = change_at + timedelta(hours=settings.article_window_after_hours)
    return window_start <= pub_dt <= window_end


def _matches_keywords(entry: dict, keywords: list[str]) -> bool:
    text = (entry.get("title", "") + " " + entry.get("summary", "")).lower()
    return any(kw.lower() in text for kw in keywords)


def fetch_articles(
    keywords: list[str], domain: str, change_at: datetime | None = None
) -> list[Source]:
    feed_urls = RSS_FEEDS.get(domain, [])
    seen_urls: set[str] = set()
    results: list[Source] = []

    for feed_url in feed_urls:
        parsed = feedparser.parse(feed_url)
        for entry in parsed.get("entries", []):
            url = entry.get("link", "")
            if url in seen_urls:
                continue
            if change_at is not None and not _is_within_window(entry, change_at):
                continue
            if not _matches_keywords(entry, keywords):
                continue
            seen_urls.add(url)
            results.append(Source(title=entry.get("title", ""), url=url, type="rss"))

    return results
