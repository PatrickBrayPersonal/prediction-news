import asyncio
from datetime import datetime, timezone

from loguru import logger

from prediction_news.articles.rss import fetch_articles
from prediction_news.config import settings
from prediction_news.kalshi import (
    get_all_markets,
    get_candlesticks,
    market_to_card_fields,
    max_single_day_move,
    most_recent_qualifying_move,
)
from prediction_news.keywords import extract_keywords
from prediction_news.models import MarketLogEntry, StoryCard
from prediction_news.ranking import filter_cards, rank_cards
from prediction_news.services.llm import (
    prefilter_articles,
    rank_sources,
)

DOMAIN_CATEGORIES: dict[str, list[str]] = {
    "news": [
        "Climate and Weather",
        "Companies",
        "Economics",
        "Elections",
        "Entertainment",
        "Financials",
        "Health",
        "Politics",
        "Science and Technology",
        "Social",
        "Transportation",
        "World",
    ],
    "sports": ["Sports"],
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


async def _build_card_from_candles(
    market: dict,
    candles: list[dict],
    probability_move: float,
    change_at: datetime,
    domain: str,
    run_timestamp: str = "",
) -> tuple[StoryCard | None, MarketLogEntry]:
    ticker = market.get("ticker", "")
    event_ticker = market.get("event_ticker", "")
    yes_sub_title = market.get("yes_sub_title", "")

    card_fields = market_to_card_fields(market, candles, probability_move=probability_move)
    market_name = card_fields["market_name"]
    keywords = extract_keywords(market_name, yes_sub_title)

    logger.info(
        f"_build_card ticker={ticker} prob_move={probability_move:.4f}"
        f" open_interest={card_fields['open_interest']:.2f} keywords={keywords}"
        f" change_at={change_at}"
    )

    articles = fetch_articles(keywords, domain, change_at=change_at)
    logger.info(f"_build_card ticker={ticker} fetched {len(articles)} raw articles")

    filtered = await prefilter_articles(market_name, articles)
    logger.info(
        f"_build_card ticker={ticker} prefilter: {len(filtered)}/{len(articles)} articles passed"
    )

    sources = await rank_sources(market_name, filtered)
    logger.info(f"_build_card ticker={ticker} rank_sources returned {len(sources)} sources")

    def _entry(card_built: bool, skip_reason: str | None) -> MarketLogEntry:
        return MarketLogEntry(
            run_timestamp=run_timestamp,
            domain=domain,
            ticker=ticker,
            event_ticker=event_ticker,
            market_name=market_name,
            yes_sub_title=yes_sub_title,
            probability_move=probability_move,
            current_probability=card_fields["current_probability"],
            open_interest=card_fields["open_interest"],
            volume_usd=card_fields["volume_usd"],
            change_at=change_at.isoformat(),
            articles_fetched=len(articles),
            articles_fetched_urls="|".join(a.url for a in articles) or None,
            articles_prefiltered=len(filtered),
            articles_prefiltered_urls="|".join(a.url for a in filtered) or None,
            sources_matched=len(sources),
            sources_matched_urls="|".join(s.url for s in sources) or None,
            card_built=card_built,
            skip_reason=skip_reason,
        )

    if not sources:
        logger.info(f"_build_card skipping ticker={ticker}: no causally matched sources")
        return None, _entry(False, "no_matched_sources")

    card = StoryCard(
        **card_fields,
        domain=domain,
        summary=sources[0].excerpt or "",
        sources=sources,
        change_at=change_at.isoformat(),
    )
    return card, _entry(True, None)


async def _build_card(
    market: dict, domain: str, run_timestamp: str = ""
) -> tuple[StoryCard | None, MarketLogEntry]:
    ticker = market.get("ticker", "")
    series_ticker = market.get("series_ticker", "")
    event_ticker = market.get("event_ticker", "")
    yes_sub_title = market.get("yes_sub_title", "")
    market_name = yes_sub_title or ticker

    def _early_exit(skip_reason: str) -> tuple[None, MarketLogEntry]:
        return None, MarketLogEntry(
            run_timestamp=run_timestamp,
            domain=domain,
            ticker=ticker,
            event_ticker=event_ticker,
            market_name=market_name,
            yes_sub_title=yes_sub_title,
            probability_move=None,
            current_probability=None,
            open_interest=None,
            volume_usd=None,
            change_at=None,
            articles_fetched=None,
            articles_fetched_urls=None,
            articles_prefiltered=None,
            articles_prefiltered_urls=None,
            sources_matched=None,
            sources_matched_urls=None,
            card_built=False,
            skip_reason=skip_reason,
        )

    if not series_ticker:
        logger.debug(f"_build_card skipping ticker={ticker}: no series_ticker")
        return _early_exit("no_series_ticker")

    try:
        candles = await get_candlesticks(
            ticker, series_ticker, days=settings.kalshi_lookback_days
        )
    except Exception:
        logger.warning(f"Failed to fetch candlesticks for {ticker}")
        return _early_exit("candlestick_fetch_failed")

    if not candles:
        logger.debug(f"_build_card skipping ticker={ticker}: 0 candles returned")
        return _early_exit("candlestick_fetch_failed")

    probability_move, change_at = most_recent_qualifying_move(
        candles, settings.min_probability_move
    )
    if not change_at:
        logger.debug(
            f"_build_card skipping ticker={ticker}: no single-day move"
            f" >= {settings.min_probability_move}"
        )
        return _early_exit("below_min_probability_move")

    return await _build_card_from_candles(
        market, candles, probability_move, change_at, domain, run_timestamp
    )


async def build_feed(domain: str) -> tuple[list[StoryCard], list[MarketLogEntry]]:
    categories = DOMAIN_CATEGORIES.get(domain, [])
    logger.info(f"build_feed domain={domain} categories={categories}")
    if not categories:
        logger.warning(f"build_feed unknown domain={domain}, returning empty feed")
        return [], []

    run_timestamp = datetime.now(timezone.utc).isoformat()
    log_entries: list[MarketLogEntry] = []

    try:
        domain_cats = {c.casefold() for c in categories}
        all_markets_raw = await get_all_markets()
        seen: set[str] = set()
        all_markets = []
        skipped_low_oi: list[dict] = []
        for m in all_markets_raw:
            ticker = m.get("ticker", "")
            if (m.get("category") or "").casefold() not in domain_cats:
                continue
            if ticker in seen:
                continue
            seen.add(ticker)
            oi = float(m.get("open_interest") or 0)
            if oi < settings.min_open_interest:
                skipped_low_oi.append(m)
                continue
            all_markets.append(m)
    except Exception as exc:
        logger.exception(
            f"Failed to fetch markets from Kalshi for domain={domain}: {exc}"
        )
        return [], []

    for m in skipped_low_oi:
        log_entries.append(
            MarketLogEntry(
                run_timestamp=run_timestamp,
                domain=domain,
                ticker=m.get("ticker", ""),
                event_ticker=m.get("event_ticker", ""),
                market_name=m.get("yes_sub_title", "") or m.get("ticker", ""),
                yes_sub_title=m.get("yes_sub_title", ""),
                probability_move=None,
                current_probability=None,
                open_interest=float(m.get("open_interest") or 0),
                volume_usd=None,
                change_at=None,
                articles_fetched=None,
                articles_fetched_urls=None,
                articles_prefiltered=None,
                articles_prefiltered_urls=None,
                sources_matched=None,
                sources_matched_urls=None,
                card_built=False,
                skip_reason="below_min_open_interest",
            )
        )

    logger.info(
        f"build_feed domain={domain}: {len(all_markets)} markets after open_interest"
        f" filter (skipped {len(skipped_low_oi)})"
    )
    pre_dedup = all_markets[:]
    all_markets = await _select_top_market_per_event(all_markets)

    selected_tickers = {m.get("ticker", "") for m in all_markets}
    for m in pre_dedup:
        if m.get("ticker", "") not in selected_tickers:
            log_entries.append(
                MarketLogEntry(
                    run_timestamp=run_timestamp,
                    domain=domain,
                    ticker=m.get("ticker", ""),
                    event_ticker=m.get("event_ticker", ""),
                    market_name=m.get("yes_sub_title", "") or m.get("ticker", ""),
                    yes_sub_title=m.get("yes_sub_title", ""),
                    probability_move=None,
                    current_probability=None,
                    open_interest=None,
                    volume_usd=None,
                    change_at=None,
                    articles_fetched=None,
                    articles_fetched_urls=None,
                    articles_prefiltered=None,
                    articles_prefiltered_urls=None,
                    sources_matched=None,
                    sources_matched_urls=None,
                    card_built=False,
                    skip_reason="dedup_loser",
                )
            )

    logger.info(
        f"build_feed domain={domain}: {len(all_markets)} markets after event dedup"
    )

    results = await asyncio.gather(
        *[_build_card(market, domain, run_timestamp) for market in all_markets],
        return_exceptions=True,
    )

    errors = [r for r in results if isinstance(r, Exception)]
    pairs = [r for r in results if not isinstance(r, Exception)]
    cards = [card for card, _ in pairs if card is not None]
    log_entries.extend(entry for _, entry in pairs)

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
    return ranked, log_entries
