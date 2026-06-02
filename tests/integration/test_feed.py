from unittest.mock import AsyncMock, patch


from prediction_news.feed import build_feed
from prediction_news.models import Source, StoryCard

SAMPLE_MARKET = {
    "ticker": "KXELECTION-24-DEM",
    "title": "Will Democrats win the 2024 presidential election?",
    "yes_bid": {"close_dollars": "0.45"},
    "yes_ask": {"close_dollars": "0.47"},
    "volume_fp": "5000000.00",
    "status": "open",
    "series_ticker": "KXELECTION",
}

SAMPLE_CANDLES = [
    {
        "end_period_ts": 1700000000,
        "yes_bid": {"close_dollars": "0.40"},
        "yes_ask": {"close_dollars": "0.42"},
        "volume_fp": "100000.00",
    },
    {
        "end_period_ts": 1700086400,
        "yes_bid": {"close_dollars": "0.44"},
        "yes_ask": {"close_dollars": "0.48"},
        "volume_fp": "120000.00",
    },
    {
        "end_period_ts": 1700172800,
        "yes_bid": {"close_dollars": "0.50"},
        "yes_ask": {"close_dollars": "0.54"},
        "volume_fp": "90000.00",
    },
]

SAMPLE_SOURCE = Source(
    title="Election article", url="https://reuters.com/1", type="rss"
)
SAMPLE_SUMMARY = "Democrats gained ground after a strong debate performance."
SAMPLE_NOTE = "A 10pp move in a $5M market is highly significant."


async def test_build_feed_returns_story_cards():
    with (
        patch(
            "prediction_news.feed.list_markets_by_category",
            new=AsyncMock(return_value=[SAMPLE_MARKET]),
        ),
        patch(
            "prediction_news.feed.get_candlesticks",
            new=AsyncMock(return_value=SAMPLE_CANDLES),
        ),
        patch("prediction_news.feed.fetch_articles", return_value=[SAMPLE_SOURCE]),
        patch(
            "prediction_news.feed.prefilter_articles",
            new=AsyncMock(return_value=[SAMPLE_SOURCE]),
        ),
        patch(
            "prediction_news.feed.score_and_summarize",
            new=AsyncMock(return_value=(SAMPLE_SUMMARY, [SAMPLE_SOURCE])),
        ),
        patch(
            "prediction_news.feed.generate_calibration_note",
            new=AsyncMock(return_value=SAMPLE_NOTE),
        ),
    ):
        result = await build_feed("politics")

    assert len(result) == 1
    card = result[0]
    assert isinstance(card, StoryCard)
    assert card.domain == "politics"
    assert card.platform == "Kalshi"
    assert card.summary == SAMPLE_SUMMARY
    assert card.calibration_note == SAMPLE_NOTE
    assert card.sources == [SAMPLE_SOURCE]


async def test_build_feed_cards_are_ranked():
    # high: 80pp single-day move, $120k volume → score ≈ 96k
    high_candles = [
        {
            "end_period_ts": 1700000000,
            "yes_bid": {"close_dollars": "0.10"},
            "yes_ask": {"close_dollars": "0.12"},
            "volume_fp": "60000.00",
        },
        {
            "end_period_ts": 1700172800,
            "yes_bid": {"close_dollars": "0.90"},
            "yes_ask": {"close_dollars": "0.92"},
            "volume_fp": "60000.00",
        },
    ]
    # low: 5pp single-day move, $120k volume → passes filters but ranks below high
    low_candles = [
        {
            "end_period_ts": 1700000000,
            "yes_bid": {"close_dollars": "0.48"},
            "yes_ask": {"close_dollars": "0.50"},
            "volume_fp": "60000.00",
        },
        {
            "end_period_ts": 1700172800,
            "yes_bid": {"close_dollars": "0.54"},
            "yes_ask": {"close_dollars": "0.56"},
            "volume_fp": "60000.00",
        },
    ]
    market_high = {**SAMPLE_MARKET, "ticker": "KXELECTION-HIGH"}
    market_low = {**SAMPLE_MARKET, "ticker": "KXELECTION-LOW"}

    candles_by_ticker = {"KXELECTION-HIGH": high_candles, "KXELECTION-LOW": low_candles}

    async def mock_candlesticks(ticker, series_ticker, days=7):
        return candles_by_ticker[ticker]

    with (
        patch(
            "prediction_news.feed.list_markets_by_category",
            new=AsyncMock(return_value=[market_high, market_low]),
        ),
        patch("prediction_news.feed.get_candlesticks", side_effect=mock_candlesticks),
        patch("prediction_news.feed.fetch_articles", return_value=[SAMPLE_SOURCE]),
        patch(
            "prediction_news.feed.prefilter_articles",
            new=AsyncMock(return_value=[SAMPLE_SOURCE]),
        ),
        patch(
            "prediction_news.feed.score_and_summarize",
            new=AsyncMock(return_value=(SAMPLE_SUMMARY, [SAMPLE_SOURCE])),
        ),
        patch(
            "prediction_news.feed.generate_calibration_note",
            new=AsyncMock(return_value=SAMPLE_NOTE),
        ),
    ):
        result = await build_feed("politics")

    assert len(result) == 2
    assert result[0].id == "KXELECTION-HIGH"
    assert result[1].id == "KXELECTION-LOW"


async def test_build_feed_handles_kalshi_failure():
    with patch(
        "prediction_news.feed.list_markets_by_category",
        new=AsyncMock(side_effect=Exception("API down")),
    ):
        result = await build_feed("politics")
    assert result == []


async def test_build_feed_unknown_domain_returns_empty():
    with patch(
        "prediction_news.feed.list_markets_by_category", new=AsyncMock(return_value=[])
    ) as mock_list:
        result = await build_feed("unknown_domain")
    mock_list.assert_not_called()
    assert result == []
