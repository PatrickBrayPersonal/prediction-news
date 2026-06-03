import re
from datetime import datetime, timedelta, timezone

import feedparser

from prediction_news.config import settings
from prediction_news.models import Source


def _strip_html(text: str) -> str:
    return re.sub(r"<[^>]+>", "", text).strip()


RSS_FEEDS: dict[str, list[str]] = {
    "politics": [
        # US Politics & Policy
        "https://feeds.reuters.com/reuters/politicsNews",
        "https://rss.nytimes.com/services/xml/rss/nyt/Politics.xml",
        "https://feeds.washingtonpost.com/rss/politics",
        "https://feeds.politico.com/politico/rss/politicopicks",
        "https://thehill.com/rss/syndicator/19109",
        "https://www.axios.com/feeds/feed.rss",
        "https://www.npr.org/rss/rss.php?id=1014",  # NPR Politics
        # Business & Markets
        "https://rss.nytimes.com/services/xml/rss/nyt/Business.xml",
        "https://feeds.bloomberg.com/markets/news.rss",
        "https://feeds.marketwatch.com/marketwatch/topstories/",
        "https://feeds.marketwatch.com/marketwatch/realtimeheadlines/",
        "https://www.cnbc.com/id/100003114/device/rss/rss.html",  # CNBC Top News
        "https://www.cnbc.com/id/10001147/device/rss/rss.html",  # CNBC Business
        "https://fortune.com/feed/",
        "https://www.wsj.com/xml/rss/3_7031.xml",  # WSJ Markets
        "https://www.ft.com/rss/home",
        "https://www.ft.com/markets?format=rss",
        # Technology
        "https://rss.nytimes.com/services/xml/rss/nyt/Technology.xml",
        "https://feeds.bloomberg.com/technology/news.rss",
        "https://feeds.arstechnica.com/arstechnica/index",
        "https://www.wired.com/feed/rss",
        "https://techcrunch.com/feed/",
        "https://www.theverge.com/rss/index.xml",
    ],
    "world": [
        "https://feeds.reuters.com/reuters/worldNews",
        "https://rss.nytimes.com/services/xml/rss/nyt/World.xml",
        "https://feeds.bbci.co.uk/news/world/rss.xml",
        "https://feeds.bbci.co.uk/news/rss.xml",
        "https://www.aljazeera.com/xml/rss/all.xml",
        "https://feeds.washingtonpost.com/rss/world",
        "https://www.npr.org/rss/rss.php?id=1004",  # NPR World
        "https://feeds.theguardian.com/theguardian/world/rss",
        "https://rss.dw.com/xml/rss-en-world",  # Deutsche Welle
        "https://www.france24.com/en/rss",
        "https://feeds.feedburner.com/time/world",
        "https://feeds.skynews.com/feeds/rss/world.xml",
        "https://apnews.com/rss/apf-intlnews",  # AP International
    ],
    "sports": [
        # General
        "https://www.espn.com/espn/rss/news",
        "https://sports.yahoo.com/rss/",
        "https://www.cbssports.com/rss/headlines/",
        "https://sportingnews.com/rss",
        # ESPN by sport
        "https://www.espn.com/espn/rss/nfl/news",
        "https://www.espn.com/espn/rss/nba/news",
        "https://www.espn.com/espn/rss/mlb/news",
        "https://www.espn.com/espn/rss/nhl/news",
        "https://www.espn.com/espn/rss/soccer/news",
        "https://www.espn.com/espn/rss/ncf/news",  # College Football
        "https://www.espn.com/espn/rss/ncb/news",  # College Basketball
        # Other
        "https://www.skysports.com/rss/12040",  # Sky Sports Football
        "https://www.nfl.com/rss/rsslanding.html",
        "https://www.si.com/rss/si_topstories.rss",
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
            published_parsed = entry.get("published_parsed")
            published_at = (
                datetime(*published_parsed[:6], tzinfo=timezone.utc).isoformat()
                if published_parsed
                else None
            )
            raw_excerpt = entry.get("summary", "") or ""
            excerpt = _strip_html(raw_excerpt) or None
            results.append(
                Source(
                    title=entry.get("title", ""),
                    url=url,
                    type="rss",
                    published_at=published_at,
                    excerpt=excerpt,
                )
            )
    return results
