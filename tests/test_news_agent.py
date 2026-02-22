"""Unit tests for the News Synthesizer Agent."""

import pytest
from unittest.mock import patch, MagicMock


def _mock_response(content: str) -> MagicMock:
    mock = MagicMock()
    mock.choices[0].message.content = content
    return mock


_ARTICLE_1 = (
    "Federal Reserve signals pause in rate hikes as inflation cools to 3.1%. "
    "Markets rallied on the news with the S&P 500 gaining 1.2%."
)
_ARTICLE_2 = (
    "Tech giants report mixed earnings. Apple beats estimates while Google misses. "
    "Analysts cite ad-revenue weakness as a key concern."
)
_ARTICLE_3 = (
    "Oil prices rise 2% amid OPEC+ production cuts. Energy stocks outperform "
    "broader market for the third consecutive week."
)


class TestSynthesizeNews:

    @patch("src.agents.news_synthesizer_agent.news_agent.get_client")
    def test_returns_non_empty_string(self, mock_get_client):
        mock_get_client.return_value.chat.completions.create.return_value = _mock_response(
            "This week's key themes: Fed pause, mixed tech earnings, oil rally."
        )
        from src.agents.news_synthesizer_agent.news_agent import synthesize_news

        result = synthesize_news([_ARTICLE_1])
        assert isinstance(result, str)
        assert len(result.strip()) > 0

    @patch("src.agents.news_synthesizer_agent.news_agent.get_client")
    def test_handles_multiple_articles(self, mock_get_client):
        mock_get_client.return_value.chat.completions.create.return_value = _mock_response(
            "Synthesis of three articles..."
        )
        from src.agents.news_synthesizer_agent.news_agent import synthesize_news

        result = synthesize_news([_ARTICLE_1, _ARTICLE_2, _ARTICLE_3])
        assert isinstance(result, str)
        assert len(result.strip()) > 0

    @patch("src.agents.news_synthesizer_agent.news_agent.get_client")
    def test_handles_empty_list(self, mock_get_client):
        """An empty articles list should not raise."""
        mock_get_client.return_value.chat.completions.create.return_value = _mock_response(
            "No articles provided — general overview..."
        )
        from src.agents.news_synthesizer_agent.news_agent import synthesize_news

        result = synthesize_news([])
        assert isinstance(result, str)
        assert len(result.strip()) > 0

    @patch("src.agents.news_synthesizer_agent.news_agent.get_client")
    def test_all_articles_appear_in_prompt(self, mock_get_client):
        """Each article's content should appear in the user message."""
        mock_get_client.return_value.chat.completions.create.return_value = _mock_response("Answer.")
        from src.agents.news_synthesizer_agent.news_agent import synthesize_news

        synthesize_news([_ARTICLE_1, _ARTICLE_2])
        call_kwargs = mock_get_client.return_value.chat.completions.create.call_args.kwargs
        user_content = next(m["content"] for m in call_kwargs["messages"] if m["role"] == "user")
        assert "Federal Reserve" in user_content
        assert "Tech giants" in user_content

    @patch("src.agents.news_synthesizer_agent.news_agent.get_client")
    def test_system_prompt_included(self, mock_get_client):
        mock_get_client.return_value.chat.completions.create.return_value = _mock_response("Answer.")
        from src.agents.news_synthesizer_agent.news_agent import synthesize_news

        synthesize_news([_ARTICLE_1])
        call_kwargs = mock_get_client.return_value.chat.completions.create.call_args.kwargs
        system_msgs = [m for m in call_kwargs["messages"] if m["role"] == "system"]
        assert len(system_msgs) >= 1

    def test_raises_on_non_list_input(self):
        from src.agents.news_synthesizer_agent.news_agent import synthesize_news

        with pytest.raises(TypeError):
            synthesize_news("some news article")  # type: ignore[arg-type]

    def test_raises_on_non_string_elements(self):
        from src.agents.news_synthesizer_agent.news_agent import synthesize_news

        with pytest.raises(ValueError):
            synthesize_news([_ARTICLE_1, 12345])  # type: ignore[list-item]
