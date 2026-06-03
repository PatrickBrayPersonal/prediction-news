import asyncio
import base64
import time
from datetime import datetime, timezone
from pathlib import Path

import httpx
from cachetools import TTLCache
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding
from loguru import logger
from tenacity import retry, retry_if_exception, stop_after_attempt, wait_exponential

from prediction_news.config import settings
from prediction_news.models import SparklinePoint

KALSHI_BASE = "https://external-api.kalshi.com/trade-api/v2"

_REPO_ROOT = Path(__file__).parent.parent

_SEMAPHORE = asyncio.Semaphore(3)
_MARKET_LIST_CACHE: TTLCache = TTLCache(maxsize=64, ttl=300)
_EVENTS_CACHE: TTLCache = TTLCache(maxsize=32, ttl=300)
_CANDLESTICK_CACHE: TTLCache = TTLCache(maxsize=512, ttl=600)
_CANDLESTICK_FAILURE_CACHE: TTLCache = TTLCache(maxsize=512, ttl=120)


def _is_retryable(exc: BaseException) -> bool:
    if isinstance(exc, httpx.HTTPStatusError):
        return exc.response.status_code in (429, 500, 502, 503, 504)
    return isinstance(exc, httpx.RequestError)


_KALSHI_RETRY = retry(
    retry=retry_if_exception(_is_retryable),
    wait=wait_exponential(multiplier=1, min=1, max=30),
    stop=stop_after_attempt(5),
    reraise=True,
)


def _load_private_key(key_path: str | None = None):
    path = Path(key_path or settings.kalshi_private_key_path)
    if not path.is_absolute():
        path = _REPO_ROOT / path
    with open(path, "rb") as f:
        return serialization.load_pem_private_key(f.read(), password=None)


def _auth_headers(method: str, path: str) -> dict[str, str]:
    api_key = settings.kalshi_key_id
    timestamp_ms = str(int(time.time() * 1000))
    message = timestamp_ms + method.upper() + path
    key = _load_private_key()
    signature = key.sign(
        message.encode("utf-8"),
        padding.PSS(
            mgf=padding.MGF1(hashes.SHA256()), salt_length=padding.PSS.DIGEST_LENGTH
        ),
        hashes.SHA256(),
    )
    return {
        "KALSHI-ACCESS-KEY": api_key,
        "KALSHI-ACCESS-TIMESTAMP": timestamp_ms,
        "KALSHI-ACCESS-SIGNATURE": base64.b64encode(signature).decode("utf-8"),
    }


@_KALSHI_RETRY
async def _fetch_markets(params: dict[str, str]) -> list[dict]:
    path = "/trade-api/v2/markets"
    async with _SEMAPHORE:
        async with httpx.AsyncClient(base_url=KALSHI_BASE) as client:
            response = await client.get(
                "/markets",
                params=params,
                headers=_auth_headers("GET", path),
            )
            response.raise_for_status()
            return response.json().get("markets", [])


async def list_markets(series: str | None = None) -> list[dict]:
    cache_key = series or "__all__"
    if cache_key in _MARKET_LIST_CACHE:
        logger.debug(f"list_markets cache hit for key={cache_key}")
        return _MARKET_LIST_CACHE[cache_key]
    logger.debug(f"list_markets fetching from API for key={cache_key}")
    params: dict[str, str] = {"status": "open", "limit": "100"}
    if series:
        params["series_ticker"] = series
    result = await _fetch_markets(params)
    logger.info(f"list_markets fetched {len(result)} markets for key={cache_key}")
    _MARKET_LIST_CACHE[cache_key] = result
    return result


@_KALSHI_RETRY
async def _fetch_events(category: str) -> list[dict]:
    path = "/trade-api/v2/events"
    async with _SEMAPHORE:
        async with httpx.AsyncClient(base_url=KALSHI_BASE) as client:
            response = await client.get(
                "/events",
                params={
                    "status": "open",
                    "category": category,
                    "limit": str(settings.kalshi_events_limit),
                },
                headers=_auth_headers("GET", path),
            )
            response.raise_for_status()
            return response.json().get("events", [])


