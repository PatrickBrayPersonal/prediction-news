from prediction_news.models import Source, SparklinePoint, StoryCard
from prediction_news.ranking import filter_cards, rank_cards, score_card


def _make_card(
    probability_move: float,
    volume_usd: float,
    open_interest: float = 250_000.0,
    card_id: str = "test",
) -> StoryCard:
    return StoryCard(
        id=card_id,
        domain="politics",
        headline="Test headline",
        platform="Kalshi",
        market_name="Test Market",
        current_probability=0.5,
        probability_move=probability_move,
        volume_usd=volume_usd,
        open_interest=open_interest,
        sparkline=[SparklinePoint(date="2024-01-01", probability=0.5)],
        summary="Test summary",
        calibration_note="Test note",
        sources=[Source(title="Test", url="https://test.com", type="rss")],
    )


def test_score_card_multiplies_abs_move_by_volume():
    card = _make_card(probability_move=0.12, volume_usd=2_000_000)
    assert abs(score_card(card) - 240_000.0) < 0.01


def test_score_card_uses_absolute_value_of_move():
    pos = _make_card(probability_move=0.10, volume_usd=1_000_000)
    neg = _make_card(probability_move=-0.10, volume_usd=1_000_000)
    assert score_card(pos) == score_card(neg)


def test_rank_cards_sorts_descending():
    cards = [
        _make_card(0.05, 1_000_000, card_id="low"),
        _make_card(0.20, 5_000_000, card_id="high"),
        _make_card(0.10, 2_000_000, card_id="mid"),
    ]
    ranked = rank_cards(cards)
    assert [c.id for c in ranked] == ["high", "mid", "low"]


def test_rank_cards_empty_list():
    assert rank_cards([]) == []


def test_rank_cards_single_card():
    card = _make_card(0.10, 500_000)
    assert rank_cards([card]) == [card]


def test_filter_cards_excludes_low_move():
    low = _make_card(probability_move=0.03, volume_usd=200_000, card_id="low")
    high = _make_card(probability_move=0.10, volume_usd=200_000, card_id="high")
    result = filter_cards([low, high], min_move=0.05, min_open_interest=100_000)
    assert [c.id for c in result] == ["high"]


def test_filter_cards_excludes_low_open_interest():
    low_oi = _make_card(
        probability_move=0.10, volume_usd=50_000, open_interest=50_000, card_id="low_oi"
    )
    ok = _make_card(
        probability_move=0.10, volume_usd=100_000, open_interest=100_000, card_id="ok"
    )
    result = filter_cards([low_oi, ok], min_move=0.05, min_open_interest=100_000)
    assert [c.id for c in result] == ["ok"]


def test_filter_cards_passes_qualifying_cards():
    card = _make_card(probability_move=0.05, volume_usd=100_000, card_id="borderline")
    result = filter_cards([card], min_move=0.05, min_open_interest=100_000)
    assert len(result) == 1


def test_filter_cards_uses_absolute_value_of_move():
    neg = _make_card(probability_move=-0.08, volume_usd=150_000, card_id="neg")
    result = filter_cards([neg], min_move=0.05, min_open_interest=100_000)
    assert len(result) == 1


def test_filter_cards_empty_list():
    assert filter_cards([], min_move=0.05, min_open_interest=100_000) == []
