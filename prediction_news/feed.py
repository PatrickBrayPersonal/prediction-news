import asyncio

from loguru import logger

from prediction_news.articles.rss import fetch_articles
from prediction_news.config import settings
from prediction_news.kalshi import (
    get_candlesticks,
    list_markets_by_category,
    market_to_card_fields,
    max_single_day_move,
    most_recent_qualifying_move,
)
from prediction_news.keywords import extract_keywords
from prediction_news.models import StoryCard
from prediction_news.ranking import filter_cards, rank_cards
from prediction_news.services.llm import (
    prefilter_articles,
    rank_sources,
)

DOMAIN_CATEGORIES: dict[str, list[str]] = {
    "politics": ["Politics", "Elections"],
    "world": ["World", "Economics", "Science and Technology", "Climate and Weather"],
    "sports": ["Sports", "Entertainment"],
}


async def _select_top_market_per_event(markets: list[dict]) -> list[dict]:
    groups: dict[str, list[dict]] = {}
    for m in markets:
        key = m.get("event_ticker") or m.get("ticker", "")
        groups.setdefault(key, []).append(m)

    result: list[dict] = []
    for event_key, group in groups.items():
        if len(group) == 1:
            result.append(group[0])
            continue

        candle_results = await asyncio.gather(
            *[
                get_candlesticks(
                    m.get("ticker", ""),
                    m.get("series_ticker", ""),
                    days=settings.kalshi_lookback_days,
                )
                for m in group
            ],
            return_exceptions=True,
        )

        best_idx = 0
        best_move = -1.0
        for i, candles in enumerate(candle_results):
            if isinstance(candles, Exception) or not candles:
                continue
            move = max_single_day_move(candles)
            if move > best_move:
                best_move = move
                best_idx = i

        dropped = len(group) - 1
        winner_ticker = group[best_idx].get("ticker", "?")
        logger.info(
            f"_select_top_market_per_event event={event_key}: keeping {winner_ticker},"
            f" dropping {dropped} other market(s)"
        )
        result.append(group[best_idx])

    return result


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

    move_value, change_at = most_recent_qualifying_move(
        candles, settings.min_probability_move
    )
    if not change_at:
        logger.debug(
            f"_build_card skipping ticker={ticker}: no single-day move"
            f" >= {settings.min_probability_move}"
        )
        return None

    card_fields = market_to_card_fields(market, candles, probability_move=move_value)

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
        f" change_at={change_at}"
    )

    articles = fetch_articles(keywords, domain, change_at=change_at)
    logger.info(f"_build_card ticker={ticker} fetched {len(articles)} raw articles")

    filtered = await prefilter_articles(card_fields["market_name"], articles)
    logger.info(
        f"_build_card ticker={ticker} prefilter: {len(filtered)}/{len(articles)} articles passed"
    )

    sources = await rank_sources(card_fields["market_name"], filtered)
    logger.info(
        f"_build_card ticker={ticker} rank_sources returned {len(sources)} sources"
    )
    if not sources:
        logger.info(f"_build_card skipping ticker={ticker}: no causally matched sources")
        return None

    summary = sources[0].excerpt if sources else ""

    return StoryCard(
        **card_fields,
        domain=domain,
        summary=summary,
        sources=sources,
        change_at=change_at.isoformat(),
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
        f"build_feed domain={domain}: {len(all_markets)} total unique markets before dedup"
    )
    all_markets = await _select_top_market_per_event(all_markets)
    logger.info(
        f"build_feed domain={domain}: {len(all_markets)} markets after event dedup"
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
