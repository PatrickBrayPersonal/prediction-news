"""
Export Kalshi market probability and volume history to CSV.

Usage:
    poetry run python scripts/export_market_history.py
    poetry run python scripts/export_market_history.py --days 30 --category politics
    poetry run python scripts/export_market_history.py --days 90 --all-markets

Outputs: data/market_history_YYYYMMDD_HHMMSS.csv
Columns: ticker, series_ticker, title, date, probability, volume_usd
"""

import argparse
import asyncio
import csv
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv
from loguru import logger

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))
load_dotenv(ROOT / ".env")

from prediction_news.kalshi import (  # noqa: E402
    _auth_headers,
    _candle_mid_price,
    _fetch_candlesticks,
    _SEMAPHORE,
    list_markets,
    list_markets_by_category,
)

import httpx  # noqa: E402

KALSHI_BASE = "https://external-api.kalshi.com/trade-api/v2"


async def _fetch_all_markets_paginated(limit: int = 1_000) -> list[dict]:
    """Fetch all open markets with pagination."""
    all_markets: list[dict] = []
    cursor: str | None = None
    page = 0

    async with httpx.AsyncClient(base_url=KALSHI_BASE) as client:
        while True:
            path = "/trade-api/v2/markets"
            params: dict[str, str] = {"status": "open", "limit": str(limit)}
            if cursor:
                params["cursor"] = cursor

            async with _SEMAPHORE:
                response = await client.get(
                    "/markets",
                    params=params,
                    headers=_auth_headers("GET", path),
                )
                response.raise_for_status()
                body = response.json()

            batch = body.get("markets", [])
            all_markets.extend(batch)
            page += 1
            logger.info(
                f"Page {page}: fetched {len(batch)} markets (total {len(all_markets)})"
            )

            cursor = body.get("cursor")
            if not cursor or len(batch) < limit:
                break

    return all_markets


async def fetch_candles_for_market(
    market: dict,
    days: int,
) -> list[dict]:
    """Return flat row dicts for one market across all candle periods."""
    ticker: str = market.get("ticker", "")
    series_ticker: str = market.get("series_ticker", "")
    title: str = market.get("title", "")
    yes_sub: str = market.get("yes_sub_title", "").strip()
    if yes_sub and "  " in title:
        title = title.replace("  ", f" {yes_sub} ", 1)

    if not series_ticker:
        logger.debug(f"Skipping {ticker}: no series_ticker")
        return []

    end_ts = int(time.time())
    start_ts = end_ts - days * 86_400
    params = {
        "start_ts": str(start_ts),
        "end_ts": str(end_ts),
        "period_interval": "1440",
    }

    try:
        candles = await _fetch_candlesticks(ticker, series_ticker, params)
    except Exception as exc:
        logger.warning(f"{ticker}: candlestick fetch failed — {exc}")
        return []

    rows = []
    for i, candle in enumerate(candles):
        ts = candle.get("end_period_ts", 0)
        date = datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d")
        prob = round(min(max(_candle_mid_price(candle), 0.0), 1.0), 4)
        prev_prob = (
            round(min(max(_candle_mid_price(candles[i - 1]), 0.0), 1.0), 4)
            if i > 0
            else None
        )
        day_change = round(prob - prev_prob, 4) if prev_prob is not None else None
        volume = float(candle.get("volume_fp") or 0)
        open_interest = float(candle.get("open_interest_fp") or 0)
        rows.append(
            {
                "ticker": ticker,
                "series_ticker": series_ticker,
                "title": title,
                "yes_sub_title": yes_sub,
                "date": date,
                "probability": prob,
                "day_change": day_change,
                "volume_usd": round(volume, 2),
                "open_interest": round(open_interest, 2),
            }
        )

    logger.debug(f"{ticker}: {len(rows)} candle rows")
    return rows


async def main(days: int, category: str | None, all_markets: bool) -> None:
    logger.info(
        f"Fetching markets (days={days}, category={category}, all={all_markets})"
    )

    if all_markets:
        markets = await _fetch_all_markets_paginated()
    elif category:
        markets = await list_markets_by_category(category)
    else:
        markets = await list_markets()

    logger.info(f"Got {len(markets)} markets — fetching candlesticks...")

    BATCH = 20
    all_rows: list[dict] = []
    for i in range(0, len(markets), BATCH):
        batch = markets[i : i + BATCH]
        results = await asyncio.gather(
            *[fetch_candles_for_market(m, days) for m in batch],
            return_exceptions=True,
        )
        for result in results:
            if isinstance(result, Exception):
                logger.warning(f"Batch error: {result}")
            else:
                all_rows.extend(result)
        logger.info(
            f"Progress: {min(i + BATCH, len(markets))}/{len(markets)} markets processed"
        )

    if not all_rows:
        logger.error("No rows collected — check credentials and market availability")
        sys.exit(1)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path = ROOT / "data" / f"market_history_{timestamp}.csv"
    out_path.parent.mkdir(parents=True, exist_ok=True)

    fieldnames = [
        "ticker",
        "series_ticker",
        "title",
        "yes_sub_title",
        "date",
        "probability",
        "day_change",
        "volume_usd",
        "open_interest",
    ]
    with open(out_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(all_rows)

    markets_covered = len({r["ticker"] for r in all_rows})
    logger.info(
        f"Wrote {len(all_rows)} rows for {markets_covered} markets → {out_path}"
    )
    print(
        f"\nExported {len(all_rows):,} rows ({markets_covered} markets) to:\n  {out_path}"
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Export Kalshi market history to CSV")
    parser.add_argument(
        "--days", type=int, default=30, help="Lookback window in days (default: 30)"
    )
    parser.add_argument(
        "--category", type=str, default=None, help="Kalshi category (e.g. politics)"
    )
    parser.add_argument(
        "--all-markets", action="store_true", help="Paginate through all open markets"
    )
    args = parser.parse_args()

    asyncio.run(
        main(days=args.days, category=args.category, all_markets=args.all_markets)
    )
