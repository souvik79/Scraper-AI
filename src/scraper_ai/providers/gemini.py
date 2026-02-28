"""Google Gemini provider — generous free tier, large context window."""

from __future__ import annotations

import logging
import time

from google import genai
from google.genai import types

from scraper_ai.config import Settings
from scraper_ai.models import PageResult
from scraper_ai.providers.base import AIProvider, ExtractionError

logger = logging.getLogger(__name__)

# Gemini free tier: 10 RPM, 250K TPM, 250 RPD.
# 1M token context — no chunking needed for HTML pages.
GEMINI_MAX_CHUNK_CHARS = 500_000

# Seconds between API calls to stay within 10 RPM.
GEMINI_RATE_LIMIT_DELAY = 7


class GeminiProvider(AIProvider):
    name = "gemini"
    max_chunk_chars = GEMINI_MAX_CHUNK_CHARS

    def __init__(self, settings: Settings) -> None:
        super().__init__(settings)
        if not settings.gemini_api_key:
            raise ValueError("GEMINI_API_KEY is required for the Gemini provider")
        self._client = genai.Client(api_key=settings.gemini_api_key)
        self._model = settings.gemini_model
        self._last_call: float = 0

    def _rate_limit(self) -> None:
        """Wait if needed to respect Gemini's RPM limit."""
        elapsed = time.time() - self._last_call
        if self._last_call and elapsed < GEMINI_RATE_LIMIT_DELAY:
            wait = GEMINI_RATE_LIMIT_DELAY - elapsed
            logger.info("Gemini rate limit: waiting %.1fs", wait)
            time.sleep(wait)

    def _chat(self, system: str, user: str, *, json_mode: bool = False) -> str:
        """Send a request to Gemini and return the response text."""
        self._rate_limit()

        config = types.GenerateContentConfig(
            system_instruction=system,
            temperature=self.settings.temperature,
        )
        if json_mode:
            config.response_mime_type = "application/json"

        response = self._client.models.generate_content(
            model=self._model,
            config=config,
            contents=user,
        )
        self._last_call = time.time()
        return response.text or ""

    def understand_page(self, html: str, page_url: str) -> str:
        """Phase 2: Read HTML and produce clean markdown."""
        system, user = self._build_phase2_messages(html, page_url)
        try:
            return self._chat(system, user, json_mode=False)
        except Exception as exc:
            logger.error("Gemini understand_page failed: %s", exc)
            raise ExtractionError(f"Gemini understand_page failed: {exc}") from exc

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
            logger.error("Gemini request failed: %s", exc)
            raise ExtractionError(f"Gemini request failed: {exc}") from exc
