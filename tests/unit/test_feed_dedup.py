from unittest.mock import AsyncMock, patch

import pytest

from prediction_news.feed import _select_top_market_per_event


def _market(ticker: str, event_ticker: str = "", series_ticker: str = "SER") -> dict:
    return {
        "ticker": ticker,
        "event_ticker": event_ticker,
        "series_ticker": series_ticker,
    }


@pytest.mark.asyncio
async def test_single_market_event_passes_through():
    markets = [_market("A-YES", event_ticker="EVT-A")]
    with patch("prediction_news.feed.get_candlesticks", new=AsyncMock()):
        result = await _select_top_market_per_event(markets)
    assert [m["ticker"] for m in result] == ["A-YES"]


@pytest.mark.asyncio
async def test_picks_market_with_bigger_move():
    # EVT-A moves 0.10, EVT-B moves 0.30 → EVT-B wins
    markets = [
        _market("EVT-A", event_ticker="EVT"),
        _market("EVT-B", event_ticker="EVT"),
    ]

    async def mock_candles(ticker, series_ticker, days):
        delta = 0.10 if ticker == "EVT-A" else 0.30
        return [
            {
                "end_period_ts": 1700000000,
                "yes_bid": {"close_dollars": "0.40"},
                "yes_ask": {"close_dollars": "0.42"},
                "volume_fp": "1000",
                "open_interest_fp": "5000",
            },
            {
                "end_period_ts": 1700086400,
                "yes_bid": {"close_dollars": str(round(0.40 + delta, 4))},
                "yes_ask": {"close_dollars": str(round(0.42 + delta, 4))},
                "volume_fp": "1000",
                "open_interest_fp": "5000",
            },
        ]

    with patch("prediction_news.feed.get_candlesticks", side_effect=mock_candles):
        result = await _select_top_market_per_event(markets)

    assert len(result) == 1
    assert result[0]["ticker"] == "EVT-B"


@pytest.mark.asyncio
async def test_market_without_event_ticker_is_its_own_group():
    # Each market falls back to its own ticker as the group key
    markets = [
        _market("SOLO-1", event_ticker=""),
        _market("SOLO-2", event_ticker=""),
    ]
    with patch("prediction_news.feed.get_candlesticks", new=AsyncMock(return_value=[])):
        result = await _select_top_market_per_event(markets)

    assert len(result) == 2


@pytest.mark.asyncio
async def test_candlestick_failure_falls_back_to_first_market():
    markets = [
        _market("EVT-A", event_ticker="EVT"),
        _market("EVT-B", event_ticker="EVT"),
    ]

    async def mock_candles(ticker, series_ticker, days):
        raise Exception("API error")

    with patch("prediction_news.feed.get_candlesticks", side_effect=mock_candles):
        result = await _select_top_market_per_event(markets)

    assert len(result) == 1
    assert result[0]["ticker"] == "EVT-A"


@pytest.mark.asyncio
async def test_multiple_events_each_produce_one_winner():
    markets = [
        _market("EV1-A", event_ticker="EV1"),
        _market("EV1-B", event_ticker="EV1"),
        _market("EV2-X", event_ticker="EV2"),
        _market("EV2-Y", event_ticker="EV2"),
    ]

    moves = {"EV1-A": 0.05, "EV1-B": 0.20, "EV2-X": 0.30, "EV2-Y": 0.10}

    async def mock_candles(ticker, series_ticker, days):
        delta = moves[ticker]
        return [
            {
                "end_period_ts": 1700000000,
                "yes_bid": {"close_dollars": "0.40"},
                "yes_ask": {"close_dollars": "0.42"},
                "volume_fp": "1000",
                "open_interest_fp": "5000",
            },
            {
                "end_period_ts": 1700086400,
                "yes_bid": {"close_dollars": str(round(0.40 + delta, 4))},
                "yes_ask": {"close_dollars": str(round(0.42 + delta, 4))},
                "volume_fp": "1000",
                "open_interest_fp": "5000",
            },
        ]

    with patch("prediction_news.feed.get_candlesticks", side_effect=mock_candles):
        result = await _select_top_market_per_event(markets)

    assert len(result) == 2
    assert {m["ticker"] for m in result} == {"EV1-B", "EV2-X"}


@pytest.mark.asyncio
async def test_empty_input_returns_empty():
    result = await _select_top_market_per_event([])
    assert result == []
