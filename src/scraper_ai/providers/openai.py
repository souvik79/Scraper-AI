"""OpenAI provider using GPT-4o."""

from __future__ import annotations

import logging

from openai import OpenAI

from scraper_ai.config import Settings
from scraper_ai.models import PageResult
from scraper_ai.providers.base import AIProvider, ExtractionError

logger = logging.getLogger(__name__)


class OpenAIProvider(AIProvider):
    name = "openai"

    def __init__(self, settings: Settings) -> None:
        super().__init__(settings)
        if not settings.openai_api_key:
            raise ValueError("OPENAI_API_KEY is required for the OpenAI provider")
        self._client = OpenAI(api_key=settings.openai_api_key)

    def _chat(self, system: str, user: str, *, json_mode: bool = False) -> str:
        """Send a chat request to OpenAI and return the response text."""
        kwargs: dict = {
            "model": "gpt-4o",
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "temperature": self.settings.temperature,
        }
        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}

        response = self._client.chat.completions.create(**kwargs)
        return response.choices[0].message.content or ""

    def understand_page(self, html: str, page_url: str) -> str:
        """Phase 2: Read HTML and produce clean markdown."""
        system, user = self._build_phase2_messages(html, page_url)
        try:
            return self._chat(system, user, json_mode=False)
        except Exception as exc:
            logger.error("OpenAI understand_page failed: %s", exc)
            raise ExtractionError(f"OpenAI understand_page failed: {exc}") from exc

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
            logger.error("OpenAI request failed: %s", exc)
            raise ExtractionError(f"OpenAI request failed: {exc}") from exc
