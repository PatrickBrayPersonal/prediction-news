from prediction_news.models import StoryCard

MIN_PROBABILITY_MOVE = 0.05
MIN_OPEN_INTEREST = 10_000.0


def score_card(card: StoryCard) -> float:
    return abs(card.probability_move) * card.volume_usd


def filter_cards(
    cards: list[StoryCard],
    min_move: float = MIN_PROBABILITY_MOVE,
    min_open_interest: float = MIN_OPEN_INTEREST,
) -> list[StoryCard]:
    return [
        c
        for c in cards
        if abs(c.probability_move) >= min_move and c.open_interest >= min_open_interest
    ]


def rank_cards(cards: list[StoryCard]) -> list[StoryCard]:
    return sorted(cards, key=score_card, reverse=True)
