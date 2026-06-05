# PredictionNews

A news site that surfaces stories by the size of their impact on prediction markets. Instead of recency or clicks, the feed is ranked by how much a story actually moved the odds — filtering out noise and highlighting news that materially changed people's view of the future.

## How it works

1. **Market move detection** — prediction market APIs (Kalshi, Polymarket) are polled for price changes over a rolling 7-day window
2. **Candidate retrieval** — for each significant move, articles are pulled from RSS feeds and X posts that match the market's entity keywords within a time window before the move
3. **LLM ranking** — candidate articles are scored by causal relevance to the price move
4. **Calibration** — each story card includes a note contextualizing how much to update based on the move (the site's editorial signature)

Stories are ranked by `|probability_move| × volume` — a proxy for "interestingness" that weights moves in high-liquidity markets more heavily than thin ones.

## Stack

- **Backend** — Python, FastAPI, Poetry
- **Frontend** — React, Vite, TypeScript, Tailwind CSS
- **LLM** — Claude (Anthropic) for relevance scoring and summaries
- **Data** — Kalshi + Polymarket APIs, RSS feeds, X API

## Running locally

```bash
# Backend
poetry install
poetry run uvicorn prediction_news.api:app --reload --port 8000

# Frontend
cd frontend
npm install
npm run dev  # http://localhost:5173/
```

Vite proxies `/api` → `http://localhost:8000`.

## Feed pipeline

The feed is built by `scripts/pipeline.py`, which breaks the process into three independently runnable steps. This lets you iterate on scoring logic without re-fetching market data on every run.

### Steps

| Step | Command | What it does |
|---|---|---|
| 1 | `pull-markets` | Paginates Kalshi events + markets, writes `data/pipeline/{date}/markets_{domain}.json` |
| 2 | `pull-candles` | Applies open-interest filter, fetches candlestick data, deduplicates by event, writes `data/pipeline/{date}/candles_{domain}.json` |
| 3 | `build-cards` | Reads cached candles, fetches articles, runs LLM scoring, writes `data/feeds/{domain}.json` |

### Usage

```bash
# Full run (all three steps)
poetry run python scripts/pipeline.py run

# Run steps individually
poetry run python scripts/pipeline.py pull-markets
poetry run python scripts/pipeline.py pull-candles
poetry run python scripts/pipeline.py build-cards

# Iterate on scoring without re-fetching market data
poetry run python scripts/pipeline.py build-cards

# Single domain or specific date
poetry run python scripts/pipeline.py build-cards --domain sports
poetry run python scripts/pipeline.py build-cards --date 2026-06-04 --domain news
```

Steps 1 and 2 hit the Kalshi API. Step 3 only calls the Anthropic API and local RSS feeds — re-running it is fast and cheap. Checkpoints warn if they are more than 4 hours old.

### Debug a single ticker

```bash
poetry run python scripts/pipeline.py build-cards --ticker KXELECTION-24-DEM --domain news
```

Fetches the market directly from Kalshi (no checkpoint needed) and writes one card to `data/feeds/news-{ticker}.json`. Useful for checking why a specific market isn't appearing in the feed.

### Output

| File | Contents |
|---|---|
| `data/feeds/news.json` | Ranked story cards for the news feed |
| `data/feeds/sports.json` | Ranked story cards for the sports feed |
| `data/feeds/last_updated.json` | ISO timestamp of the last completed run |
| `data/pipeline/{date}/markets_{domain}.json` | Raw market checkpoint from step 1 |
| `data/pipeline/{date}/candles_{domain}.json` | Candle checkpoint from step 2 |
| `logs/{date}/` | Per-run log files and market-level CSV audit trail |
