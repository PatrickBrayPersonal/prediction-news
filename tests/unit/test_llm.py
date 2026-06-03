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


def _make_text_client(
    response_text: str, input_tokens: int = 100, output_tokens: int = 50
) -> MagicMock:
    mock_content = MagicMock()
    mock_content.text = response_text

    mock_response = MagicMock()
    mock_response.content = [mock_content]
    mock_response.usage = MagicMock(input_tokens=input_tokens, output_tokens=output_tokens)

    mock_client = MagicMock()
    mock_client.messages = AsyncMock()
    mock_client.messages.create.return_value = mock_response
    return mock_client


def _make_tool_client(
    urls: list[str], input_tokens: int = 100, output_tokens: int = 50
) -> MagicMock:
    mock_tool_use = MagicMock()
    mock_tool_use.type = "tool_use"
    mock_tool_use.name = "submit_ranked_sources"
    mock_tool_use.input = {"urls": urls}

    mock_response = MagicMock()
    mock_response.content = [mock_tool_use]
    mock_response.usage = MagicMock(input_tokens=input_tokens, output_tokens=output_tokens)

    mock_client = MagicMock()
    mock_client.messages = AsyncMock()
    mock_client.messages.create.return_value = mock_response
    return mock_client


def _make_no_tool_client() -> MagicMock:
    mock_response = MagicMock()
    mock_response.content = []
    mock_response.usage = MagicMock(input_tokens=100, output_tokens=10)

    mock_client = MagicMock()
    mock_client.messages = AsyncMock()
    mock_client.messages.create.return_value = mock_response
    return mock_client


# --- prefilter_articles ---

async def test_prefilter_articles_uses_haiku():
    mock_client = _make_text_client("[0]")
    with patch("prediction_news.services.llm._client", mock_client):
        await prefilter_articles("US Election 2024", SAMPLE_SOURCES)
    call_kwargs = mock_client.messages.create.call_args.kwargs
    assert "haiku" in call_kwargs["model"]


async def test_prefilter_articles_returns_subset():
    mock_client = _make_text_client("[0]")
    with patch("prediction_news.services.llm._client", mock_client):
        result = await prefilter_articles("US Election 2024", SAMPLE_SOURCES)
    assert len(result) == 1
    assert result[0].url == "https://reuters.com/1"


async def test_prefilter_articles_empty_input_skips_api():
    with patch("prediction_news.services.llm._client") as mock_client:
        result = await prefilter_articles("US Election 2024", [])
    mock_client.messages.create.assert_not_called()
    assert result == []


# --- rank_sources ---

async def test_rank_sources_uses_sonnet():
    mock_client = _make_tool_client(["https://reuters.com/1"])
    with patch("prediction_news.services.llm._client", mock_client):
        await rank_sources("US Election 2024", SAMPLE_SOURCES)
    call_kwargs = mock_client.messages.create.call_args.kwargs
    assert "sonnet" in call_kwargs["model"]


async def test_rank_sources_forces_tool_call():
    mock_client = _make_tool_client(["https://reuters.com/1"])
    with patch("prediction_news.services.llm._client", mock_client):
        await rank_sources("US Election 2024", SAMPLE_SOURCES)
    call_kwargs = mock_client.messages.create.call_args.kwargs
    assert call_kwargs["tool_choice"] == {"type": "tool", "name": "submit_ranked_sources"}


async def test_rank_sources_returns_ranked_list():
    mock_client = _make_tool_client(["https://reuters.com/1"])
    with patch("prediction_news.services.llm._client", mock_client):
        sources = await rank_sources("US Election 2024", SAMPLE_SOURCES)
    assert len(sources) == 1
    assert sources[0].url == "https://reuters.com/1"


async def test_rank_sources_preserves_model_ordering():
    mock_client = _make_tool_client(["https://reuters.com/2", "https://reuters.com/1"])
    with patch("prediction_news.services.llm._client", mock_client):
        sources = await rank_sources("US Election 2024", SAMPLE_SOURCES)
    assert sources[0].url == "https://reuters.com/2"
    assert sources[1].url == "https://reuters.com/1"


async def test_rank_sources_empty_array_returns_empty():
    mock_client = _make_tool_client([])
    with patch("prediction_news.services.llm._client", mock_client):
        result = await rank_sources("US Election 2024", SAMPLE_SOURCES)
    assert result == []


async def test_rank_sources_empty_input_skips_api():
    with patch("prediction_news.services.llm._client") as mock_client:
        result = await rank_sources("US Election 2024", [])
    mock_client.messages.create.assert_not_called()
    assert result == []


async def test_rank_sources_ignores_unknown_urls():
    mock_client = _make_tool_client(["https://reuters.com/1", "https://unknown.com/x"])
    with patch("prediction_news.services.llm._client", mock_client):
        sources = await rank_sources("US Election 2024", SAMPLE_SOURCES)
    assert len(sources) == 1
    assert sources[0].url == "https://reuters.com/1"


async def test_rank_sources_returns_empty_when_no_tool_use_block():
    mock_client = _make_no_tool_client()
    with patch("prediction_news.services.llm._client", mock_client):
        sources = await rank_sources("US Election 2024", SAMPLE_SOURCES)
    assert sources == []
