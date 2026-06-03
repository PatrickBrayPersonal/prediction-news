from dataclasses import dataclass
from typing import Literal

from pydantic import BaseModel, field_validator


class SparklinePoint(BaseModel):
    date: str
    probability: float

    @field_validator("probability")
    @classmethod
    def probability_in_range(cls, v: float) -> float:
        if not 0.0 <= v <= 1.0:
            raise ValueError("probability must be between 0 and 1")
        return v


class Source(BaseModel):
    title: str
    url: str
    type: Literal["rss", "twitter", "manual"]
    published_at: str | None = None
    excerpt: str | None = None


class StoryCard(BaseModel):
    id: str
    domain: Literal["politics", "world", "sports"]
    headline: str
    platform: Literal["Kalshi", "Polymarket"]
    market_name: str
    yes_sub_title: str = ""
    market_url: str = ""
    change_at: str | None = None
    current_probability: float
    probability_move: float
    volume_usd: float
    open_interest: float
    sparkline: list[SparklinePoint]
    summary: str
    sources: list[Source]

    @field_validator("current_probability")
    @classmethod
    def current_probability_in_range(cls, v: float) -> float:
        if not 0.0 <= v <= 1.0:
            raise ValueError("current_probability must be between 0 and 1")
        return v

    @field_validator("probability_move")
    @classmethod
    def probability_move_in_range(cls, v: float) -> float:
        if not -1.0 <= v <= 1.0:
            raise ValueError("probability_move must be between -1 and 1")
        return v

    @field_validator("volume_usd")
    @classmethod
    def volume_non_negative(cls, v: float) -> float:
        if v < 0:
            raise ValueError("volume_usd must be non-negative")
        return v


@dataclass
class MarketLogEntry:
    run_timestamp: str
    domain: str
    ticker: str
    event_ticker: str
    market_name: str
    yes_sub_title: str
    probability_move: float | None
    current_probability: float | None
    open_interest: float | None
    volume_usd: float | None
    change_at: str | None
    articles_fetched: int | None
    articles_fetched_urls: str | None
    articles_prefiltered: int | None
    articles_prefiltered_urls: str | None
    sources_matched: int | None
    sources_matched_urls: str | None
    card_built: bool
    skip_reason: str | None
