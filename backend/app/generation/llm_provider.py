import abc
from dataclasses import dataclass
import re
from typing import Optional
import httpx

from app.core.config import settings


@dataclass
class LLMResponse:
    """Standardized response from any LLM provider."""

    content: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    model: str = ""


class BaseLLMProvider(abc.ABC):
    """Abstract interface for LLM generation providers."""

    @abc.abstractmethod
    async def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.1,
    ) -> LLMResponse:
        """Generate a completion given system and user prompts."""
        pass


class OpenAILLMProvider(BaseLLMProvider):
    """OpenAI Chat Completions provider."""

    def __init__(self, api_key: str, model: str = "gpt-4o-mini"):
        self.api_key = api_key
        self.model = model

    async def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.1,
    ) -> LLMResponse:
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {self.api_key}"},
                json={
                    "model": self.model,
                    "temperature": temperature,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                },
            )
            resp.raise_for_status()
            data = resp.json()
            usage = data.get("usage", {})
            return LLMResponse(
                content=data["choices"][0]["message"]["content"],
                prompt_tokens=usage.get("prompt_tokens", 0),
                completion_tokens=usage.get("completion_tokens", 0),
                model=self.model,
            )


class GeminiLLMProvider(BaseLLMProvider):
    """Google Gemini REST API provider."""

    def __init__(self, api_key: str, model: str = "gemini-2.0-flash"):
        self.api_key = api_key
        self.model = model

    async def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.1,
    ) -> LLMResponse:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent"
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(
                url,
                params={"key": self.api_key},
                json={
                    "system_instruction": {"parts": [{"text": system_prompt}]},
                    "contents": [{"parts": [{"text": user_prompt}]}],
                    "generationConfig": {"temperature": temperature},
                },
            )
            resp.raise_for_status()
            data = resp.json()
            text = data["candidates"][0]["content"]["parts"][0]["text"]
            usage = data.get("usageMetadata", {})
            return LLMResponse(
                content=text,
                prompt_tokens=usage.get("promptTokenCount", 0),
                completion_tokens=usage.get("candidatesTokenCount", 0),
                model=self.model,
            )


class OllamaLLMProvider(BaseLLMProvider):
    """Local Ollama chat completions provider."""

    def __init__(self, base_url: str, model: str = "llama3.1"):
        self.base_url = base_url.rstrip("/")
        self.model = model

    async def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.1,
    ) -> LLMResponse:
        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(
                f"{self.base_url}/api/chat",
                json={
                    "model": self.model,
                    "stream": False,
                    "options": {"temperature": temperature},
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                },
            )
            resp.raise_for_status()
            data = resp.json()
            return LLMResponse(
                content=data["message"]["content"],
                prompt_tokens=data.get("prompt_eval_count", 0),
                completion_tokens=data.get("eval_count", 0),
                model=self.model,
            )


class MockLLMProvider(BaseLLMProvider):
    """Deterministic extractive mock LLM for offline testing and Baseline A verification."""

    async def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.1,
    ) -> LLMResponse:
        # Extract evidence blocks from the formatted user prompt
        evidence_matches = re.findall(
            r"\[Evidence \d+ \| (.*?) \| Page (\d+)\]\n(.*?)(?=\n\n\[Evidence|\n\nQuestion:|$)",
            user_prompt,
            flags=re.DOTALL,
        )
        if not evidence_matches:
            content = "No relevant document passages were retrieved to answer this question."
        else:
            top_doc, top_page, top_text = evidence_matches[0]
            snippet = top_text.strip().replace("\n", " ")
            if len(snippet) > 350:
                snippet = snippet[:347] + "..."
            content = (
                f"Based on the retrieved document evidence ({top_doc}, Page {top_page}): "
                f"{snippet} [Source: {top_doc}, Page {top_page}]"
            )

        return LLMResponse(
            content=content,
            prompt_tokens=len(user_prompt.split()),
            completion_tokens=len(content.split()),
            model="mock-extractive-v1",
        )


def get_llm_provider() -> BaseLLMProvider:
    """Factory returning the configured LLM provider."""
    provider = settings.DEFAULT_LLM_PROVIDER.lower()
    if provider == "openai" and settings.OPENAI_API_KEY:
        return OpenAILLMProvider(api_key=settings.OPENAI_API_KEY, model=settings.DEFAULT_LLM_MODEL)
    if provider == "gemini" and settings.GEMINI_API_KEY:
        return GeminiLLMProvider(api_key=settings.GEMINI_API_KEY, model=settings.DEFAULT_LLM_MODEL)
    if provider == "ollama":
        return OllamaLLMProvider(base_url=settings.OLLAMA_BASE_URL, model=settings.DEFAULT_LLM_MODEL)
    return MockLLMProvider()

