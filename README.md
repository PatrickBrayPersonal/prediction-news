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

**Prerequisites:** Python 3.11+, Node 18+, Poetry

```bash
# Backend (terminal 1)
cd prediction-news
poetry install
poetry run uvicorn prediction_news.api:app --reload --port 8000

# Frontend (terminal 2)
cd prediction-news/frontend
npm install
npm run dev
```

Open http://localhost:5173

The frontend proxies `/api` requests to the backend at `:8000`, so no CORS config needed in dev.

## Project structure

```
prediction-news/
  prediction_news/
    api.py         # FastAPI app — GET /api/feeds/{domain}
    models.py      # Pydantic schemas (StoryCard, SparklinePoint, Source)
    mock_data.py   # Fixture data for prototype (9 cards across 3 domains)
  frontend/
    src/
      App.tsx                    # Root — tab nav + feed
      types.ts                   # TypeScript types
      hooks/useFeed.ts           # Fetch hook
      components/
        StoryCard.tsx            # Card: headline, sparkline, summary, sources
        Sparkline.tsx            # Pure SVG 7-day probability chart
```

## Story card anatomy

Each card shows:
- **Headline** — market question rewritten as plain-language news
- **Sparkline** — 7-day probability chart (green = moved up, red = moved down)
- **Probability badge** — current odds + signed point move (e.g. `48% +14pts`)
- **Summary** — 2–3 sentence synthesis of what happened
- **Calibration note** — how much to actually update based on this move
- **Source links** — RSS articles and X posts that explain the move

## Feeds

| Domain   | Scope |
|----------|-------|
| Politics | US federal policy, elections, monetary policy |
| World    | International events with US-relevant market exposure |
| Sports   | Game outcomes, championship odds, player news |
