import asyncio

from loguru import logger

from prediction_news.articles.rss import fetch_articles
from prediction_news.config import settings
from prediction_news.kalshi import (
    get_candlesticks,
    list_markets_by_category,
    market_to_card_fields,
    max_single_day_move,
)
from prediction_news.keywords import extract_keywords
from prediction_news.models import StoryCard
from prediction_news.ranking import filter_cards, rank_cards
from prediction_news.services.llm import (
    prefilter_articles,
    score_and_summarize,
)

DOMAIN_CATEGORIES: dict[str, list[str]] = {
    "politics": ["Politics", "Elections"],
    "world": ["World", "Economics", "Science and Technology", "Climate and Weather"],
    "sports": ["Sports", "Entertainment"],
}


async def _build_card(market: dict, domain: str) -> StoryCard | None:
    ticker = market.get("ticker", "")
    series_ticker = market.get("series_ticker", "")
    if not series_ticker:
        logger.debug(f"_build_card skipping ticker={ticker}: no series_ticker")
        return None
    try:
        candles = await get_candlesticks(
            ticker, series_ticker, days=settings.kalshi_lookback_days
        )
    except Exception:
        logger.warning(f"Failed to fetch candlesticks for {ticker}")
        return None

    if not candles:
        logger.debug(f"_build_card skipping ticker={ticker}: 0 candles returned")
        return None

    card_fields = market_to_card_fields(market, candles)

    daily_move = max_single_day_move(candles)
    if daily_move < settings.min_probability_move:
        logger.debug(
            f"_build_card skipping ticker={ticker}: max single-day move"
            f" {daily_move:.4f} < {settings.min_probability_move}"
        )
        return None

    open_interest = card_fields["open_interest"]
    if open_interest < settings.min_open_interest:
        logger.debug(
            f"_build_card skipping ticker={ticker}: open_interest {open_interest:.2f}"
            f" < {settings.min_open_interest}"
        )
        return None

    yes_sub_title = market.get("yes_sub_title", "")
    keywords = extract_keywords(card_fields["market_name"], yes_sub_title)
    logger.info(
        f"_build_card ticker={ticker} prob_move={card_fields['probability_move']:.4f}"
        f" open_interest={card_fields['open_interest']:.2f} keywords={keywords}"
    )

    articles = fetch_articles(keywords, domain)
    logger.info(f"_build_card ticker={ticker} fetched {len(articles)} raw articles")

    filtered = await prefilter_articles(card_fields["market_name"], articles)
    logger.info(
        f"_build_card ticker={ticker} prefilter: {len(filtered)}/{len(articles)} articles passed"
    )

    summary, sources = await score_and_summarize(card_fields["market_name"], filtered)
    logger.info(
        f"_build_card ticker={ticker} score_and_summarize returned {len(sources)} sources"
    )

    return StoryCard(
        **card_fields,
        domain=domain,
        summary=summary,
        sources=sources,
    )


async def build_feed(domain: str) -> list[StoryCard]:
    categories = DOMAIN_CATEGORIES.get(domain, [])
    logger.info(f"build_feed domain={domain} categories={categories}")
    if not categories:
        logger.warning(f"build_feed unknown domain={domain}, returning empty feed")
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
        logger.exception(
            f"Failed to fetch markets from Kalshi for domain={domain}: {exc}"
        )
        return []

    logger.info(
        f"build_feed domain={domain}: {len(all_markets)} total unique markets to process"
    )

    results = await asyncio.gather(
        *[_build_card(market, domain) for market in all_markets],
        return_exceptions=True,
    )

    errors = [r for r in results if isinstance(r, Exception)]
    cards = [r for r in results if isinstance(r, StoryCard)]
    if errors:
        for exc in errors:
            logger.exception(
                f"build_feed domain={domain}: card failed with exception", exc_info=exc
            )
        logger.warning(
            f"build_feed domain={domain}: {len(errors)} cards failed with exceptions"
        )
    logger.info(
        f"build_feed domain={domain}: {len(cards)}/{len(all_markets)} cards built successfully"
    )

    filtered = filter_cards(
        cards,
        min_move=settings.min_probability_move,
        min_open_interest=settings.min_open_interest,
    )
    ranked = rank_cards(filtered)
    logger.info(f"build_feed domain={domain}: returning {len(ranked)} ranked cards")
    return ranked
