import base64
import os
import time
from datetime import datetime, timedelta, timezone

import httpx
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding

from prediction_news.models import SparklinePoint

BASE_URL = "https://external-api.kalshi.com/trade-api/v2"


def _load_private_key() -> bytes:
    path = os.environ.get("KALSHI_PRIVATE_KEY_PATH")
    if path:
        with open(path, "rb") as f:
            return f.read()
    pem = os.environ.get("KALSHI_PRIVATE_KEY", "")
    return pem.replace("\\n", "\n").encode()


def _auth_headers(method: str, path: str) -> dict:
    ts = str(int(time.time() * 1000))
    msg = (ts + method.upper() + path).encode()
    private_key = serialization.load_pem_private_key(_load_private_key(), password=None)
    sig = private_key.sign(
        msg,
        padding.PSS(mgf=padding.MGF1(hashes.SHA256()), salt_length=padding.PSS.DIGEST_LENGTH),
        hashes.SHA256(),
    )
    return {
        "KALSHI-ACCESS-KEY": os.environ["KALSHI_KEY_ID"],
        "KALSHI-ACCESS-TIMESTAMP": ts,
        "KALSHI-ACCESS-SIGNATURE": base64.b64encode(sig).decode(),
    }


def list_markets(limit: int = 20, cursor: str | None = None, **filters) -> dict:
    """Returns {"markets": [...], "cursor": "..."}. Pass filters like status="open"."""
    path = "/trade-api/v2/markets"
    params = {"limit": limit, **filters}
    if cursor:
        params["cursor"] = cursor
    with httpx.Client(base_url=BASE_URL) as client:
        r = client.get("/markets", headers=_auth_headers("GET", path), params=params)
        r.raise_for_status()
        return r.json()


def get_market(ticker: str) -> dict:
    path = f"/trade-api/v2/markets/{ticker}"
    with httpx.Client(base_url=BASE_URL) as client:
        r = client.get(f"/markets/{ticker}", headers=_auth_headers("GET", path))
        r.raise_for_status()
        return r.json()["market"]


def get_candlesticks(ticker: str, days: int = 7) -> list[dict]:
    now = datetime.now(tz=timezone.utc)
    start_ts = int((now - timedelta(days=days)).timestamp())
    end_ts = int(now.timestamp())
    path = f"/trade-api/v2/series/{ticker}/markets/candlesticks"  # series-level endpoint
    # Fall back to market-level historical endpoint
    market_path = f"/trade-api/v2/historical/markets/{ticker}/candlesticks"
    params = {"start_ts": start_ts, "end_ts": end_ts, "period_interval": 1440}
    with httpx.Client(base_url=BASE_URL) as client:
        r = client.get(
            f"/historical/markets/{ticker}/candlesticks",
            headers=_auth_headers("GET", market_path),
            params=params,
        )
        r.raise_for_status()
        return r.json().get("candlesticks", [])


# ── Conversion helpers ────────────────────────────────────────────────────────

def _f(val) -> float:
    """All Kalshi numeric fields are returned as strings — centralise the cast."""
    return float(val or 0)


def candle_to_probability(candle: dict) -> float:
    """Extract mid-price from a candlestick. Kalshi prices are in dollar terms (0.01–0.99)."""
    price_block = candle.get("price", {}) or {}
    if "mean" in price_block:
        return _f(price_block["mean"])
    bid_close = _f((candle.get("yes_bid", {}) or {}).get("close", 0))
    ask_close = _f((candle.get("yes_ask", {}) or {}).get("close", 0))
    if bid_close and ask_close:
        return (bid_close + ask_close) / 2
    return _f(price_block.get("close", 0))


def candlesticks_to_sparkline(candles: list[dict]) -> list[SparklinePoint]:
    points = []
    for c in candles:
        date = datetime.fromtimestamp(c["end_period_ts"], tz=timezone.utc).strftime("%Y-%m-%d")
        points.append(SparklinePoint(date=date, probability=candle_to_probability(c)))
    return sorted(points, key=lambda p: p.date)


def market_to_card_fields(market: dict, candles: list[dict]) -> dict:
    """
    Map a Kalshi market + its candlesticks to the fields our StoryCard needs.
    summary, calibration_note, domain, and sources still need to be filled in
    externally (LLM or manual).
    """
    sparkline = candlesticks_to_sparkline(candles)

    bid = _f(market.get("yes_bid_dollars"))
    ask = _f(market.get("yes_ask_dollars"))
    current_prob = (bid + ask) / 2 if (bid and ask) else _f(market.get("last_price_dollars"))

    if len(sparkline) >= 2:
        probability_move = round(sparkline[-1].probability - sparkline[0].probability, 4)
    else:
        probability_move = 0.0

    volume = int(_f(market.get("volume_fp")))

    return {
        "id": market["ticker"].lower(),
        "platform": "Kalshi",
        "market_name": market.get("title", market["ticker"]),
        "headline": market.get("yes_sub_title") or market.get("title", ""),
        "current_probability": current_prob,
        "probability_move": probability_move,
        "volume_usd": volume,
        "sparkline": sparkline,
    }
