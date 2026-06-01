from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from prediction_news.api import app
from prediction_news.models import Source, SparklinePoint, StoryCard

SAMPLE_CARD = StoryCard(
    id="test-1",
    domain="politics",
    headline="Test headline",
    platform="Kalshi",
    market_name="Test Market",
    current_probability=0.55,
    probability_move=0.10,
    volume_usd=1_000_000.0,
    sparkline=[SparklinePoint(date="2024-01-01", probability=0.55)],
    summary="Test summary",
    calibration_note="Test note",
    sources=[Source(title="Test", url="https://test.com", type="rss")],
)


def test_get_feed_returns_200_with_cards():
    with patch(
        "prediction_news.api.build_feed", new=AsyncMock(return_value=[SAMPLE_CARD])
    ):
        client = TestClient(app)
        response = client.get("/api/feeds/politics")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["id"] == "test-1"
    assert data[0]["domain"] == "politics"


def test_get_feed_invalid_domain_returns_422():
    client = TestClient(app)
    response = client.get("/api/feeds/invalid")
    assert response.status_code == 422


def test_get_feed_cors_header_present():
    with patch("prediction_news.api.build_feed", new=AsyncMock(return_value=[])):
        client = TestClient(app)
        response = client.get(
            "/api/feeds/politics",
            headers={"Origin": "http://localhost:5173"},
        )
    assert "access-control-allow-origin" in response.headers
    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"
