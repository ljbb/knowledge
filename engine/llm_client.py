"""LLM 统一调用接口 — 支持 Claude / DeepSeek / Gemini"""

import os
from typing import Any

from engine.config import get_llm_config, load_config


class LLMClientError(Exception):
    """LLM 调用错误。"""
    pass


class LLMClient:
    """统一的 LLM 客户端，封装多 provider 调用。"""

    def __init__(self, provider: str | None = None):
        """初始化 LLM 客户端。

        Args:
            provider: LLM provider 名称 (claude/deepseek/gemini)，None 使用默认。
        """
        config = load_config()
        llm_config = config["llm"]
        self._provider = provider or llm_config["default"]
        self._cfg = get_llm_config(self._provider)
        self._available = self._check_available()

    @property
    def provider(self) -> str:
        return self._provider

    @property
    def is_available(self) -> bool:
        return self._available

    def _check_available(self) -> bool:
        """检查 API key 是否已配置且 SDK 是否已安装。"""
        api_key = os.environ.get(self._cfg["api_key_env"], "")
        if not api_key:
            return False

        provider_type = self._cfg["type"]
        try:
            if provider_type == "anthropic":
                import anthropic  # noqa: F401
            elif provider_type in ("openai_compatible",):
                import openai  # noqa: F401
            elif provider_type == "google":
                import google.genai  # noqa: F401
        except ImportError:
            return False

        return True

    def chat(
        self,
        messages: list[dict[str, Any]],
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> str:
        """向 LLM 发送消息并返回文本响应。

        Args:
            messages: 消息列表 [{"role": "system"|"user"|"assistant", "content": "..."}]
            model: 模型名称，None 使用默认
            temperature: 温度参数
            max_tokens: 最大输出 token

        Returns:
            LLM 的文本响应

        Raises:
            LLMClientError: LLM 不可用或调用失败
        """
        if not self._available:
            raise LLMClientError(
                f"LLM provider '{self._provider}' 不可用。"
                f"请设置环境变量 {self._cfg['api_key_env']}。"
            )

        model = model or self._cfg.get("default_model", "")
        provider_type = self._cfg["type"]

        try:
            if provider_type == "anthropic":
                return self._chat_anthropic(messages, model, temperature, max_tokens)
            elif provider_type in ("openai_compatible",):
                return self._chat_openai_compatible(messages, model, temperature, max_tokens)
            elif provider_type == "google":
                return self._chat_google(messages, model, temperature, max_tokens)
            else:
                raise LLMClientError(f"不支持的 provider 类型: {provider_type}")
        except Exception as e:
            raise LLMClientError(f"LLM 调用失败 [{self._provider}]: {e}") from e

    def _chat_anthropic(
        self,
        messages: list[dict[str, Any]],
        model: str,
        temperature: float,
        max_tokens: int,
    ) -> str:
        import anthropic

        client = anthropic.Anthropic()
        system = ""
        chat_messages = []
        for m in messages:
            if m["role"] == "system":
                system = m["content"]
            else:
                chat_messages.append(m)

        response = client.messages.create(
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
            system=system or anthropic.NOT_GIVEN,
            messages=chat_messages,
        )
        return response.content[0].text

    def _chat_openai_compatible(
        self,
        messages: list[dict[str, Any]],
        model: str,
        temperature: float,
        max_tokens: int,
    ) -> str:
        import openai

        client = openai.OpenAI(
            api_key=os.environ[self._cfg["api_key_env"]],
            base_url=self._cfg.get("base_url"),
        )
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return response.choices[0].message.content or ""

    def _chat_google(
        self,
        messages: list[dict[str, Any]],
        model: str,
        temperature: float,
        max_tokens: int,
    ) -> str:
        from google import genai

        client = genai.Client(api_key=os.environ[self._cfg["api_key_env"]])
        contents = []
        system_instruction = ""
        for m in messages:
            if m["role"] == "system":
                system_instruction = m["content"]
            elif m["role"] == "user":
                contents.append({"role": "user", "parts": [{"text": m["content"]}]})
            elif m["role"] == "assistant":
                contents.append({"role": "model", "parts": [{"text": m["content"]}]})

        config_args = {
            "temperature": temperature,
            "max_output_tokens": max_tokens,
        }
        if system_instruction:
            config_args["system_instruction"] = system_instruction

        response = client.models.generate_content(
            model=model,
            contents=contents,
            config=genai.types.GenerateContentConfig(**config_args),
        )
        return response.text
