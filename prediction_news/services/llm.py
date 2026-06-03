import json

from anthropic import AsyncAnthropic
from loguru import logger

from prediction_news.config import settings
from prediction_news.models import Source

HAIKU_MODEL = "claude-haiku-4-5-20251001"
SONNET_MODEL = "claude-sonnet-4-6"

_client: AsyncAnthropic | None = None


def _get_client() -> AsyncAnthropic:
    global _client
    if _client is None:
        _client = AsyncAnthropic(api_key=settings.anthropic_api_key)
    return _client


RANK_TOOL = {
    "name": "submit_ranked_sources",
    "description": "Submit the filtered and ranked list of article URLs relevant to the prediction market.",
    "input_schema": {
        "type": "object",
        "properties": {
            "urls": {
                "type": "array",
                "items": {"type": "string"},
                "description": (
                    "URLs of articles with genuine causal relevance to the market outcome, "
                    "ordered from most to least relevant. Empty array if none qualify. "
                    "Use only URLs from the provided list, verbatim."
                ),
            }
        },
        "required": ["urls"],
    },
}


async def prefilter_articles(market_name: str, articles: list[Source]) -> list[Source]:
    if not articles:
        return []

    article_list = "\n".join(f"{i}. {a.title}" for i, a in enumerate(articles))
    prompt = (
        f"You are filtering news articles for relevance to a prediction market.\n\n"
        f"Market: {market_name}\n\n"
        f"Articles:\n{article_list}\n\n"
        f"Return a JSON array of the 0-based indices of articles causally relevant to this market. "
        f"Return [] if none are relevant. Return only the JSON array, nothing else."
    )

    response = await _get_client().messages.create(
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

    article_list = "\n".join(f"- {a.title} ({a.url})" for a in articles)
    prompt = (
        f"Filter and rank news articles for a prediction market.\n\n"
        f"Market: {market_name}\n\n"
        f"Articles:\n{article_list}\n\n"
        f"Include only articles with a genuine causal relationship to the market outcome — "
        f"the headline plausibly explains why the market probability would move. "
        f"Exclude coincidental, tangential, or unrelated articles.\n\n"
        f"Call submit_ranked_sources with your final ordered list. Do not explain your reasoning."
    )

    response = await _get_client().messages.create(
        model=SONNET_MODEL,
        max_tokens=1024,
        tools=[RANK_TOOL],
        tool_choice={"type": "tool", "name": "submit_ranked_sources"},
        messages=[{"role": "user", "content": prompt}],
    )
    logger.info(
        f"rank_sources tokens: input={response.usage.input_tokens} output={response.usage.output_tokens}"
    )

    tool_use = next(
        (b for b in response.content if b.type == "tool_use" and b.name == "submit_ranked_sources"),
        None,
    )
    if tool_use is None:
        logger.warning(f"No tool_use block in response: {response.content}")
        return []

    urls = tool_use.input.get("urls", [])
    url_to_source = {a.url: a for a in articles}

    ranked = []
    unknown = []
    for u in urls:
        if u in url_to_source:
            ranked.append(url_to_source[u])
        else:
            unknown.append(u)

    if unknown:
        logger.warning(f"Model returned URLs not in input set: {unknown}")

    return ranked
