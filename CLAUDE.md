# PredictionNews

A news site that ranks stories by their impact on prediction markets — filtering out noise and surfacing news that materially changed people's view of the future.

## Vision
- News-first, prediction markets second. The market signal does the filtering; the reader doesn't need to think in odds.
- Three domain feeds (US-first): **Politics**, **World**, **Sports**
- Sorted by `|probability_move| × volume` over a rolling 7-day window
- Full vision and design spec in notes vault: `1 Me/PredictionNews/`

## Stack
- **Backend**: Python 3.11, FastAPI, Poetry — `poetry run uvicorn prediction_news.api:app --reload --port 8000`
- **Frontend**: React, Vite, TypeScript, Tailwind CSS — `cd frontend && npm run dev` (runs on :5173, proxies /api to :8000)
- **LLM**: Claude (Anthropic) for relevance scoring and summaries

## Current state
Prototype with mock data. No real API integrations yet.

## Card anatomy
Each story card: headline · 7-day sparkline · probability badge (e.g. `48% +14pts`) · LLM summary · calibration note · source links

## Causal attribution pipeline (planned)
1. Time-window + keyword retrieval (market entity matching against RSS/X)
2. LLM relevance scoring to rank candidates

## Notes vault
Vision and design docs live in OneDrive at `1 Me/PredictionNews/`. Start sessions with:
```
claude --add-dir "/Users/braypatrick/Library/CloudStorage/OneDrive-TheBostonConsultingGroup,Inc/Documents/Notes/MAIN/1 Me/PredictionNews/"
```
