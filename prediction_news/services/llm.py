import json
import logging

from anthropic import AsyncAnthropic

from prediction_news.config import settings
from prediction_news.models import Source

logger = logging.getLogger(__name__)

HAIKU_MODEL = "claude-haiku-4-5-20251001"
SONNET_MODEL = "claude-sonnet-4-6"


async def prefilter_articles(market_name: str, articles: list[Source]) -> list[Source]:
    if not articles:
        return []

    client = AsyncAnthropic(api_key=settings.anthropic_api_key)
    article_list = "\n".join(f"{i}. {a.title}" for i, a in enumerate(articles))
    prompt = (
        f"You are filtering news articles for relevance to a prediction market.\n\n"
        f"Market: {market_name}\n\n"
        f"Articles:\n{article_list}\n\n"
        f"Return a JSON array of the 0-based indices of articles causally relevant to this market. "
        f"Return [] if none are relevant. Return only the JSON array, nothing else."
    )

    response = await client.messages.create(
        model=HAIKU_MODEL,
        max_tokens=200,
        messages=[{"role": "user", "content": prompt}],
    )
    logger.info(
        "prefilter_articles tokens: input=%d output=%d",
        response.usage.input_tokens,
        response.usage.output_tokens,
    )

    try:
        indices = json.loads(response.content[0].text.strip())
        return [articles[i] for i in indices if 0 <= i < len(articles)]
    except (json.JSONDecodeError, IndexError):
        return articles


async def score_and_summarize(
    market_name: str, articles: list[Source]
) -> tuple[str, list[Source]]:
    if not articles:
        return ("", [])

    client = AsyncAnthropic(api_key=settings.anthropic_api_key)
    article_list = "\n".join(f"- {a.title} ({a.url})" for a in articles)
    prompt = (
        f"You are analyzing news articles and their relationship to a prediction market move.\n\n"
        f"Market: {market_name}\n"
        f"Articles:\n{article_list}\n\n"
        f"Respond in exactly this format:\n"
        f"SUMMARY: <one paragraph explaining why the market moved>\n"
        f"SOURCES: <comma-separated list of URLs in order of relevance>"
    )

    response = await client.messages.create(
        model=SONNET_MODEL,
        max_tokens=500,
        messages=[{"role": "user", "content": prompt}],
    )
    logger.info(
        "score_and_summarize tokens: input=%d output=%d",
        response.usage.input_tokens,
        response.usage.output_tokens,
    )

    summary = ""
    ranked_sources: list[Source] = articles
    url_to_source = {a.url: a for a in articles}

    for line in response.content[0].text.strip().split("\n"):
        if line.startswith("SUMMARY:"):
            summary = line[len("SUMMARY:") :].strip()
        elif line.startswith("SOURCES:"):
            urls = [u.strip() for u in line[len("SOURCES:") :].split(",")]
            ranked_sources = [url_to_source[u] for u in urls if u in url_to_source]

    return (summary, ranked_sources)


async def generate_calibration_note(probability_move: float, volume_usd: float) -> str:
    client = AsyncAnthropic(api_key=settings.anthropic_api_key)
    move_pct = round(abs(probability_move) * 100, 1)
    prompt = (
        f"You are writing a one-sentence calibration note for a prediction market move.\n\n"
        f"The market moved {move_pct} percentage points. The market has ${volume_usd:,.0f} in volume.\n\n"
        f"Write a single sentence contextualizing how significant this move is. Be concise and specific."
    )

    response = await client.messages.create(
        model=SONNET_MODEL,
        max_tokens=100,
        messages=[{"role": "user", "content": prompt}],
    )
    logger.info(
        "generate_calibration_note tokens: input=%d output=%d",
        response.usage.input_tokens,
        response.usage.output_tokens,
    )

    return response.content[0].text.strip()
