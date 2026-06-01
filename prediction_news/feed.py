import asyncio
import logging

from prediction_news.articles.rss import fetch_articles
from prediction_news.kalshi import (
    get_candlesticks,
    list_markets_by_category,
    market_to_card_fields,
)
from prediction_news.models import StoryCard
from prediction_news.ranking import rank_cards
from prediction_news.services.llm import (
    generate_calibration_note,
    prefilter_articles,
    score_and_summarize,
)

logger = logging.getLogger(__name__)

DOMAIN_CATEGORIES: dict[str, list[str]] = {
    "politics": ["Politics", "Elections"],
    "world": ["World", "Economics", "Science and Technology", "Climate and Weather"],
    "sports": ["Sports", "Entertainment"],
}


async def _build_card(market: dict, domain: str) -> StoryCard | None:
    ticker = market.get("ticker", "")
    series_ticker = market.get("series_ticker", "")
    if not series_ticker:
        return None
    try:
        candles = await get_candlesticks(ticker, series_ticker, days=7)
    except Exception:
        logger.warning("Failed to fetch candlesticks for %s", ticker)
        return None

    if not candles:
        return None

    card_fields = market_to_card_fields(market, candles)
    keywords = card_fields["market_name"].split()

    articles = fetch_articles(keywords, domain)
    filtered = await prefilter_articles(card_fields["market_name"], articles)
    summary, sources = await score_and_summarize(card_fields["market_name"], filtered)
    calibration_note = await generate_calibration_note(
        card_fields["probability_move"], card_fields["volume_usd"]
    )

    return StoryCard(
        **card_fields,
        domain=domain,
        summary=summary,
        calibration_note=calibration_note,
        sources=sources,
    )


async def build_feed(domain: str) -> list[StoryCard]:
    categories = DOMAIN_CATEGORIES.get(domain, [])
    if not categories:
        return []

    try:
        market_lists = await asyncio.gather(
            *[list_markets_by_category(cat) for cat in categories]
        )
        seen: set[str] = set()
        all_markets = []
        for markets in market_lists:
            for m in markets:
                ticker = m.get("ticker", "")
                if ticker not in seen:
                    seen.add(ticker)
                    all_markets.append(m)
    except Exception as exc:
        logger.error(
            "Failed to fetch markets from Kalshi for domain=%s: %s",
            domain,
            exc,
            exc_info=True,
        )
        return []

    results = await asyncio.gather(
        *[_build_card(market, domain) for market in all_markets],
        return_exceptions=True,
    )

    cards = [r for r in results if isinstance(r, StoryCard)]
    return rank_cards(cards)
