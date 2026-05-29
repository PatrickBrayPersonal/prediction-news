#!/usr/bin/env python3
"""
Smoke test for the Kalshi API connection and field mapping.

Usage:
    # List open markets to find real tickers:
    poetry run python scripts/check_kalshi.py

    # Then inspect + map a specific ticker:
    poetry run python scripts/check_kalshi.py TICKER
"""
import sys
import json
from dotenv import load_dotenv

load_dotenv()

from prediction_news.kalshi import list_markets, get_market, get_candlesticks, market_to_card_fields

if len(sys.argv) < 2:
    # Try a few different queries to find useful markets
    SERIES_TO_TRY = [
        # Sports
        "KXNBA", "KXMLB", "KXNFL", "KXNHL", "KXSOCCER",
        # Politics / macro
        "KXFED", "KXPOL", "KXGOV", "KXCONGRESS", "KXBUDGET",
        "KXSENATE", "KXHOUSE", "KXELECT", "KXTARIFF", "KXAPPROVAL",
        "KXTRUMP", "KXECON",
        # Finance / world
        "KXINXD", "KXBTC", "KXWORLD",
        # Old-style unprefixed (fallback)
        "FED", "PRES", "INXD",
    ]
    found = []

    for series in SERIES_TO_TRY:
        result = list_markets(limit=100, series_ticker=series, status="open")
        batch = result.get("markets", [])
        if not batch:
            continue

        # Collapse strike ladders: keep only the highest-volume market per event
        by_event: dict[str, dict] = {}
        for m in batch:
            event = m.get("event_ticker", m["ticker"])
            vol = float(m.get("volume_fp") or 0)
            if event not in by_event or vol > float(by_event[event].get("volume_fp") or 0):
                by_event[event] = m

        top = sorted(by_event.values(), key=lambda m: float(m.get("volume_fp") or 0), reverse=True)[:5]
        print(f"── {series} ({'─' * (44 - len(series))})")
        for m in top:
            vol = float(m.get("volume_fp") or 0)
            bid = float(m.get("yes_bid_dollars") or 0)
            ask = float(m.get("yes_ask_dollars") or 0)
            mid = (bid + ask) / 2
            print(f"  {m['ticker']:<48} {mid:>5.0%}  vol=${vol:>10,.0f}  {m.get('title', '')[:35]}")
        found.extend(top)

    if not found:
        print("No markets found via series lookup. Falling back to open-market list…")
        result = list_markets(limit=200)
        markets = result.get("markets", [])
        parlay_prefixes = ("KXMVE", "KXMVECROSS")
        markets = [m for m in markets if not any(m["ticker"].startswith(p) for p in parlay_prefixes)]
        markets.sort(key=lambda m: m.get("volume", 0), reverse=True)
        print(f"  {len(markets)} non-parlay markets found out of {len(result.get('markets', []))} total")
        for m in markets[:30]:
            vol = m.get("volume", 0)
            print(f"  {m['ticker']:<50} vol={vol:<8} {m.get('title', '')[:50]}")

    print("\nRe-run with a ticker to inspect it:")
    print("  poetry run python scripts/check_kalshi.py <TICKER>")
    sys.exit(0)

ticker = sys.argv[1]
print(f"Fetching market: {ticker}\n")

market = get_market(ticker)
print("── Raw market fields ──────────────────────────────────")
interesting = {k: market[k] for k in (
    "ticker", "title", "yes_sub_title", "yes_bid", "yes_ask",
    "last_price", "volume", "volume_fp", "open_time", "close_time",
) if k in market}
print(json.dumps(interesting, indent=2))

print("\n── Candlesticks (last 7 days) ─────────────────────────")
candles = get_candlesticks(ticker, days=7)
print(f"{len(candles)} candles returned")
if candles:
    print("First candle:", json.dumps(candles[0], indent=2))
    print("Last candle: ", json.dumps(candles[-1], indent=2))

print("\n── Mapped card fields ─────────────────────────────────")
card = market_to_card_fields(market, candles)
card["sparkline"] = [p.model_dump() for p in card["sparkline"]]
print(json.dumps(card, indent=2))

print("\n── Fields still needed (filled by LLM / pipeline) ────")
print("  domain, summary, calibration_note, sources")
