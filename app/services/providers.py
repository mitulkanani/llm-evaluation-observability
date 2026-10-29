from dataclasses import dataclass
from math import ceil
from typing import Protocol


@dataclass(frozen=True)
class Generation:
    output: str
    prompt_tokens: int
    completion_tokens: int


class ProviderError(RuntimeError):
    """Raised when a model provider cannot return a usable completion."""


class LLMProvider(Protocol):
    name: str

    def generate(
        self,
        prompt: str,
        model: str,
        *,
        temperature: float = 0.0,
        mock_response: str | None = None,
    ) -> Generation: ...


def approximate_tokens(text: str) -> int:
    """Cheap token estimate for fallback use; not equivalent to a tokenizer."""
    return max(1, ceil(len(text) / 4)) if text else 0


class MockProvider:
    """Deterministic provider so tests and demos run without API credentials."""

    name = "mock"

    def generate(
        self,
        prompt: str,
        model: str,
        *,
        temperature: float = 0.0,
        mock_response: str | None = None,
    ) -> Generation:
        output = mock_response if mock_response is not None else f"Mock response: {prompt[-500:]}"
        return Generation(
            output=output,
            prompt_tokens=approximate_tokens(prompt),
            completion_tokens=approximate_tokens(output),
        )


class OpenAIProvider:
    """Optional OpenAI Chat Completions adapter (requires `pip install .[openai]`)."""

    name = "openai"

    def __init__(self, api_key: str | None = None) -> None:
        try:
            from openai import OpenAI
        except ImportError as exc:
            raise ProviderError("OpenAI support is optional; install with `pip install -e '.[openai]'`.") from exc
        if not api_key:
            import os
            api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ProviderError("OPENAI_API_KEY is required for provider='openai'.")
        self._client = OpenAI(api_key=api_key)

    def generate(
        self,
        prompt: str,
        model: str,
        *,
        temperature: float = 0.0,
        mock_response: str | None = None,
    ) -> Generation:
        del mock_response  # mock fixtures must never alter a live model result
        try:
            response = self._client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                temperature=temperature,
            )
            output = response.choices[0].message.content or ""
            usage = response.usage
            prompt_tokens = getattr(usage, "prompt_tokens", 0) if usage else 0
            completion_tokens = getattr(usage, "completion_tokens", 0) if usage else 0
            return Generation(
                output=output,
                prompt_tokens=int(prompt_tokens or 0),
                completion_tokens=int(completion_tokens or 0),
            )
        except Exception as exc:
            raise ProviderError(f"OpenAI request failed: {type(exc).__name__}: {exc}") from exc


def build_provider(provider_name: str) -> LLMProvider:
    if provider_name == "mock":
        return MockProvider()
    if provider_name == "openai":
        return OpenAIProvider()
    raise ProviderError(f"Unsupported provider '{provider_name}'.")
