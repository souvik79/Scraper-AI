"""Provider registry and factory with lazy imports."""

from __future__ import annotations

import importlib

from scrapper_ai.config import Settings
from scrapper_ai.providers.base import AIProvider

_PROVIDER_REGISTRY: dict[str, str] = {
    "openai": "scrapper_ai.providers.openai.OpenAIProvider",
    "anthropic": "scrapper_ai.providers.anthropic.AnthropicProvider",
    "ollama": "scrapper_ai.providers.ollama.OllamaProvider",
    "groq": "scrapper_ai.providers.groq.GroqProvider",
    "gemini": "scrapper_ai.providers.gemini.GeminiProvider",
}


def get_provider(name: str, settings: Settings) -> AIProvider:
    """Instantiate an AI provider by name. Uses lazy imports."""
    if name not in _PROVIDER_REGISTRY:
        available = ", ".join(sorted(_PROVIDER_REGISTRY))
        raise ValueError(f"Unknown provider '{name}'. Available: {available}")

    module_path, class_name = _PROVIDER_REGISTRY[name].rsplit(".", 1)
    module = importlib.import_module(module_path)
    provider_class = getattr(module, class_name)
    return provider_class(settings)


def list_providers() -> list[str]:
    return sorted(_PROVIDER_REGISTRY)
