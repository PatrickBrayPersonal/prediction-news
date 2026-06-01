import asyncio
import base64
import time
from datetime import datetime, timezone
from pathlib import Path

import httpx
from cachetools import TTLCache
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding
from tenacity import retry, retry_if_exception, stop_after_attempt, wait_exponential

from prediction_news.config import settings
from prediction_news.models import SparklinePoint

KALSHI_BASE = "https://external-api.kalshi.com/trade-api/v2"

_REPO_ROOT = Path(__file__).parent.parent

_SEMAPHORE = asyncio.Semaphore(3)
_MARKET_LIST_CACHE: TTLCache = TTLCache(maxsize=64, ttl=300)
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
    api_key = settings.kalshi_api_key
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
        return _MARKET_LIST_CACHE[cache_key]
    params: dict[str, str] = {"status": "open", "limit": "100"}
    if series:
        params["series_ticker"] = series
    result = await _fetch_markets(params)
    _MARKET_LIST_CACHE[cache_key] = result
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
async def _fetch_candlesticks(ticker: str, params: dict[str, str]) -> list[dict]:
    path = f"/trade-api/v2/markets/{ticker}/candlesticks"
    async with _SEMAPHORE:
        async with httpx.AsyncClient(base_url=KALSHI_BASE) as client:
            response = await client.get(
                f"/markets/{ticker}/candlesticks",
                params=params,
                headers=_auth_headers("GET", path),
            )
            response.raise_for_status()
            candles = response.json().get("candlesticks", [])
            return sorted(candles, key=lambda c: c["end_period_ts"])


async def get_candlesticks(ticker: str, days: int = 7) -> list[dict]:
    cache_key = (ticker, days)
    if cache_key in _CANDLESTICK_CACHE:
        return _CANDLESTICK_CACHE[cache_key]
    if cache_key in _CANDLESTICK_FAILURE_CACHE:
        raise _CANDLESTICK_FAILURE_CACHE[cache_key]
    end_ts = int(time.time())
    start_ts = end_ts - days * 86400
    params = {
        "start_ts": str(start_ts),
        "end_ts": str(end_ts),
        "period_interval": "1440",
    }
    try:
        result = await _fetch_candlesticks(ticker, params)
    except Exception as exc:
        _CANDLESTICK_FAILURE_CACHE[cache_key] = exc
        raise
    _CANDLESTICK_CACHE[cache_key] = result
    return result


def _candle_mid_price(candle: dict) -> float:
    bid = candle.get("yes_bid", 0.0)
    ask = candle.get("yes_ask", 0.0)
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


def market_to_card_fields(market: dict, candles: list[dict]) -> dict:
    sparkline = candlesticks_to_sparkline(candles)
    current_prob = round(
        min(max(_candle_mid_price(candles[-1]) if candles else 0.0, 0.0), 1.0), 4
    )
    first_prob = round(
        min(max(_candle_mid_price(candles[0]) if candles else 0.0, 0.0), 1.0), 4
    )
    probability_move = round(current_prob - first_prob, 4)
    volume = market.get("volume", 0)
    return {
        "id": market.get("ticker", ""),
        "platform": "Kalshi",
        "market_name": market.get("title", ""),
        "headline": market.get("title", ""),
        "current_probability": current_prob,
        "probability_move": probability_move,
        "volume_usd": float(volume),
        "sparkline": sparkline,
    }
