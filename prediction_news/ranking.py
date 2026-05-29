from prediction_news.models import StoryCard


def score_card(card: StoryCard) -> float:
    return abs(card.probability_move) * card.volume_usd


def rank_cards(cards: list[StoryCard]) -> list[StoryCard]:
    return sorted(cards, key=score_card, reverse=True)
