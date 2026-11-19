#!/usr/bin/env python3
"""
LLM Client Layer — Multi-Provider Support.

Supports OpenAI, Anthropic, and local model providers.
Designed to be pluggable: the translator pipeline can use any provider.
"""

from __future__ import annotations

import json
import os
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, ClassVar
from urllib.parse import urlsplit


@dataclass
class LLMResponse:
    """Standardized response from any LLM provider."""
    content: str
    model: str
    provider: str
    tokens_used: int = 0
    cost_usd: float = 0.0
    latency_ms: int = 0
    finish_reason: str = "completed"


class LLMClient(ABC):
    """Abstract base class for LLM providers."""

    def __init__(self, model: str, api_key: str | None = None, **kwargs):
        self.model = model
        self.api_key = api_key
        self.kwargs = kwargs

    @abstractmethod
    def complete(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.3,
        max_tokens: int = 2000,
        **kwargs,
    ) -> LLMResponse:
        """Generate a completion from the LLM."""
        ...

    @abstractmethod
    def is_available(self) -> bool:
        """Check if the provider is available (API key set, package installed)."""
        ...


class OpenAIClient(LLMClient):
    """OpenAI API client (GPT-3.5, GPT-4, GPT-4o, etc.)."""

    def __init__(
        self,
        model: str = "gpt-4o",
        api_key: str | None = None,
        base_url: str | None = None,
        **kwargs,
    ) -> None:
        super().__init__(model, api_key, **kwargs)
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.base_url = base_url or os.getenv("OPENAI_BASE_URL")
        self._client = None

    def _get_client(self):
        """Lazy-load OpenAI client."""
        if self._client is None:
            try:
                from openai import OpenAI  # type: ignore

                self._client = OpenAI(
                    api_key=self.api_key,
                    base_url=self.base_url,
                    timeout=self.kwargs.get("timeout", 60.0),
                    max_retries=self.kwargs.get("max_retries", 2),
                )
            except ImportError:
                raise ImportError(
                    "openai package not installed. Run: pip install openai"
                )
        return self._client

    def is_available(self) -> bool:
        """Check if OpenAI API key is configured."""
        return bool(self.api_key)

    def complete(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.3,
        max_tokens: int = 2000,
        **kwargs,
    ) -> LLMResponse:
        """Generate completion via OpenAI API."""
        start = time.time()

        client = self._get_client()
        response = client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs,
        )

        content = response.choices[0].message.content or ""
        latency_ms = int((time.time() - start) * 1000)

        return LLMResponse(
            content=content,
            model=self.model,
            provider="openai",
            tokens_used=response.usage.total_tokens if response.usage else 0,
            latency_ms=latency_ms,
            finish_reason=response.choices[0].finish_reason or "completed",
        )


class AnthropicClient(LLMClient):
    """Anthropic API client (Claude 3, Claude 3.5, etc.)."""

    def __init__(
        self,
        model: str = "claude-3-5-sonnet-20241022",
        api_key: str | None = None,
        **kwargs,
    ) -> None:
        super().__init__(model, api_key, **kwargs)
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        self._client = None

    def _get_client(self):
        """Lazy-load Anthropic client."""
        if self._client is None:
            try:
                import anthropic  # type: ignore

                self._client = anthropic.Anthropic(
                    api_key=self.api_key,
                    timeout=self.kwargs.get("timeout", 60.0),
                    max_retries=self.kwargs.get("max_retries", 2),
                )
            except ImportError:
                raise ImportError(
                    "anthropic package not installed. Run: pip install anthropic"
                )
        return self._client

    def is_available(self) -> bool:
        """Check if Anthropic API key is configured."""
        return bool(self.api_key)

    def complete(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.3,
        max_tokens: int = 2000,
        **kwargs,
    ) -> LLMResponse:
        """Generate completion via Anthropic API."""
        start = time.time()

        client = self._get_client()

        # Convert messages to Anthropic format
        system_message = ""
        user_messages = []
        for msg in messages:
            if msg["role"] == "system":
                system_message = msg["content"]
            else:
                user_messages.append(msg)

        response = client.messages.create(
            model=self.model,
            system=system_message or None,
            messages=user_messages,
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs,
        )

        content = ""
        for block in response.content:
            if hasattr(block, "text"):
                content += block.text

        latency_ms = int((time.time() - start) * 1000)

        return LLMResponse(
            content=content,
            model=self.model,
            provider="anthropic",
            tokens_used=response.usage.input_tokens + response.usage.output_tokens
            if response.usage
            else 0,
            latency_ms=latency_ms,
            finish_reason=response.stop_reason or "completed",
        )


