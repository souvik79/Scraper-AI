"""Anthropic Claude provider."""

from __future__ import annotations

import logging

import anthropic

from scrapper_ai.config import Settings
from scrapper_ai.models import PageResult
from scrapper_ai.providers.base import AIProvider, ExtractionError

logger = logging.getLogger(__name__)


class AnthropicProvider(AIProvider):
    name = "anthropic"

    def __init__(self, settings: Settings) -> None:
        super().__init__(settings)
        if not settings.anthropic_api_key:
            raise ValueError("ANTHROPIC_API_KEY is required for the Anthropic provider")
        self._client = anthropic.Anthropic(api_key=settings.anthropic_api_key)

    def _chat(self, system: str, user: str) -> str:
        """Send a chat request to Anthropic and return the response text."""
        response = self._client.messages.create(
            model=self.settings.claude_model,
            max_tokens=4096,
            system=system,
            messages=[{"role": "user", "content": user}],
            temperature=self.settings.temperature,
        )
        return response.content[0].text

    def understand_page(self, html: str, page_url: str) -> str:
        """Phase 2: Read HTML and produce clean markdown."""
        system, user = self._build_phase2_messages(html, page_url)
        try:
            return self._chat(system, user)
        except Exception as exc:
            logger.error("Anthropic understand_page failed: %s", exc)
            raise ExtractionError(f"Anthropic understand_page failed: {exc}") from exc

    def analyze_page(
        self,
        html: str,
        user_prompt: str,
        page_url: str,
    ) -> PageResult:
        """Phase 3: Extract structured JSON data."""
        system, user = self._build_messages(html, user_prompt, page_url)
        try:
            raw = self._chat(system, user)
            return self._parse_response(raw)
        except ExtractionError:
            raise
        except Exception as exc:
            logger.error("Anthropic request failed: %s", exc)
            raise ExtractionError(f"Anthropic request failed: {exc}") from exc
