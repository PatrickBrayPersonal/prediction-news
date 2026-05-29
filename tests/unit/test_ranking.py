from prediction_news.models import Source, SparklinePoint, StoryCard
from prediction_news.ranking import rank_cards, score_card


def _make_card(probability_move: float, volume_usd: float, card_id: str = "test") -> StoryCard:
    return StoryCard(
        id=card_id,
        domain="politics",
        headline="Test headline",
        platform="Kalshi",
        market_name="Test Market",
        current_probability=0.5,
        probability_move=probability_move,
        volume_usd=volume_usd,
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
        _make_card(0.05, 1_000_000, "low"),
        _make_card(0.20, 5_000_000, "high"),
        _make_card(0.10, 2_000_000, "mid"),
    ]
    ranked = rank_cards(cards)
    assert [c.id for c in ranked] == ["high", "mid", "low"]


def test_rank_cards_empty_list():
    assert rank_cards([]) == []


def test_rank_cards_single_card():
    card = _make_card(0.10, 500_000)
    assert rank_cards([card]) == [card]
