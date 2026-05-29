# PredictionNews

A news aggregator that ranks stories by their impact on prediction markets. The feed is ordered by `|probability_move| × volume` — filtering noise and surfacing news that materially changed people's view of the future.

## Architecture

**Backend** — Python 3.11+, FastAPI, Poetry
**Frontend** — React, Vite, TypeScript, Tailwind CSS
**LLM** — Claude (Anthropic) via `anthropic` SDK for relevance scoring and story summaries
**Data sources** — Kalshi API, Polymarket API, RSS feeds, X API

## How the pipeline works

1. Poll Kalshi + Polymarket for price changes over a rolling 7-day window
2. For each significant move, retrieve candidate articles from RSS feeds and X posts matching the market's entity keywords within a time window before the move
3. Score candidates with Claude for causal relevance to the price move
4. Attach a calibration note contextualizing the size of the move
5. Rank by `|probability_move| × volume`

## Project structure

```
prediction_news/      # FastAPI app
  api/                # Route handlers
  services/           # Market polling, article retrieval, LLM scoring
  models/             # Pydantic schemas
scripts/              # One-off data tasks
frontend/             # React + Vite app
  src/
    components/       # UI components
    hooks/            # Custom React hooks
    pages/            # Route-level components
```

## Key conventions

- All API endpoints return typed Pydantic models — no raw dicts
- LLM calls go through a single service layer (`services/llm.py`) — never call the Anthropic SDK directly from routes
- Market polling is async — use `httpx.AsyncClient`, not `requests`
- Article retrieval and LLM scoring run concurrently with `asyncio.gather` where possible
- Frontend fetches are typed with `zod` schemas matching backend response shapes

## LLM usage guidelines

- Use `claude-haiku-4-5` for pre-filtering candidates (cheap, fast)
- Use `claude-sonnet-4-6` for final relevance scoring and summary generation
- Always set a `max_tokens` budget per call — never leave it open-ended
- Batch article scoring where possible — avoid one API call per article
- Log token usage per pipeline run for cost tracking

## Environment variables

```
ANTHROPIC_API_KEY=
KALSHI_API_KEY=
POLYMARKET_API_KEY=
X_BEARER_TOKEN=
DATABASE_URL=
```

## Running locally

```bash
# Backend
poetry install
poetry run uvicorn prediction_news.main:app --reload

# Frontend
cd frontend
npm install
npm run dev
```

## Testing

- Backend: `poetry run pytest` — aim for 80%+ coverage on scoring and ranking logic
- Frontend: `npm run test`
- Write tests before implementing ranking or scoring changes (TDD)

## Security notes

- All external API keys in environment variables only — never hardcoded or logged
- Validate and sanitize all RSS/X content before passing to LLM prompts (prompt injection risk)
- Rate-limit outbound requests to market APIs — respect their terms
