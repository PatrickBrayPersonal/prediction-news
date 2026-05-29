from enum import Enum

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from prediction_news.config import settings
from prediction_news.feed import build_feed
from prediction_news.models import StoryCard

app = FastAPI(title="PredictionNews")

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
