from unittest.mock import AsyncMock, MagicMock, patch


from prediction_news.kalshi import (
    _auth_headers,
    _load_private_key,
    _resolve_headline,
    candlesticks_to_sparkline,
    get_candlesticks,
    list_markets,
    market_to_card_fields,
    max_single_day_move,
)

SAMPLE_MARKET = {
    "ticker": "KXELECTION-24-DEM",
    "title": "Will Democrats win the 2024 presidential election?",
    "yes_bid": 0.45,
    "yes_ask": 0.47,
    "volume": 5000000,
    "open_interest": 1000000,
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


def test_load_private_key_from_file():
    key = _load_private_key(key_path="tests/fixtures/test.key")
    assert key is not None


def test_auth_headers_contain_required_fields(monkeypatch):
    monkeypatch.setenv("KALSHI_PRIVATE_KEY_PATH", "tests/fixtures/test.key")
    headers = _auth_headers("GET", "/trade-api/v2/markets")
    assert "KALSHI-ACCESS-KEY" in headers
    assert "KALSHI-ACCESS-TIMESTAMP" in headers
    assert "KALSHI-ACCESS-SIGNATURE" in headers


def test_auth_headers_signature_is_base64(monkeypatch):
    import base64

    monkeypatch.setenv("KALSHI_PRIVATE_KEY_PATH", "tests/fixtures/test.key")
    headers = _auth_headers("GET", "/trade-api/v2/markets")
    sig = headers["KALSHI-ACCESS-SIGNATURE"]
    decoded = base64.b64decode(sig)
    assert len(decoded) > 0


def _make_mock_client(json_payload: dict) -> MagicMock:
    mock_response = MagicMock()
    mock_response.json.return_value = json_payload
    mock_response.raise_for_status = MagicMock()
    mock_client = AsyncMock()
    mock_client.__aenter__.return_value = mock_client
    mock_client.__aexit__.return_value = None
    mock_client.get.return_value = mock_response
    return mock_client


async def test_list_markets_returns_markets(monkeypatch):
    monkeypatch.setenv("KALSHI_PRIVATE_KEY_PATH", "tests/fixtures/test.key")
    mock_client = _make_mock_client({"markets": [SAMPLE_MARKET], "cursor": ""})
    with patch("prediction_news.kalshi.httpx.AsyncClient", return_value=mock_client):
        markets = await list_markets()
    assert len(markets) == 1
    assert markets[0]["ticker"] == "KXELECTION-24-DEM"


async def test_list_markets_empty_response(monkeypatch):
    monkeypatch.setenv("KALSHI_PRIVATE_KEY_PATH", "tests/fixtures/test.key")
    mock_client = _make_mock_client({"markets": [], "cursor": ""})
    with patch("prediction_news.kalshi.httpx.AsyncClient", return_value=mock_client):
        markets = await list_markets()
    assert markets == []


async def test_get_candlesticks_returns_sorted_points(monkeypatch):
    monkeypatch.setenv("KALSHI_PRIVATE_KEY_PATH", "tests/fixtures/test.key")
    mock_client = _make_mock_client({"candlesticks": SAMPLE_CANDLES})
    with patch("prediction_news.kalshi.httpx.AsyncClient", return_value=mock_client):
        candles = await get_candlesticks("KXELECTION-24-DEM", "KXELECTION", days=3)
    assert len(candles) == 3
    assert candles[0]["end_period_ts"] <= candles[-1]["end_period_ts"]


def test_candlesticks_to_sparkline_converts_correctly():
    sparkline = candlesticks_to_sparkline(SAMPLE_CANDLES)
    assert len(sparkline) == 3
    assert all(hasattr(p, "date") and hasattr(p, "probability") for p in sparkline)
    assert all(0.0 <= p.probability <= 1.0 for p in sparkline)


def test_candlesticks_to_sparkline_sorted_by_date():
    reversed_candles = list(reversed(SAMPLE_CANDLES))
    sparkline = candlesticks_to_sparkline(reversed_candles)
    dates = [p.date for p in sparkline]
    assert dates == sorted(dates)


def test_market_to_card_fields_computes_move():
    card_fields = market_to_card_fields(SAMPLE_MARKET, SAMPLE_CANDLES)
    assert card_fields["platform"] == "Kalshi"
    assert card_fields["market_name"] == SAMPLE_MARKET["title"]
    assert "current_probability" in card_fields
    assert "probability_move" in card_fields
    assert "volume_usd" in card_fields
    assert "sparkline" in card_fields
    assert -1.0 <= card_fields["probability_move"] <= 1.0


def test_resolve_headline_fills_double_space_blank():
    result = _resolve_headline("Will  become President before 2045?", "Gavin Newsom")
    assert result == "Will Gavin Newsom become President before 2045?"


def test_resolve_headline_no_double_space_unchanged():
    result = _resolve_headline("Who will be the next Pope?", "Peter Erdo")
    assert result == "Who will be the next Pope?"


def test_resolve_headline_empty_sub_title_unchanged():
    result = _resolve_headline("Will  become President before 2045?", "")
    assert result == "Will  become President before 2045?"


def test_resolve_headline_replaces_only_first_blank():
    result = _resolve_headline("Will  beat  in 2028?", "Alice")
    assert result == "Will Alice beat  in 2028?"


def test_market_to_card_fields_uses_yes_sub_title():
    market_with_sub = {
        **SAMPLE_MARKET,
        "title": "Will  become President of the United States before 2045?",
        "yes_sub_title": "Gavin Newsom",
    }
    card_fields = market_to_card_fields(market_with_sub, SAMPLE_CANDLES)
    assert (
        card_fields["headline"]
        == "Will Gavin Newsom become President of the United States before 2045?"
    )
    assert card_fields["market_name"] == card_fields["headline"]


def test_market_to_card_fields_no_sub_title_uses_raw_title():
    market_without_sub = {
        **SAMPLE_MARKET,
        "title": "Will  become President before 2045?",
    }
    card_fields = market_to_card_fields(market_without_sub, SAMPLE_CANDLES)
    assert card_fields["headline"] == "Will  become President before 2045?"


def test_market_to_card_fields_probability_move_direction():
    card_fields = market_to_card_fields(SAMPLE_MARKET, SAMPLE_CANDLES)
    first_prob = (
        float(SAMPLE_CANDLES[0]["yes_bid"]["close_dollars"])
        + float(SAMPLE_CANDLES[0]["yes_ask"]["close_dollars"])
    ) / 2
    last_prob = (
        float(SAMPLE_CANDLES[-1]["yes_bid"]["close_dollars"])
        + float(SAMPLE_CANDLES[-1]["yes_ask"]["close_dollars"])
    ) / 2
    expected_move = round(last_prob - first_prob, 4)
    assert abs(card_fields["probability_move"] - expected_move) < 0.001


def test_max_single_day_move_returns_largest_swing():
    # Day 0 mid: (0.40+0.42)/2 = 0.41
    # Day 1 mid: (0.44+0.48)/2 = 0.46  → delta = 0.05
    # Day 2 mid: (0.50+0.54)/2 = 0.52  → delta = 0.06
    result = max_single_day_move(SAMPLE_CANDLES)
    assert abs(result - 0.06) < 0.001


def test_max_single_day_move_single_candle_returns_zero():
    result = max_single_day_move([SAMPLE_CANDLES[0]])
    assert result == 0.0


def test_max_single_day_move_empty_returns_zero():
    result = max_single_day_move([])
    assert result == 0.0


def test_max_single_day_move_uses_absolute_value():
    falling_candles = [
        {
            "end_period_ts": 1700000000,
            "yes_bid": {"close_dollars": "0.80"},
            "yes_ask": {"close_dollars": "0.82"},
            "volume_fp": "50000.00",
        },
        {
            "end_period_ts": 1700086400,
            "yes_bid": {"close_dollars": "0.60"},
            "yes_ask": {"close_dollars": "0.62"},
            "volume_fp": "50000.00",
        },
    ]
    result = max_single_day_move(falling_candles)
    assert abs(result - 0.20) < 0.001
