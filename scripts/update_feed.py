import argparse
import asyncio
import csv
import dataclasses
import json
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from loguru import logger

from prediction_news.config import settings
from prediction_news.feed import _build_card, build_feed
from prediction_news.kalshi import get_market
from prediction_news.models import MarketLogEntry

LOG_DIR = Path(__file__).parent.parent / "logs"
DATA_DIR = Path(__file__).parent.parent / "data" / "feeds"
DOMAINS = settings.feed_domains_list


def _setup_logging(now: datetime) -> Path:
    day_dir = LOG_DIR / now.strftime("%Y-%m-%d")
    day_dir.mkdir(parents=True, exist_ok=True)
    log_file = day_dir / f"update_feed_{now.strftime('%H%M%SZ')}.log"

    logger.remove()
    logger.add(
        sys.stderr,
        format="{time:HH:mm:ss} {level:<8} {name}  {message}",
        level="INFO",
    )
    logger.add(
        log_file,
        format="{time:YYYY-MM-DD HH:mm:ss} {level} {message}",
        level="INFO",
    )
    logger.info(f"Logging to {log_file}")
    return day_dir


def _write_market_log_csv(entries: list[MarketLogEntry], csv_path: Path) -> None:
    if not entries:
        return
    fields = [f.name for f in dataclasses.fields(MarketLogEntry)]
    with csv_path.open("w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        for entry in entries:
            writer.writerow(dataclasses.asdict(entry))
    logger.info(f"Market log written to {csv_path} ({len(entries)} rows)")


async def _run_ticker(ticker: str, domain: str, now: datetime) -> None:
    t0 = time.perf_counter()
    market = await get_market(ticker)
    if not market:
        logger.error(f"Market not found: {ticker}")
        sys.exit(1)
    if not market.get("series_ticker"):
        event_ticker = market.get("event_ticker", "")
        match = re.match(r"^(.+)-\d+$", event_ticker)
        if match:
            market = {**market, "series_ticker": match.group(1)}
    card, log_entry = await _build_card(market, domain, now.isoformat())
    day_dir = LOG_DIR / now.strftime("%Y-%m-%d")
    csv_path = day_dir / f"market_log_{now.strftime('%H%M%SZ')}.csv"
    _write_market_log_csv([log_entry], csv_path)
    if card is None:
        logger.info(f"No card built for {ticker} (filtered out or insufficient data)")
        return
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    path = DATA_DIR / f"{domain}-{ticker}.json"
    path.write_text(json.dumps([card.model_dump()], indent=2))
    elapsed = time.perf_counter() - t0
    logger.info(f"  1 card → {path} ({elapsed:.1f}s)")


async def _run_all(now: datetime, domains: list[str] = DOMAINS) -> None:
    t0 = time.perf_counter()
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    all_log_entries: list[MarketLogEntry] = []

    for domain in domains:
        logger.info(f"Building {domain}...")
        t1 = time.perf_counter()
        cards, log_entries = await build_feed(domain)
        all_log_entries.extend(log_entries)
        path = DATA_DIR / f"{domain}.json"
        path.write_text(json.dumps([c.model_dump() for c in cards], indent=2))
        logger.info(f"  {len(cards)} cards → {path} ({time.perf_counter() - t1:.1f}s)")

    (DATA_DIR / "last_updated.json").write_text(
        json.dumps({"last_updated": datetime.now(timezone.utc).isoformat()})
    )

    day_dir = LOG_DIR / now.strftime("%Y-%m-%d")
    csv_path = day_dir / f"market_log_{now.strftime('%H%M%SZ')}.csv"
    _write_market_log_csv(all_log_entries, csv_path)

    logger.info(f"Done. ({time.perf_counter() - t0:.1f}s total)")


async def main() -> None:
    parser = argparse.ArgumentParser(description="Update prediction news feed")
    parser.add_argument("--ticker", help="Build a single card for this market ticker")
    parser.add_argument(
        "--domain",
        default="news",
        choices=["sports", "news"],
        help="Domain for RSS article lookup when --ticker is used (default: politics)",
    )
    args = parser.parse_args()
    now = datetime.now(timezone.utc)
    _setup_logging(now)
    domains = DOMAINS if not args.domain else [args.domain]

    if args.ticker:
        await _run_ticker(args.ticker, args.domain, now)
    else:
        await _run_all(now, domains=domains)


if __name__ == "__main__":
    asyncio.run(main())
