import os

from prediction_news.models import StoryCard, Source
from prediction_news.mock_data import MOCK_CARDS

CARDS_PER_DOMAIN = 5

# Maps our domain names to the Kalshi series tickers that cover them
DOMAIN_SERIES: dict[str, list[str]] = {
    "politics": ["KXFED", "KXTRUMP", "KXCONGRESS", "KXGOV", "KXBUDGET", "KXSENATE"],
    "world":    ["KXBTC", "KXINXD", "KXWORLD"],
    "sports":   ["KXNBA", "KXMLB", "KXNFL", "KXNHL"],
}


def get_feed(domain: str) -> list[StoryCard]:
    if os.getenv("DATA", "test") == "real":
        try:
            return _real_feed(domain)
        except Exception as e:
            print(f"[feed] Kalshi fetch failed ({e}), falling back to mock data")
            return _mock_feed(domain)
    return _mock_feed(domain)


def _mock_feed(domain: str) -> list[StoryCard]:
    cards = [c for c in MOCK_CARDS if c.domain == domain]
    return _sort(cards)


def _real_feed(domain: str) -> list[StoryCard]:
    from prediction_news.kalshi import list_markets, get_candlesticks, market_to_card_fields, _f

    # Collect best market per event across all series for this domain
    by_event: dict[str, dict] = {}
    for series in DOMAIN_SERIES.get(domain, []):
        result = list_markets(limit=100, series_ticker=series, status="open")
        for m in result.get("markets", []):
            event = m.get("event_ticker", m["ticker"])
            if event not in by_event or _f(m.get("volume_fp")) > _f(by_event[event].get("volume_fp")):
                by_event[event] = m

    top = sorted(by_event.values(), key=lambda m: _f(m.get("volume_fp")), reverse=True)[:CARDS_PER_DOMAIN]

    cards = []
    for market in top:
        try:
            candles = get_candlesticks(market["ticker"], days=7)
            fields = market_to_card_fields(market, candles)
            cards.append(StoryCard(
                domain=domain,
                summary="",
                calibration_note="",
                sources=[],
                **fields,
            ))
        except Exception as e:
            print(f"[feed] Skipping {market['ticker']}: {e}")

    return _sort(cards)


def _sort(cards: list[StoryCard]) -> list[StoryCard]:
    return sorted(cards, key=lambda c: abs(c.probability_move) * c.volume_usd, reverse=True)
