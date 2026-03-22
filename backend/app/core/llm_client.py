from __future__ import annotations

import json
import logging
from abc import ABC, abstractmethod
from typing import Any

import httpx

from app.core.config import settings
from app.models.enums import LLMProvider

logger = logging.getLogger(__name__)

SUPPORTED_LLM_PROVIDERS = tuple(item.value for item in LLMProvider)


class BaseLLMClient(ABC):
    @abstractmethod
    async def complete(
        self,
        prompt: str,
        system: str = "",
        temperature: float = 0.3,
        max_tokens: int = 4096,
    ) -> str:
        """Generate plain text completion."""

    async def complete_json(
        self,
        prompt: str,
        system: str = "",
        temperature: float = 0.2,
        max_tokens: int = 4096,
    ) -> dict:
        raw = await self.complete(
            prompt=prompt,
            system=system + "\n\nFAQAT JSON qaytaring. Markdown yoki izoh yozmang.",
            temperature=temperature,
            max_tokens=max_tokens,
        )

        cleaned = raw.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.split("```", 2)[1]
            if cleaned.startswith("json"):
                cleaned = cleaned[4:]
            cleaned = cleaned.rsplit("```", 1)[0].strip()

        try:
            return json.loads(cleaned)
        except json.JSONDecodeError as exc:
            logger.error("LLM JSON parse xatosi: %s", exc)
            raise ValueError(f"LLM valid JSON qaytarmadi: {exc}") from exc


class ClaudeClient(BaseLLMClient):
    def __init__(self, api_key: str, model: str = "claude-sonnet-4-20250514") -> None:
        try:
            import anthropic
        except ImportError as exc:  # pragma: no cover
            raise ImportError("anthropic paketi kerak: pip install anthropic") from exc

        self._client = anthropic.AsyncAnthropic(api_key=api_key)
        self._model = model

    async def complete(
        self,
        prompt: str,
        system: str = "",
        temperature: float = 0.3,
        max_tokens: int = 4096,
    ) -> str:
        payload: dict[str, Any] = {
            "model": self._model,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": [{"role": "user", "content": prompt}],
        }
        if system:
            payload["system"] = system

        response = await self._client.messages.create(**payload)
        return response.content[0].text


class OpenAIClient(BaseLLMClient):
    def __init__(self, api_key: str, model: str = "gpt-4o") -> None:
        try:
            from openai import AsyncOpenAI
        except ImportError as exc:  # pragma: no cover
            raise ImportError("openai paketi kerak: pip install openai") from exc

        self._client = AsyncOpenAI(api_key=api_key)
        self._model = model

    async def complete(
        self,
        prompt: str,
        system: str = "",
        temperature: float = 0.3,
        max_tokens: int = 4096,
    ) -> str:
        messages: list[dict[str, str]] = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        response = await self._client.chat.completions.create(
            model=self._model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        content = response.choices[0].message.content
        return content or ""


class GeminiClient(BaseLLMClient):
    def __init__(self, api_key: str, model: str = "gemini-1.5-pro") -> None:
        self._api_key = api_key
        self._model = model
        self._base = "https://generativelanguage.googleapis.com/v1beta"

    async def complete(
        self,
        prompt: str,
        system: str = "",
        temperature: float = 0.3,
        max_tokens: int = 4096,
    ) -> str:
        full_prompt = f"{system}\n\n{prompt}" if system else prompt
        payload = {
            "contents": [{"parts": [{"text": full_prompt}]}],
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": max_tokens,
            },
        }
        url = f"{self._base}/models/{self._model}:generateContent?key={self._api_key}"
        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            data = response.json()
        return data["candidates"][0]["content"]["parts"][0]["text"]


class OllamaClient(BaseLLMClient):
    def __init__(self, base_url: str = "http://localhost:11434", model: str = "llama3.1") -> None:
        self._base_url = base_url.rstrip("/")
        self._model = model

    async def complete(
        self,
        prompt: str,
        system: str = "",
        temperature: float = 0.3,
        max_tokens: int = 4096,
    ) -> str:
        payload = {
            "model": self._model,
            "prompt": prompt,
            "system": system,
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
            },
        }
        async with httpx.AsyncClient(timeout=120) as client:
            response = await client.post(f"{self._base_url}/api/generate", json=payload)
            response.raise_for_status()
            data = response.json()
        return data.get("response", "")


class DeepSeekClient(BaseLLMClient):
    def __init__(
        self,
        api_key: str,
        model: str = "deepseek-chat",
        base_url: str = "https://api.deepseek.com",
    ) -> None:
        self._api_key = api_key
        self._model = model
        self._base_url = base_url.rstrip("/")

    async def complete(
        self,
        prompt: str,
        system: str = "",
        temperature: float = 0.3,
        max_tokens: int = 4096,
    ) -> str:
        messages: list[dict[str, str]] = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": self._model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": False,
        }
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }
        async with httpx.AsyncClient(timeout=120) as client:
            response = await client.post(f"{self._base_url}/chat/completions", json=payload, headers=headers)
            response.raise_for_status()
            data = response.json()
        return data["choices"][0]["message"]["content"]


def normalize_llm_provider(provider: str | LLMProvider | None = None) -> str:
    selected = (provider.value if isinstance(provider, LLMProvider) else provider or settings.default_llm_provider).strip().lower()
    if selected not in SUPPORTED_LLM_PROVIDERS:
        supported = " | ".join(SUPPORTED_LLM_PROVIDERS)
        raise ValueError(f"Noma'lum LLM provider: '{selected}'. Qo'llab-quvvatlanadigan: {supported}")
    return selected


def get_default_model_for_provider(provider: str | LLMProvider | None = None) -> str:
    selected = normalize_llm_provider(provider)
    defaults = {
        LLMProvider.CLAUDE.value: settings.anthropic_model,
        LLMProvider.OPENAI.value: settings.openai_model,
        LLMProvider.GEMINI.value: settings.gemini_model,
        LLMProvider.OLLAMA.value: settings.ollama_model,
        LLMProvider.DEEPSEEK.value: settings.deepseek_model,
    }
    return defaults[selected]


def resolve_llm_selection(
    provider: str | LLMProvider | None = None,
    model: str | None = None,
) -> tuple[str, str]:
    selected_provider = normalize_llm_provider(provider)
    normalized_model = (model or "").strip() or get_default_model_for_provider(selected_provider)
    return selected_provider, normalized_model


def format_llm_selection(
    provider: str | LLMProvider | None = None,
    model: str | None = None,
) -> str:
    selected_provider, selected_model = resolve_llm_selection(provider=provider, model=model)
    return f"{selected_provider}:{selected_model}"


def get_llm_client(
    provider: str | LLMProvider | None = None,
    model: str | None = None,
) -> BaseLLMClient:
    selected, selected_model = resolve_llm_selection(provider=provider, model=model)

    if selected == "claude":
        return ClaudeClient(api_key=settings.anthropic_api_key, model=selected_model)

    if selected == "openai":
        return OpenAIClient(api_key=settings.openai_api_key, model=selected_model)

    if selected == "gemini":
        return GeminiClient(api_key=settings.google_api_key, model=selected_model)

    if selected == "ollama":
        return OllamaClient(base_url=settings.ollama_base_url, model=selected_model)

    if selected == "deepseek":
        return DeepSeekClient(api_key=settings.deepseek_api_key, model=selected_model)

    supported = " | ".join(SUPPORTED_LLM_PROVIDERS)
    raise ValueError(f"Noma'lum LLM provider: '{selected}'. Qo'llab-quvvatlanadigan: {supported}")