@_KALSHI_RETRY
async def _fetch_markets_by_event(event_ticker: str) -> list[dict]:
    path = "/trade-api/v2/markets"
    async with _SEMAPHORE:
        async with httpx.AsyncClient(base_url=KALSHI_BASE) as client:
            response = await client.get(
                "/markets",
                params={"event_ticker": event_ticker, "status": "open", "limit": "20"},
                headers=_auth_headers("GET", path),
            )
            response.raise_for_status()
            return response.json().get("markets", [])


async def list_markets_by_category(category: str) -> list[dict]:
    if category in _EVENTS_CACHE:
        logger.debug(f"list_markets_by_category cache hit for category={category}")
        return _EVENTS_CACHE[category]

    logger.info(f"list_markets_by_category fetching events for category={category}")
    events = await _fetch_events(category)
    logger.info(
        f"list_markets_by_category got {len(events)} events for category={category}"
    )

    market_batches = await asyncio.gather(
        *[_fetch_markets_by_event(e["event_ticker"]) for e in events],
        return_exceptions=True,
    )

    seen: set[str] = set()
    result: list[dict] = []
    failed = 0
    for event, batch in zip(events, market_batches):
        if isinstance(batch, Exception):
            logger.warning(
                f"list_markets_by_category failed to fetch markets"
                f" for event={event.get('event_ticker', '?')}: {batch}"
            )
            failed += 1
            continue
        series_ticker = event.get("series_ticker", "")
        before = len(result)
        for m in batch:
            ticker = m.get("ticker", "")
            if ticker and ticker not in seen:
                seen.add(ticker)
                result.append(
                    {
                        **m,
                        "series_ticker": series_ticker,
                        "event_ticker": event.get("event_ticker", ""),
                    }
                )
        logger.debug(
            f"event={event.get('event_ticker', '?')} added {len(result) - before}"
            f" markets (batch size={len(batch)})"
        )

    logger.info(
        f"list_markets_by_category category={category}:"
        f" {len(result)} total markets, {failed} events failed"
    )
    _EVENTS_CACHE[category] = result
    return result


@_KALSHI_RETRY
async def get_market(ticker: str) -> dict:
    path = f"/trade-api/v2/markets/{ticker}"
    async with _SEMAPHORE:
        async with httpx.AsyncClient(base_url=KALSHI_BASE) as client:
            response = await client.get(
                f"/markets/{ticker}",
                headers=_auth_headers("GET", path),
            )
            response.raise_for_status()
            return response.json().get("market", {})


@_KALSHI_RETRY
async def _fetch_candlesticks(
    ticker: str, series_ticker: str, params: dict[str, str]
) -> list[dict]:
    path = f"/trade-api/v2/series/{series_ticker}/markets/{ticker}/candlesticks"
    async with _SEMAPHORE:
        async with httpx.AsyncClient(base_url=KALSHI_BASE) as client:
            response = await client.get(
                f"/series/{series_ticker}/markets/{ticker}/candlesticks",
                params=params,
                headers=_auth_headers("GET", path),
            )
            response.raise_for_status()
            candles = response.json().get("candlesticks", [])
            return sorted(candles, key=lambda c: c["end_period_ts"])


async def get_candlesticks(
    ticker: str, series_ticker: str, days: int = 7
) -> list[dict]:
    cache_key = (ticker, days)
    if cache_key in _CANDLESTICK_CACHE:
        logger.debug(f"get_candlesticks cache hit for ticker={ticker} days={days}")
        return _CANDLESTICK_CACHE[cache_key]
    if cache_key in _CANDLESTICK_FAILURE_CACHE:
        logger.debug(
            f"get_candlesticks failure cache hit for ticker={ticker}, skipping"
        )
        raise _CANDLESTICK_FAILURE_CACHE[cache_key]
    end_ts = int(time.time())
    start_ts = end_ts - days * 86400
    params = {
        "start_ts": str(start_ts),
        "end_ts": str(end_ts),
        "period_interval": "1440",
    }
    logger.debug(
        f"get_candlesticks fetching ticker={ticker} series={series_ticker} days={days}"
    )
    try:
        result = await _fetch_candlesticks(ticker, series_ticker, params)
    except Exception as exc:
        logger.warning(f"get_candlesticks fetch failed for ticker={ticker}: {exc}")
        _CANDLESTICK_FAILURE_CACHE[cache_key] = exc
        raise
    logger.info(f"get_candlesticks ticker={ticker} returned {len(result)} candles")
    _CANDLESTICK_CACHE[cache_key] = result
    return result


