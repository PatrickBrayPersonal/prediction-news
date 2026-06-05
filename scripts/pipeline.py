"""
Step-by-step pipeline for faster development iteration.

  pull-markets   Fetch all Kalshi markets per domain → data/pipeline/{date}/markets_{domain}.json
  pull-candles   Fetch candlesticks for qualifying markets → data/pipeline/{date}/candles_{domain}.json
  build-cards    Run LLM scoring and write feed → data/feeds/{domain}.json
  run            Execute all three steps in sequence

Usage:
  poetry run python scripts/pipeline.py pull-markets
  poetry run python scripts/pipeline.py pull-candles
  poetry run python scripts/pipeline.py build-cards
  poetry run python scripts/pipeline.py run
  poetry run python scripts/pipeline.py build-cards --domain sports --date 2026-06-04
  poetry run python scripts/pipeline.py build-cards --ticker KXELECTION-24-DEM --domain news
"""

import argparse
import asyncio
import csv
import dataclasses
import json
import re
import sys
import time
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
from loguru import logger

load_dotenv()

from prediction_news.config import settings
from prediction_news.feed import DOMAIN_CATEGORIES, _build_card, _build_card_from_candles
from prediction_news.kalshi import (
    get_all_markets,
    get_candlesticks,
    get_market,
    max_single_day_move,
    most_recent_qualifying_move,
)
from prediction_news.models import (
    CandleEntry,
    CandlesCheckpoint,
    MarketLogEntry,
    MarketsCheckpoint,
)
from prediction_news.ranking import filter_cards, rank_cards

_REPO_ROOT = Path(__file__).parent.parent
PIPELINE_DIR = _REPO_ROOT / "data" / "pipeline"
FEEDS_DIR = _REPO_ROOT / "data" / "feeds"
LOG_DIR = _REPO_ROOT / "logs"


def _setup_logging(now: datetime) -> None:
    day_dir = LOG_DIR / now.strftime("%Y-%m-%d")
    day_dir.mkdir(parents=True, exist_ok=True)
    log_file = day_dir / f"pipeline_{now.strftime('%H%M%SZ')}.log"
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


def _step_dir(date_str: str) -> Path:
    d = PIPELINE_DIR / date_str
    d.mkdir(parents=True, exist_ok=True)
    return d


def _markets_path(step_dir: Path, domain: str) -> Path:
    return step_dir / f"markets_{domain}.json"


def _candles_path(step_dir: Path, domain: str) -> Path:
    return step_dir / f"candles_{domain}.json"


def _staleness_warning(fetched_at: str, label: str, threshold_hours: float = 4.0) -> None:
    age = (
        datetime.now(timezone.utc) - datetime.fromisoformat(fetched_at)
    ).total_seconds() / 3600
    if age > threshold_hours:
        logger.warning(f"{label} checkpoint is {age:.1f}h old (threshold {threshold_hours}h)")


async def cmd_pull_markets(domains: list[str], date_str: str) -> None:
    t0 = time.perf_counter()
    logger.info("pull-markets: fetching all open markets from Kalshi...")
    all_markets = await get_all_markets()
    logger.info(
        f"pull-markets: {len(all_markets)} total markets"
        f" ({time.perf_counter() - t0:.1f}s)"
    )

    step_dir = _step_dir(date_str)
    for domain in domains:
        categories = DOMAIN_CATEGORIES.get(domain, [])
        if not categories:
            logger.warning(f"pull-markets: unknown domain={domain}, skipping")
            continue
        domain_cats = {c.casefold() for c in categories}
        markets = [
            m for m in all_markets
            if (m.get("category") or "").casefold() in domain_cats
        ]
        checkpoint = MarketsCheckpoint(
            fetched_at=datetime.now(timezone.utc).isoformat(),
            domain=domain,
            markets=markets,
        )
        path = _markets_path(step_dir, domain)
        path.write_text(checkpoint.model_dump_json(indent=2))
        logger.info(f"pull-markets: {domain} → {len(markets)} markets → {path}")


