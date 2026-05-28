from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from models import StoryCard
from mock_data import MOCK_CARDS

app = FastAPI(title="Prediction News API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["GET"],
    allow_headers=["*"],
)

VALID_DOMAINS = {"politics", "world", "sports"}


@app.get("/api/feeds/{domain}", response_model=list[StoryCard])
def get_feed(domain: str) -> list[StoryCard]:
    if domain not in VALID_DOMAINS:
        raise HTTPException(status_code=404, detail=f"Unknown domain: {domain}")
    cards = [c for c in MOCK_CARDS if c.domain == domain]
    return sorted(cards, key=lambda c: abs(c.probability_move) * c.volume_usd, reverse=True)
