import logging
from enum import Enum

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from prediction_news.config import settings
from prediction_news.feed import build_feed
from prediction_news.models import StoryCard

logger = logging.getLogger(__name__)

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
    return await build_feed(domain.value)