async def cmd_pull_candles(domains: list[str], date_str: str) -> None:
    step_dir = _step_dir(date_str)

    for domain in domains:
        path = _markets_path(step_dir, domain)
        if not path.exists():
            logger.error(f"pull-candles: {path} not found — run pull-markets first")
            sys.exit(1)

        markets_ckpt = MarketsCheckpoint.model_validate_json(path.read_text())
        _staleness_warning(markets_ckpt.fetched_at, f"pull-candles [{domain}] markets")

        qualifying = [
            m for m in markets_ckpt.markets
            if float(m.get("open_interest") or 0) >= settings.min_open_interest
        ]
        logger.info(
            f"pull-candles {domain}: {len(qualifying)}/{len(markets_ckpt.markets)}"
            f" markets pass OI filter (min={settings.min_open_interest})"
        )

        t0 = time.perf_counter()
        candle_results = await asyncio.gather(
            *[
                get_candlesticks(
                    m.get("ticker", ""),
                    m.get("series_ticker", ""),
                    days=settings.kalshi_lookback_days,
                )
                for m in qualifying
            ],
            return_exceptions=True,
        )
        logger.info(
            f"pull-candles {domain}: candle fetch done ({time.perf_counter() - t0:.1f}s)"
        )

        # Group by event_ticker, keep the market with the largest single-day move per event
        event_groups: dict[str, list[tuple[dict, list[dict]]]] = defaultdict(list)
        failed = 0
        for m, result in zip(qualifying, candle_results):
            if isinstance(result, Exception) or not result:
                failed += 1
                continue
            key = m.get("event_ticker") or m.get("ticker", "")
            event_groups[key].append((m, result))

        if failed:
            logger.warning(f"pull-candles {domain}: {failed} candle fetches failed")

        entries: list[CandleEntry] = []
        skipped_move = 0
        for group in event_groups.values():
            best_market, best_candles = max(
                group, key=lambda pair: max_single_day_move(pair[1])
            )
            move, change_at = most_recent_qualifying_move(
                best_candles, settings.min_probability_move
            )
            if not change_at:
                skipped_move += 1
                continue
            entries.append(
                CandleEntry(
                    market=best_market,
                    candles=best_candles,
                    probability_move=move,
                    change_at=change_at.isoformat(),
                )
            )

        logger.info(
            f"pull-candles {domain}: {len(entries)} entries after dedup + move filter"
            f" (skipped {skipped_move} below min_move={settings.min_probability_move})"
        )

        candles_ckpt = CandlesCheckpoint(
            fetched_at=datetime.now(timezone.utc).isoformat(),
            domain=domain,
            entries=entries,
        )
        out = _candles_path(step_dir, domain)
        out.write_text(candles_ckpt.model_dump_json(indent=2))
        logger.info(f"pull-candles: {domain} → {len(entries)} entries → {out}")


async def cmd_build_cards(domains: list[str], date_str: str) -> None:
    step_dir = _step_dir(date_str)
    now = datetime.now(timezone.utc)
    run_timestamp = now.isoformat()
    FEEDS_DIR.mkdir(parents=True, exist_ok=True)

    for domain in domains:
        path = _candles_path(step_dir, domain)
        if not path.exists():
            logger.error(f"build-cards: {path} not found — run pull-candles first")
            sys.exit(1)

        candles_ckpt = CandlesCheckpoint.model_validate_json(path.read_text())
        _staleness_warning(candles_ckpt.fetched_at, f"build-cards [{domain}] candles")

        logger.info(f"build-cards {domain}: processing {len(candles_ckpt.entries)} entries")
        t0 = time.perf_counter()

        results = await asyncio.gather(
            *[
                _build_card_from_candles(
                    market=entry.market,
                    candles=entry.candles,
                    probability_move=entry.probability_move,
                    change_at=datetime.fromisoformat(entry.change_at),
                    domain=domain,
                    run_timestamp=run_timestamp,
                )
                for entry in candles_ckpt.entries
            ],
            return_exceptions=True,
        )

        errors = [r for r in results if isinstance(r, Exception)]
        pairs = [r for r in results if not isinstance(r, Exception)]
        cards = [card for card, _ in pairs if card is not None]
        log_entries: list[MarketLogEntry] = [entry for _, entry in pairs]

        if errors:
            for exc in errors:
                logger.exception("build-cards: card raised exception", exc_info=exc)
            logger.warning(f"build-cards {domain}: {len(errors)} cards failed")

        ranked = rank_cards(
            filter_cards(
                cards,
                min_move=settings.min_probability_move,
                min_open_interest=settings.min_open_interest,
            )
        )
        logger.info(
            f"build-cards {domain}: {len(ranked)}/{len(candles_ckpt.entries)} cards"
            f" ranked ({time.perf_counter() - t0:.1f}s)"
        )

        feed_path = FEEDS_DIR / f"{domain}.json"
        feed_path.write_text(json.dumps([c.model_dump() for c in ranked], indent=2))
        logger.info(f"build-cards: {domain} → {feed_path}")

        if log_entries:
            log_dir = LOG_DIR / now.strftime("%Y-%m-%d")
            log_dir.mkdir(parents=True, exist_ok=True)
            csv_path = log_dir / f"cards_{domain}_{now.strftime('%H%M%SZ')}.csv"
            fields = [f.name for f in dataclasses.fields(MarketLogEntry)]
            with csv_path.open("w", newline="") as fh:
                writer = csv.DictWriter(fh, fieldnames=fields)
                writer.writeheader()
                for e in log_entries:
                    writer.writerow(dataclasses.asdict(e))
            logger.info(f"build-cards: log → {csv_path}")

    FEEDS_DIR.joinpath("last_updated.json").write_text(
        json.dumps({"last_updated": now.isoformat()})
    )


