from unittest.mock import AsyncMock, MagicMock, patch


from prediction_news.models import Source
from prediction_news.services.llm import (
    prefilter_articles,
    rank_sources,
)

SAMPLE_SOURCES = [
    Source(title="Democrats lead in polls", url="https://reuters.com/1", type="rss"),
    Source(title="GOP fundraising up", url="https://reuters.com/2", type="rss"),
]


def _make_mock_client(
    response_text: str, input_tokens: int = 100, output_tokens: int = 50
) -> MagicMock:
    mock_usage = MagicMock()
    mock_usage.input_tokens = input_tokens
    mock_usage.output_tokens = output_tokens

    mock_content = MagicMock()
    mock_content.text = response_text

    mock_response = MagicMock()
    mock_response.content = [mock_content]
    mock_response.usage = mock_usage

    mock_messages = AsyncMock()
    mock_messages.create.return_value = mock_response

    mock_client = MagicMock()
    mock_client.messages = mock_messages
    return mock_client


async def test_prefilter_articles_uses_haiku():
    mock_client = _make_mock_client("[0]")
    with patch("prediction_news.services.llm.AsyncAnthropic", return_value=mock_client):
        await prefilter_articles("US Election 2024", SAMPLE_SOURCES)
    call_kwargs = mock_client.messages.create.call_args.kwargs
    assert "haiku" in call_kwargs["model"]


async def test_prefilter_articles_returns_subset():
    mock_client = _make_mock_client("[0]")
    with patch("prediction_news.services.llm.AsyncAnthropic", return_value=mock_client):
        result = await prefilter_articles("US Election 2024", SAMPLE_SOURCES)
    assert len(result) == 1
    assert result[0].url == "https://reuters.com/1"


async def test_prefilter_articles_empty_input_skips_api():
    with patch("prediction_news.services.llm.AsyncAnthropic") as mock_cls:
        result = await prefilter_articles("US Election 2024", [])
    mock_cls.assert_not_called()
    assert result == []


async def test_rank_sources_uses_sonnet():
    mock_client = _make_mock_client("SOURCES: https://reuters.com/1")
    with patch("prediction_news.services.llm.AsyncAnthropic", return_value=mock_client):
        await rank_sources("US Election 2024", SAMPLE_SOURCES)
    call_kwargs = mock_client.messages.create.call_args.kwargs
    assert "sonnet" in call_kwargs["model"]


async def test_rank_sources_returns_ranked_list():
    mock_client = _make_mock_client("SOURCES: https://reuters.com/1")
    with patch("prediction_news.services.llm.AsyncAnthropic", return_value=mock_client):
        sources = await rank_sources("US Election 2024", SAMPLE_SOURCES)
    assert len(sources) == 1
    assert sources[0].url == "https://reuters.com/1"


async def test_rank_sources_empty_input_skips_api():
    with patch("prediction_news.services.llm.AsyncAnthropic") as mock_cls:
        result = await rank_sources("US Election 2024", [])
    mock_cls.assert_not_called()
    assert result == []


async def test_rank_sources_falls_back_to_original_order_on_bad_response():
    mock_client = _make_mock_client("I cannot determine relevance.")
    with patch("prediction_news.services.llm.AsyncAnthropic", return_value=mock_client):
        sources = await rank_sources("US Election 2024", SAMPLE_SOURCES)
    assert sources == SAMPLE_SOURCES
