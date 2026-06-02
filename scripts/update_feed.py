import argparse
import asyncio
import json
import logging
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from prediction_news.config import settings
from prediction_news.feed import _build_card, build_feed
from prediction_news.kalshi import get_market

LOG_DIR = Path(__file__).parent.parent / "logs"
DATA_DIR = Path(__file__).parent.parent / "data" / "feeds"
DOMAINS = settings.feed_domains_list


def _setup_logging() -> logging.Logger:
    now = datetime.now(timezone.utc)
    day_dir = LOG_DIR / now.strftime("%Y-%m-%d")
    day_dir.mkdir(parents=True, exist_ok=True)
    log_file = day_dir / f"update_feed_{now.strftime('%H%M%SZ')}.log"

    logger = logging.getLogger("update_feed")
    logger.setLevel(logging.INFO)

    fmt = logging.Formatter("%(asctime)s %(levelname)s %(message)s")

    file_handler = logging.FileHandler(log_file)
    file_handler.setFormatter(fmt)
    logger.addHandler(file_handler)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(logging.Formatter("%(message)s"))
    logger.addHandler(console_handler)

    logger.info("Logging to %s", log_file)
    return logger


async def _run_ticker(ticker: str, domain: str, log: logging.Logger) -> None:
    t0 = time.perf_counter()
    market = await get_market(ticker)
    if not market:
        log.error("Market not found: %s", ticker)
        sys.exit(1)
    if not market.get("series_ticker"):
        event_ticker = market.get("event_ticker", "")
        match = re.match(r"^(.+)-\d+$", event_ticker)
        if match:
            market = {**market, "series_ticker": match.group(1)}
    card = await _build_card(market, domain)
    if card is None:
        log.info("No card built for %s (filtered out or insufficient data)", ticker)
        return
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    path = DATA_DIR / f"{domain}-{ticker}.json"
    path.write_text(json.dumps([card.model_dump()], indent=2))
    elapsed = time.perf_counter() - t0
    log.info("  1 card → %s (%.1fs)", path, elapsed)


async def _run_all(log: logging.Logger) -> None:
    t0 = time.perf_counter()
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    for domain in DOMAINS:
        log.info("Building %s...", domain)
        t1 = time.perf_counter()
        cards = await build_feed(domain)
        path = DATA_DIR / f"{domain}.json"
        path.write_text(json.dumps([c.model_dump() for c in cards], indent=2))
        log.info("  %d cards → %s (%.1fs)", len(cards), path, time.perf_counter() - t1)
    (DATA_DIR / "last_updated.json").write_text(
        json.dumps({"last_updated": datetime.now(timezone.utc).isoformat()})
    )
    log.info("Done. (%.1fs total)", time.perf_counter() - t0)


async def main() -> None:
    parser = argparse.ArgumentParser(description="Update prediction news feed")
    parser.add_argument("--ticker", help="Build a single card for this market ticker")
    parser.add_argument(
        "--domain",
        default="politics",
        choices=["politics", "world", "sports"],
        help="Domain for RSS article lookup when --ticker is used (default: politics)",
    )
    args = parser.parse_args()
    log = _setup_logging()

    if args.ticker:
        await _run_ticker(args.ticker, args.domain, log)
    else:
        await _run_all(log)


if __name__ == "__main__":
    asyncio.run(main())
