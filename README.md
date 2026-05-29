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
