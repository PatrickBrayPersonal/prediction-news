import json
import sys
from enum import Enum
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from prediction_news.config import settings
from prediction_news.models import StoryCard

DATA_DIR = Path(__file__).parent.parent / "data" / "feeds"

logger.remove()
logger.add(sys.stderr, format="{time:HH:mm:ss} {level:<8} {name}  {message}", level="INFO")

app = FastAPI(title="PredictionNews")


@app.on_event("startup")
async def _check_config() -> None:
    if not settings.kalshi_key_id:
        logger.warning("KALSHI_KEY_ID is not set — all Kalshi requests will 401")


app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_methods=["GET"],
    allow_headers=["*"],
)


class Domain(str, Enum):
    politics = "politics"
    world = "world"
    sports = "sports"


@app.get("/api/feeds/{domain}", response_model=list[StoryCard])
async def get_feed(domain: Domain) -> list[StoryCard]:
    path = DATA_DIR / f"{domain.value}.json"
    if not path.exists():
        return []
    data = json.loads(path.read_text())
    return [StoryCard.model_validate(card) for card in data]


@app.get("/api/last_updated")
async def get_last_updated() -> dict:
    path = DATA_DIR / "last_updated.json"
    if not path.exists():
        return {"last_updated": None}
    return json.loads(path.read_text())
