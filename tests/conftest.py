import pytest


@pytest.fixture(autouse=True)
def mock_env(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-anthropic-key")
    monkeypatch.setenv("KALSHI_API_KEY", "test-kalshi-key")
    monkeypatch.setenv("KALSHI_PRIVATE_KEY_PATH", "tests/fixtures/test.key")
    monkeypatch.setenv("POLYMARKET_API_KEY", "test-polymarket-key")
    monkeypatch.setenv("X_BEARER_TOKEN", "test-x-token")
    monkeypatch.setenv("CORS_ORIGINS", "http://localhost:5173")


@pytest.fixture
def sample_sparkline():
    return [
        {"date": "2024-01-01", "probability": 0.45},
        {"date": "2024-01-02", "probability": 0.50},
        {"date": "2024-01-03", "probability": 0.55},
    ]


@pytest.fixture
def sample_source():
    return {
        "title": "Test Article",
        "url": "https://example.com/article",
        "type": "rss",
    }


@pytest.fixture
def sample_story_card(sample_sparkline, sample_source):
    return {
        "id": "test-card-1",
        "domain": "politics",
        "headline": "Test headline about election odds",
        "platform": "Kalshi",
        "market_name": "US Election 2024",
        "current_probability": 0.55,
        "probability_move": 0.10,
        "volume_usd": 100000.0,
        "sparkline": sample_sparkline,
        "summary": "Test summary of market movement.",
        "calibration_note": "A 10pp move in a $100k market warrants moderate attention.",
        "sources": [sample_source],
    }
