import argparse
import asyncio
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from prediction_news.config import settings
from prediction_news.feed import _build_card, build_feed
from prediction_news.kalshi import get_market

DATA_DIR = Path(__file__).parent.parent / "data" / "feeds"
DOMAINS = settings.feed_domains_list


async def _run_ticker(ticker: str, domain: str) -> None:
    market = await get_market(ticker)
    if not market:
        print(f"Market not found: {ticker}", file=sys.stderr)
        sys.exit(1)
    if not market.get("series_ticker"):
        event_ticker = market.get("event_ticker", "")
        match = re.match(r"^(.+)-\d+$", event_ticker)
        if match:
            market = {**market, "series_ticker": match.group(1)}
    card = await _build_card(market, domain)
    if card is None:
        print(f"No card built for {ticker} (filtered out or insufficient data)")
        return
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    path = DATA_DIR / f"{domain}-{ticker}.json"
    path.write_text(json.dumps(card.model_dump(), indent=2))
    print(f"  1 card → {path}")


async def _run_all() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    for domain in DOMAINS:
        print(f"Building {domain}...", flush=True)
        cards = await build_feed(domain)
        path = DATA_DIR / f"{domain}.json"
        path.write_text(json.dumps([c.model_dump() for c in cards], indent=2))
        print(f"  {len(cards)} cards → {path}")
    (DATA_DIR / "last_updated.json").write_text(
        json.dumps({"last_updated": datetime.now(timezone.utc).isoformat()})
    )
    print("Done.")


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

    if args.ticker:
        await _run_ticker(args.ticker, args.domain)
    else:
        await _run_all()


if __name__ == "__main__":
    asyncio.run(main())
