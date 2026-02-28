"""Groq provider — free, fast inference via OpenAI-compatible API."""

from __future__ import annotations

import logging
import time

from openai import OpenAI

from scraper_ai.config import Settings
from scraper_ai.models import PageResult
from scraper_ai.providers.base import AIProvider, ExtractionError

logger = logging.getLogger(__name__)

GROQ_BASE_URL = "https://api.groq.com/openai/v1"

# Groq free tier: 6K TPM. Keep chunks small so each request fits.
# ~3 chars/token for HTML → 12K chars ≈ 4K tokens + system prompt ≈ 5K total.
GROQ_MAX_CHUNK_CHARS = 12_000

# Seconds to wait between API calls to respect TPM limits.
GROQ_RATE_LIMIT_DELAY = 15


class GroqProvider(AIProvider):
    name = "groq"
    max_chunk_chars = GROQ_MAX_CHUNK_CHARS

    def __init__(self, settings: Settings) -> None:
        super().__init__(settings)
        if not settings.groq_api_key:
            raise ValueError("GROQ_API_KEY is required for the Groq provider")
        self._client = OpenAI(
            api_key=settings.groq_api_key,
            base_url=GROQ_BASE_URL,
        )
        self._model = settings.groq_model
        self._last_call: float = 0

    def _rate_limit(self) -> None:
        """Wait if needed to respect Groq's TPM limit."""
        elapsed = time.time() - self._last_call
        if self._last_call and elapsed < GROQ_RATE_LIMIT_DELAY:
            wait = GROQ_RATE_LIMIT_DELAY - elapsed
            logger.info("Groq rate limit: waiting %.1fs", wait)
            time.sleep(wait)

    def _chat(self, system: str, user: str, *, json_mode: bool = False) -> str:
        """Send a chat request to Groq and return the response text."""
        self._rate_limit()

        kwargs: dict = {
            "model": self._model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "temperature": self.settings.temperature,
        }
        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}

        response = self._client.chat.completions.create(**kwargs)
        self._last_call = time.time()
        return response.choices[0].message.content or ""

    def understand_page(self, html: str, page_url: str) -> str:
        """Phase 2: Read HTML and produce clean markdown."""
        system, user = self._build_phase2_messages(html, page_url)
        try:
            return self._chat(system, user, json_mode=False)
        except Exception as exc:
            logger.error("Groq understand_page failed: %s", exc)
            raise ExtractionError(f"Groq understand_page failed: {exc}") from exc

    def analyze_page(
        self,
        html: str,
        user_prompt: str,
        page_url: str,
    ) -> PageResult:
        """Phase 3: Extract structured JSON data."""
        system, user = self._build_messages(html, user_prompt, page_url)
        try:
            raw = self._chat(system, user, json_mode=True)
            return self._parse_response(raw)
        except ExtractionError:
            raise
        except Exception as exc:
            logger.error("Groq request failed: %s", exc)
            raise ExtractionError(f"Groq request failed: {exc}") from exc
