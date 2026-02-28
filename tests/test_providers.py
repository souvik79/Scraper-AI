"""Tests for provider registry and base class."""

from __future__ import annotations

import json

import pytest

from scraper_ai.config import Settings
from scraper_ai.models import PageResult
from scraper_ai.providers import get_provider, list_providers
from scraper_ai.providers.base import (
    EXTRACT_SYSTEM_PROMPT,
    PHASE2_SYSTEM_PROMPT,
    AIProvider,
    ExtractionError,
)


class TestProviderRegistry:
    def test_list_providers(self):
        providers = list_providers()
        assert "anthropic" in providers
        assert "openai" in providers
        assert "ollama" in providers
        assert "groq" in providers
        assert "gemini" in providers

    def test_list_providers_returns_sorted(self):
        providers = list_providers()
        assert providers == sorted(providers)

    def test_get_provider_unknown_raises(self, settings):
        with pytest.raises(ValueError, match="Unknown provider 'nonexistent'"):
            get_provider("nonexistent", settings)

    def test_get_provider_unknown_shows_available(self, settings):
        with pytest.raises(ValueError, match="Available:"):
            get_provider("bad", settings)

    def test_get_provider_ollama(self, settings):
        provider = get_provider("ollama", settings)
        assert provider.name == "ollama"
        assert isinstance(provider, AIProvider)


class TestAIProviderBase:
    def test_build_messages(self, settings):
        provider = get_provider("ollama", settings)
        system, user = provider._build_messages(
            "<p>Hello</p>", "Extract products", "https://example.com"
        )
        assert "https://example.com" in system
        assert "Extract products" in user
        assert "---PAGE CONTENT---" in user
        assert "<p>Hello</p>" in user

    def test_build_phase2_messages(self, settings):
        provider = get_provider("ollama", settings)
        system, user = provider._build_phase2_messages(
            "<p>Hello</p>", "https://example.com"
        )
        assert "https://example.com" in system
        assert "---HTML---" in user
        assert "<p>Hello</p>" in user

    def test_parse_response_valid_json(self, settings):
        provider = get_provider("ollama", settings)
        raw = json.dumps({
            "data": [{"name": "Test"}],
            "next_urls": [],
            "detail_urls": [],
            "summary": "Found 1 item",
        })
        result = provider._parse_response(raw)
        assert isinstance(result, PageResult)
        assert len(result.data) == 1
        assert result.data[0]["name"] == "Test"

    def test_parse_response_with_code_fences(self, settings):
        provider = get_provider("ollama", settings)
        raw = '```json\n{"data": [{"name": "Test"}], "next_urls": [], "detail_urls": [], "summary": ""}\n```'
        result = provider._parse_response(raw)
        assert len(result.data) == 1

    def test_parse_response_concatenated_json(self, settings):
        """AI sometimes returns two JSON objects concatenated."""
        provider = get_provider("ollama", settings)
        raw = '{"data": [], "next_urls": [], "detail_urls": [], "summary": ""} {"name": "Extra"}'
        result = provider._parse_response(raw)
        assert len(result.data) == 1
        assert result.data[0]["name"] == "Extra"

    def test_parse_response_invalid_json_raises(self, settings):
        provider = get_provider("ollama", settings)
        with pytest.raises(ExtractionError, match="Failed to parse"):
            provider._parse_response("not json at all")

    def test_parse_response_partial_fields(self, settings):
        provider = get_provider("ollama", settings)
        raw = '{"data": [{"x": 1}]}'
        result = provider._parse_response(raw)
        assert result.next_urls == []
        assert result.detail_urls == []

    def test_max_chunk_chars_default(self, settings):
        provider = get_provider("ollama", settings)
        assert provider.max_chunk_chars == 48_000

    def test_phase2_system_prompt_has_placeholder(self):
        assert "{page_url}" in PHASE2_SYSTEM_PROMPT

    def test_extract_system_prompt_has_placeholder(self):
        assert "{page_url}" in EXTRACT_SYSTEM_PROMPT


class TestProviderInit:
    """Test provider-specific initialization requirements."""

    def test_anthropic_requires_api_key(self):
        s = Settings(scraper_api_key="test", anthropic_api_key="")
        with pytest.raises(ValueError, match="ANTHROPIC_API_KEY"):
            get_provider("anthropic", s)

    def test_openai_requires_api_key(self):
        s = Settings(scraper_api_key="test", openai_api_key="")
        with pytest.raises(ValueError, match="OPENAI_API_KEY"):
            get_provider("openai", s)

    def test_groq_requires_api_key(self):
        s = Settings(scraper_api_key="test", groq_api_key="")
        with pytest.raises(ValueError, match="GROQ_API_KEY"):
            get_provider("groq", s)

    def test_gemini_requires_api_key(self):
        s = Settings(scraper_api_key="test", gemini_api_key="")
        with pytest.raises(ValueError, match="GEMINI_API_KEY"):
            get_provider("gemini", s)

    def test_ollama_no_key_required(self):
        s = Settings(scraper_api_key="test")
        provider = get_provider("ollama", s)
        assert provider.name == "ollama"

    def test_groq_max_chunk_chars(self, settings):
        provider = get_provider("groq", settings)
        assert provider.max_chunk_chars == 12_000

    def test_gemini_max_chunk_chars(self, settings):
        provider = get_provider("gemini", settings)
        assert provider.max_chunk_chars == 500_000
