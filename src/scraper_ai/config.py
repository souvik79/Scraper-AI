"""Centralized configuration loaded from .env."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


def _load_env() -> None:
    env_path = Path.cwd() / ".env"
    if env_path.exists():
        load_dotenv(dotenv_path=env_path)
    else:
        load_dotenv()


@dataclass(frozen=True)
class Settings:
    scraper_api_key: str = ""

    # AI provider keys
    openai_api_key: str = ""
    anthropic_api_key: str = ""
    claude_model: str = "claude-haiku-4-5-20251001"

    # Ollama config
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "phi4-mini"

    # Groq config (OpenAI-compatible, free tier)
    groq_api_key: str = ""
    groq_model: str = "llama-3.1-8b-instant"

    # Gemini config (generous free tier, large context)
    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.5-flash"

    # ScraperAPI tuning
    scraper_timeout: int = 60
    render_js: bool = True
    auto_scroll: bool = False

    # Crawl settings
    default_provider: str = "ollama"
    processor_provider: str = ""  # Phase 2 SLM provider; empty = single-model mode
    max_pages: int = 100
    temperature: float = 0.0

    @classmethod
    def from_env(cls) -> Settings:
        _load_env()
        scraper_key = os.getenv("SCRAPER_API_KEY", "")
        if not scraper_key:
            raise ValueError(
                "SCRAPER_API_KEY is required. Set it in your .env file."
            )
        return cls(
            scraper_api_key=scraper_key,
            openai_api_key=os.getenv("OPENAI_API_KEY", ""),
            anthropic_api_key=os.getenv("ANTHROPIC_API_KEY", ""),
            claude_model=os.getenv("CLAUDE_MODEL", "claude-haiku-4-5-20251001"),
            ollama_base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
            ollama_model=os.getenv("OLLAMA_MODEL", "phi4-mini"),
            groq_api_key=os.getenv("GROQ_API_KEY", ""),
            groq_model=os.getenv("GROQ_MODEL", "llama-3.1-8b-instant"),
            gemini_api_key=os.getenv("GEMINI_API_KEY", ""),
            gemini_model=os.getenv("GEMINI_MODEL", "gemini-2.5-flash"),
            default_provider=os.getenv("DEFAULT_PROVIDER", "ollama"),
            processor_provider=os.getenv("PROCESSOR_PROVIDER", ""),
        )
