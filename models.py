from pydantic import BaseModel


class SparklinePoint(BaseModel):
    date: str
    probability: float


class Source(BaseModel):
    title: str
    url: str
    type: str  # "rss" | "x"


class StoryCard(BaseModel):
    id: str
    domain: str  # "politics" | "world" | "sports"
    headline: str
    platform: str  # "Kalshi" | "Polymarket"
    market_name: str
    current_probability: float
    probability_move: float  # signed delta over the week
    volume_usd: int
    sparkline: list[SparklinePoint]
    summary: str
    calibration_note: str
    sources: list[Source]
