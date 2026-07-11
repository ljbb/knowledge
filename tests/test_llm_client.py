"""测试 llm_client 模块（不调用真实 API）"""

import pytest
from engine.llm_client import LLMClient, LLMClientError


class TestLLMClient:
    def test_init_with_default_provider(self):
        client = LLMClient()
        assert client.provider in ("claude", "deepseek", "gemini")

    def test_init_with_specific_provider(self):
        client = LLMClient("claude")
        assert client.provider == "claude"

    def test_init_with_unknown_provider_raises(self):
        with pytest.raises(ValueError, match="未知的 LLM provider"):
            LLMClient("nonexistent")

    def test_is_available_false_when_no_api_key(self, monkeypatch):
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
        monkeypatch.delenv("GEMINI_API_KEY", raising=False)
        client = LLMClient("claude")
        assert client.is_available is False

    def test_chat_raises_when_not_available(self, monkeypatch):
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        client = LLMClient("claude")
        with pytest.raises(LLMClientError, match="不可用"):
            client.chat([{"role": "user", "content": "test"}])
