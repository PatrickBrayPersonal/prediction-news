import re

STOP_WORDS: frozenset[str] = frozenset(
    {
        "a",
        "an",
        "the",
        "be",
        "is",
        "are",
        "was",
        "were",
        "am",
        "will",
        "would",
        "shall",
        "should",
        "may",
        "might",
        "can",
        "could",
        "do",
        "does",
        "did",
        "have",
        "has",
        "had",
        "who",
        "what",
        "when",
        "where",
        "which",
        "how",
        "why",
        "in",
        "on",
        "at",
        "to",
        "of",
        "for",
        "with",
        "by",
        "from",
        "into",
        "through",
        "during",
        "before",
        "after",
        "above",
        "below",
        "between",
        "out",
        "off",
        "over",
        "under",
        "and",
        "or",
        "but",
        "not",
        "no",
        "nor",
        "it",
        "its",
        "this",
        "that",
        "these",
        "those",
        "i",
        "me",
        "my",
        "we",
        "our",
        "you",
        "your",
        "he",
        "him",
        "his",
        "she",
        "her",
        "they",
        "them",
        "more",
        "most",
        "other",
        "some",
        "such",
        "than",
    }
)

_PUNCT_RE = re.compile(r"[^\w]")


def _tokenize(text: str) -> list[str]:
    return [
        t
        for raw in text.split()
        if (t := _PUNCT_RE.sub("", raw).lower()) and len(t) > 1
    ]


def extract_keywords(headline: str, yes_sub_title: str = "") -> list[str]:
    """Return meaningful search keywords from a market headline.

    Strips stop words and punctuation, then appends any words from
    yes_sub_title that aren't already present (covers series-style titles
    like "Who will the next Pope be?" where the candidate name doesn't
    appear in the headline itself).
    """
    tokens = [t for t in _tokenize(headline) if t not in STOP_WORDS]
    seen = set(tokens)
    for t in _tokenize(yes_sub_title):
        if t not in STOP_WORDS and t not in seen:
            tokens.append(t)
            seen.add(t)
    return tokens