class LocalClient(LLMClient):
    """Local model client (Ollama, LM Studio, etc. via OpenAI-compatible API)."""

    def __init__(
        self,
        model: str = "llama3.1",
        api_key: str | None = None,
        base_url: str = "http://localhost:11434/v1",
        **kwargs,
    ) -> None:
        super().__init__(model, api_key, **kwargs)
        self.base_url = base_url or os.getenv("LOCAL_LLM_BASE_URL", "http://localhost:11434/v1")
        self._client = None

    def _get_client(self):
        """Lazy-load OpenAI-compatible client for local models."""
        if self._client is None:
            try:
                from openai import OpenAI  # type: ignore

                self._client = OpenAI(
                    api_key=self.api_key or "local",
                    base_url=self.base_url,
                    timeout=self.kwargs.get("timeout", 120.0),
                    max_retries=self.kwargs.get("max_retries", 1),
                )
            except ImportError:
                raise ImportError(
                    "openai package not installed. Run: pip install openai"
                )
        return self._client

    def _parse_host_port(self) -> tuple[str, int]:
        """Parse host and port from base_url (scheme-default ports honored)."""
        parts = urlsplit(self.base_url)
        host = parts.hostname or "localhost"
        port = parts.port or (443 if parts.scheme == "https" else 80)
        return host, port

    def is_available(self) -> bool:
        """Check if local server is reachable."""
        import socket

        try:
            host, port = self._parse_host_port()
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(2)
                return sock.connect_ex((host, port)) == 0
        except Exception:
            return False

    def complete(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.3,
        max_tokens: int = 2000,
        **kwargs,
    ) -> LLMResponse:
        """Generate completion via local OpenAI-compatible API."""
        start = time.time()

        client = self._get_client()
        response = client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs,
        )

        content = response.choices[0].message.content or ""
        latency_ms = int((time.time() - start) * 1000)

        return LLMResponse(
            content=content,
            model=self.model,
            provider="local",
            tokens_used=response.usage.total_tokens if response.usage else 0,
            latency_ms=latency_ms,
            finish_reason=response.choices[0].finish_reason or "completed",
        )


class LLMManager:
    """Manages LLM client selection and fallback."""

    PROVIDERS: ClassVar[dict[str, type]] = {
        "openai": OpenAIClient,
        "anthropic": AnthropicClient,
        "local": LocalClient,
    }

    def __init__(
        self,
        provider: str = "openai",
        model: str | None = None,
        api_key: str | None = None,
        fallback_provider: str | None = None,
        fallback_model: str | None = None,
        **kwargs,
    ) -> None:
        self.provider = provider
        self.fallback_provider = fallback_provider
        self.fallback_model = fallback_model
        self.kwargs = kwargs

        # Default models per provider
        default_models = {
            "openai": "gpt-4o",
            "anthropic": "claude-3-5-sonnet-20241022",
            "local": "llama3.1",
        }

        self.model = model or default_models.get(provider, "gpt-4o")
        self.api_key = api_key

        # Initialize primary client
        self.primary = self._create_client(provider, self.model, api_key, **kwargs)

        # Initialize fallback client if specified
        self.fallback = None
        if fallback_provider:
            self.fallback = self._create_client(
                fallback_provider, fallback_model or default_models.get(fallback_provider, "gpt-3.5-turbo"),
                api_key, **kwargs
            )

    def _create_client(
        self,
        provider: str,
        model: str,
        api_key: str | None,
        **kwargs,
    ) -> LLMClient:
        """Create an LLM client instance."""
        client_class = self.PROVIDERS.get(provider)
        if not client_class:
            raise ValueError(f"Unknown provider: {provider}. Available: {list(self.PROVIDERS.keys())}")
        return client_class(model=model, api_key=api_key, **kwargs)

    def complete(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.3,
        max_tokens: int = 2000,
        use_fallback: bool = True,
        **kwargs,
    ) -> LLMResponse:
        """Generate completion with optional fallback."""
        last_error: Exception | None = None

        # Try primary provider
        if self.primary and self.primary.is_available():
            try:
                return self.primary.complete(
                    messages, temperature=temperature, max_tokens=max_tokens, **kwargs
                )
            except Exception as exc:
                last_error = exc

        # Try fallback provider
        if use_fallback and self.fallback and self.fallback.is_available():
            try:
                return self.fallback.complete(
                    messages, temperature=temperature, max_tokens=max_tokens, **kwargs
                )
            except Exception as exc:
                last_error = exc

        # No provider available — raise error
        if last_error:
            raise last_error

        raise RuntimeError(
            f"No LLM provider available. Primary ({self.provider}) and fallback "
            f"({self.fallback_provider}) are not configured or not reachable."
        )

    def get_status(self) -> dict[str, Any]:
        """Get status of all configured providers."""
        return {
            "primary": {
                "provider": self.provider,
                "model": self.model,
                "available": self.primary.is_available() if self.primary else False,
            },
            "fallback": {
                "provider": self.fallback_provider,
                "model": self.fallback_model,
                "available": self.fallback.is_available() if self.fallback else False,
            }
            if self.fallback
            else None,
        }


def create_llm_manager(
    provider: str = "openai",
    model: str | None = None,
    api_key: str | None = None,
    **kwargs,
) -> LLMManager:
    """Factory function to create an LLMManager."""
    return LLMManager(
        provider=provider,
        model=model,
        api_key=api_key,
        **kwargs,
    )


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="LLM Client Test")
    parser.add_argument("--provider", default="openai", help="LLM provider")
    parser.add_argument("--model", help="Model name")
    parser.add_argument("--message", default="Hello, translate this to Arabic: Hello world", help="Test message")

    args = parser.parse_args()

    try:
        manager = create_llm_manager(provider=args.provider, model=args.model)
        status = manager.get_status()
        print("LLM Manager Status:")
        print(json.dumps(status, indent=2))

        if status["primary"]["available"]:
            response = manager.complete(
                [{"role": "user", "content": args.message}],
                temperature=0.3,
            )
            print(f"\nResponse ({response.provider}, {response.model}):")
            print(response.content)
            print(f"\nTokens: {response.tokens_used}, Latency: {response.latency_ms}ms")
        else:
            print(f"\nProvider {args.provider} not available. Set API key.")
    except Exception as exc:
        print(f"Error: {exc}")
