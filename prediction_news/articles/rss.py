from datetime import datetime, timezone

import feedparser

from prediction_news.models import Source

RSS_FEEDS: dict[str, list[str]] = {
    "politics": [
        "https://feeds.reuters.com/reuters/politicsNews",
        "https://rss.nytimes.com/services/xml/rss/nyt/Politics.xml",
        "https://feeds.washingtonpost.com/rss/politics",
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


def _is_recent(entry: dict, since_hours: int) -> bool:
    published = entry.get("published_parsed")
    if published is None:
        return True
    pub_dt = datetime(*published[:6], tzinfo=timezone.utc)
    age_hours = (datetime.now(timezone.utc) - pub_dt).total_seconds() / 3600
    return age_hours <= since_hours


def _matches_keywords(entry: dict, keywords: list[str]) -> bool:
    text = (entry.get("title", "") + " " + entry.get("summary", "")).lower()
    return any(kw.lower() in text for kw in keywords)


def fetch_articles(
    keywords: list[str], domain: str, since_hours: int = 48
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
            if not _is_recent(entry, since_hours):
                continue
            if not _matches_keywords(entry, keywords):
                continue
            seen_urls.add(url)
            results.append(Source(title=entry.get("title", ""), url=url, type="rss"))

    return results
