import pytest
from pydantic import ValidationError

from prediction_news.models import Source, SparklinePoint, StoryCard


def test_sparkline_point_valid():
    point = SparklinePoint(date="2024-01-01", probability=0.55)
    assert point.date == "2024-01-01"
    assert point.probability == 0.55


def test_sparkline_point_rejects_invalid_probability():
    with pytest.raises(ValidationError):
        SparklinePoint(date="2024-01-01", probability=1.5)


def test_sparkline_point_rejects_negative_probability():
    with pytest.raises(ValidationError):
        SparklinePoint(date="2024-01-01", probability=-0.1)


def test_source_valid_rss():
    source = Source(title="Test", url="https://example.com", type="rss")
    assert source.type == "rss"


def test_source_valid_twitter():
    source = Source(title="Test", url="https://x.com/post", type="twitter")
    assert source.type == "twitter"


def test_source_valid_manual():
    source = Source(title="Test", url="https://example.com", type="manual")
    assert source.type == "manual"


def test_source_rejects_invalid_type():
    with pytest.raises(ValidationError):
        Source(title="Test", url="https://example.com", type="blog")


def test_story_card_valid(sample_story_card):
    card = StoryCard(**sample_story_card)
    assert card.id == "test-card-1"
    assert card.domain == "news"
    assert card.platform == "Kalshi"
    assert len(card.sparkline) == 3
    assert len(card.sources) == 1


def test_story_card_valid_domains(sample_story_card):
    for domain in ("news", "sports"):
        sample_story_card["domain"] = domain
        card = StoryCard(**sample_story_card)
        assert card.domain == domain


def test_story_card_rejects_invalid_domain(sample_story_card):
    sample_story_card["domain"] = "finance"
    with pytest.raises(ValidationError):
        StoryCard(**sample_story_card)


def test_story_card_rejects_invalid_platform(sample_story_card):
    sample_story_card["platform"] = "PredictIt"
    with pytest.raises(ValidationError):
        StoryCard(**sample_story_card)


def test_story_card_probability_move_out_of_bounds(sample_story_card):
    sample_story_card["probability_move"] = 1.5
    with pytest.raises(ValidationError):
        StoryCard(**sample_story_card)


def test_story_card_probability_move_negative_out_of_bounds(sample_story_card):
    sample_story_card["probability_move"] = -1.5
    with pytest.raises(ValidationError):
        StoryCard(**sample_story_card)


def test_story_card_current_probability_out_of_bounds(sample_story_card):
    sample_story_card["current_probability"] = 1.1
    with pytest.raises(ValidationError):
        StoryCard(**sample_story_card)


def test_story_card_volume_non_negative(sample_story_card):
    sample_story_card["volume_usd"] = -500.0
    with pytest.raises(ValidationError):
        StoryCard(**sample_story_card)