async def cmd_build_ticker(ticker: str, domain: str, now: datetime) -> None:
    t0 = time.perf_counter()
    market = await get_market(ticker)
    if not market:
        logger.error(f"build-cards --ticker: market not found: {ticker}")
        sys.exit(1)
    if not market.get("series_ticker"):
        event_ticker = market.get("event_ticker", "")
        m = re.match(r"^(.+)-\d+$", event_ticker)
        if m:
            market = {**market, "series_ticker": m.group(1)}

    card, log_entry = await _build_card(market, domain, now.isoformat())

    log_dir = LOG_DIR / now.strftime("%Y-%m-%d")
    log_dir.mkdir(parents=True, exist_ok=True)
    csv_path = log_dir / f"cards_{ticker}_{now.strftime('%H%M%SZ')}.csv"
    fields = [f.name for f in dataclasses.fields(MarketLogEntry)]
    with csv_path.open("w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        writer.writerow(dataclasses.asdict(log_entry))
    logger.info(f"build-cards --ticker: log → {csv_path}")

    if card is None:
        logger.info(f"build-cards --ticker: no card built for {ticker} (filtered out or no data)")
        return

    FEEDS_DIR.mkdir(parents=True, exist_ok=True)
    path = FEEDS_DIR / f"{domain}-{ticker}.json"
    path.write_text(json.dumps([card.model_dump()], indent=2))
    logger.info(f"build-cards --ticker: 1 card → {path} ({time.perf_counter() - t0:.1f}s)")


async def main() -> None:
    parser = argparse.ArgumentParser(
        description="Stepped prediction news pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "step",
        choices=["pull-markets", "pull-candles", "build-cards", "run"],
    )
    parser.add_argument(
        "--domain",
        default=",".join(settings.feed_domains_list),
        help="Comma-separated domains (default: all configured domains)",
    )
    parser.add_argument(
        "--date",
        default=datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        help="Checkpoint date directory YYYY-MM-DD (default: today)",
    )
    parser.add_argument(
        "--ticker",
        help="Build a single card for this market ticker (only valid with build-cards)",
    )
    args = parser.parse_args()

    if args.ticker and args.step != "build-cards":
        parser.error("--ticker is only valid with the build-cards step")

    _setup_logging(datetime.now(timezone.utc))
    domains = [d.strip() for d in args.domain.split(",") if d.strip()]
    now = datetime.now(timezone.utc)

    if args.step == "pull-markets":
        await cmd_pull_markets(domains, args.date)
    elif args.step == "pull-candles":
        await cmd_pull_candles(domains, args.date)
    elif args.step == "build-cards":
        if args.ticker:
            domain = domains[0] if domains else "news"
            await cmd_build_ticker(args.ticker, domain, now)
        else:
            await cmd_build_cards(domains, args.date)
    elif args.step == "run":
        await cmd_pull_markets(domains, args.date)
        await cmd_pull_candles(domains, args.date)
        await cmd_build_cards(domains, args.date)


if __name__ == "__main__":
    asyncio.run(main())
