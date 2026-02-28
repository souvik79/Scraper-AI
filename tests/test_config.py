"""Tests for scraper_ai.config module."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from scraper_ai.config import Settings


class TestSettings:
    def test_default_values(self):
        s = Settings(scraper_api_key="test-key")
        assert s.scraper_api_key == "test-key"
        assert s.openai_api_key == ""
        assert s.anthropic_api_key == ""
        assert s.claude_model == "claude-haiku-4-5-20251001"
        assert s.ollama_base_url == "http://localhost:11434"
        assert s.ollama_model == "phi4-mini"
        assert s.groq_api_key == ""
        assert s.groq_model == "llama-3.1-8b-instant"
        assert s.gemini_api_key == ""
        assert s.gemini_model == "gemini-2.5-flash"
        assert s.render_js is True
        assert s.auto_scroll is False
        assert s.max_pages == 100
        assert s.temperature == 0.0
        assert s.default_provider == "ollama"
        assert s.processor_provider == ""

    def test_frozen_dataclass(self):
        s = Settings(scraper_api_key="test-key")
        with pytest.raises(AttributeError):
            s.scraper_api_key = "new-key"  # type: ignore[misc]

    def test_from_env_reads_env_vars(self):
        env = {
            "SCRAPER_API_KEY": "my-scraper-key",
            "OPENAI_API_KEY": "my-openai-key",
            "ANTHROPIC_API_KEY": "my-anthropic-key",
            "CLAUDE_MODEL": "claude-sonnet-4-20250514",
            "OLLAMA_BASE_URL": "http://myhost:11434",
            "OLLAMA_MODEL": "llama3",
            "GROQ_API_KEY": "my-groq-key",
            "GROQ_MODEL": "mixtral",
            "GEMINI_API_KEY": "my-gemini-key",
            "GEMINI_MODEL": "gemini-pro",
            "DEFAULT_PROVIDER": "anthropic",
            "PROCESSOR_PROVIDER": "gemini",
        }
        with patch.dict("os.environ", env, clear=False), \
             patch("scraper_ai.config.load_dotenv"):
            s = Settings.from_env()
            assert s.scraper_api_key == "my-scraper-key"
            assert s.openai_api_key == "my-openai-key"
            assert s.anthropic_api_key == "my-anthropic-key"
            assert s.claude_model == "claude-sonnet-4-20250514"
            assert s.ollama_base_url == "http://myhost:11434"
            assert s.ollama_model == "llama3"
            assert s.groq_api_key == "my-groq-key"
            assert s.groq_model == "mixtral"
            assert s.gemini_api_key == "my-gemini-key"
            assert s.gemini_model == "gemini-pro"
            assert s.default_provider == "anthropic"
            assert s.processor_provider == "gemini"

    def test_from_env_requires_scraper_key(self):
        with (
            patch.dict("os.environ", {"SCRAPER_API_KEY": ""}, clear=False),
            patch("scraper_ai.config.load_dotenv"),
            patch("os.getenv", side_effect=lambda _k, d="": d),
            pytest.raises(ValueError, match="SCRAPER_API_KEY is required"),
        ):
            Settings.from_env()

    def test_scraper_timeout_default(self):
        s = Settings(scraper_api_key="test")
        assert s.scraper_timeout == 60

    def test_extraction_retries_default(self):
        s = Settings(scraper_api_key="test")
        assert s.extraction_retries == 2

    def test_fallback_provider_default(self):
        s = Settings(scraper_api_key="test")
        assert s.fallback_provider == ""

    def test_fetch_delay_default(self):
        s = Settings(scraper_api_key="test")
        assert s.fetch_delay == 1.0

    def test_cache_defaults(self):
        s = Settings(scraper_api_key="test")
        assert s.cache_enabled is False
        assert s.cache_dir == ".scraper_cache"

    def test_from_env_reads_retry_and_cache_settings(self):
        env = {
            "SCRAPER_API_KEY": "test-key",
            "EXTRACTION_RETRIES": "3",
            "FALLBACK_PROVIDER": "openai",
            "FETCH_DELAY": "2.5",
            "SCRAPER_CACHE_DIR": "/tmp/my_cache",
        }
        with patch.dict("os.environ", env, clear=False), \
             patch("scraper_ai.config.load_dotenv"):
            s = Settings.from_env()
            assert s.extraction_retries == 3
            assert s.fallback_provider == "openai"
            assert s.fetch_delay == 2.5
            assert s.cache_dir == "/tmp/my_cache"