def _candle_mid_price(candle: dict) -> float:
    bid_data = candle.get("yes_bid") or {}
    ask_data = candle.get("yes_ask") or {}
    # Candle prices are nested dicts with close_dollars as a decimal string
    bid = float(bid_data.get("close_dollars") or 0)
    ask = float(ask_data.get("close_dollars") or 0)
    if bid and ask:
        return (bid + ask) / 2
    return bid or ask or 0.0


def candlesticks_to_sparkline(candles: list[dict]) -> list[SparklinePoint]:
    sorted_candles = sorted(candles, key=lambda c: c["end_period_ts"])
    points = []
    for candle in sorted_candles:
        ts = candle["end_period_ts"]
        date = datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d")
        prob = round(min(max(_candle_mid_price(candle), 0.0), 1.0), 4)
        points.append(SparklinePoint(date=date, probability=prob))
    return points


def _resolve_headline(title: str, yes_sub_title: str) -> str:
    """Fill in the subject blank in templated Kalshi market titles.

    Kalshi returns titles like "Will  become President..." with a double-space
    where the candidate name belongs. yes_sub_title holds the actual name.
    """
    if yes_sub_title and "  " in title:
        return title.replace("  ", f" {yes_sub_title} ", 1)
    return title


def max_single_day_move(candles: list[dict]) -> float:
    if len(candles) < 2:
        return 0.0
    sorted_candles = sorted(candles, key=lambda c: c["end_period_ts"])
    prices = [_candle_mid_price(c) for c in sorted_candles]
    return max(abs(prices[i] - prices[i - 1]) for i in range(1, len(prices)))


def most_recent_qualifying_move(
    candles: list[dict], min_move: float
) -> tuple[float, datetime | None]:
    """Return the signed move and end datetime of the largest |move| >= min_move.

    Scans all consecutive-day pairs and picks the one with the greatest absolute
    move. Returns (0.0, None) if no day qualifies.
    """
    if len(candles) < 2:
        return (0.0, None)
    sorted_candles = sorted(candles, key=lambda c: c["end_period_ts"])
    prices = [_candle_mid_price(c) for c in sorted_candles]
    best_move = 0.0
    best_ts: int | None = None
    for i in range(1, len(prices)):
        move = prices[i] - prices[i - 1]
        if abs(move) >= min_move and abs(move) > abs(best_move):
            best_move = move
            best_ts = sorted_candles[i]["end_period_ts"]
    if best_ts is None:
        return (0.0, None)
    return (round(best_move, 4), datetime.fromtimestamp(best_ts, tz=timezone.utc))


def market_to_card_fields(
    market: dict, candles: list[dict], probability_move: float
) -> dict:
    sparkline = candlesticks_to_sparkline(candles)
    current_prob = round(
        min(max(_candle_mid_price(candles[-1]) if candles else 0.0, 0.0), 1.0), 4
    )
    volume = sum(float(c.get("volume_fp") or 0) for c in candles)
    open_interest = float(candles[-1].get("open_interest_fp") or 0) if candles else 0.0
    title = market.get("title", "")
    yes_sub_title = market.get("yes_sub_title", "").strip()
    headline = _resolve_headline(title, yes_sub_title)
    ticker = market.get("ticker", "")
    series_ticker = market.get("series_ticker", "")
    market_url = (
        f"https://kalshi.com/markets/{series_ticker.lower()}/{ticker.lower()}"
        if series_ticker and ticker
        else ""
    )
    return {
        "id": ticker,
        "platform": "Kalshi",
        "market_name": headline,
        "headline": headline,
        "yes_sub_title": yes_sub_title,
        "market_url": market_url,
        "current_probability": current_prob,
        "probability_move": probability_move,
        "volume_usd": volume,
        "open_interest": open_interest,
        "sparkline": sparkline,
    }
