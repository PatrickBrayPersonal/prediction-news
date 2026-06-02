import json

from anthropic import AsyncAnthropic
from loguru import logger

from prediction_news.config import settings
from prediction_news.models import Source

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
        f"prefilter_articles tokens: input={response.usage.input_tokens} output={response.usage.output_tokens}"
    )

    try:
        indices = json.loads(response.content[0].text.strip())
        return [articles[i] for i in indices if 0 <= i < len(articles)]
    except (json.JSONDecodeError, IndexError):
        return articles


async def rank_sources(market_name: str, articles: list[Source]) -> list[Source]:
    if not articles:
        return []

    client = AsyncAnthropic(api_key=settings.anthropic_api_key)
    article_list = "\n".join(f"- {a.title} ({a.url})" for a in articles)
    prompt = (
        f"Rank the following news articles by relevance to this market: {market_name}\n\n"
        f"Articles:\n{article_list}\n\n"
        f"Respond in exactly this format:\n"
        f"SOURCES: <comma-separated list of URLs in order of relevance>"
    )

    response = await client.messages.create(
        model=SONNET_MODEL,
        max_tokens=200,
        messages=[{"role": "user", "content": prompt}],
    )
    logger.info(
        f"rank_sources tokens: input={response.usage.input_tokens} output={response.usage.output_tokens}"
    )

    url_to_source = {a.url: a for a in articles}
    for line in response.content[0].text.strip().split("\n"):
        if line.startswith("SOURCES:"):
            urls = [u.strip() for u in line[len("SOURCES:"):].split(",")]
            ranked = [url_to_source[u] for u in urls if u in url_to_source]
            return ranked if ranked else articles

    return articles
