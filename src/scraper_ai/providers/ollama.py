"""Ollama provider for local SLM inference (e.g., qwen2.5:14b)."""

from __future__ import annotations

import logging

import httpx

from scraper_ai.config import Settings
from scraper_ai.models import PageResult
from scraper_ai.providers.base import AIProvider, ExtractionError

logger = logging.getLogger(__name__)


class OllamaProvider(AIProvider):
    name = "ollama"

    def __init__(self, settings: Settings) -> None:
        super().__init__(settings)
        self._base_url = settings.ollama_base_url.rstrip("/")
        self._model = settings.ollama_model

    def _chat(self, system: str, user: str, *, json_format: bool = False, num_ctx: int = 4096) -> str:
        """Send a chat request to Ollama and return the response text."""
        payload: dict = {
            "model": self._model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "stream": False,
            "options": {
                "temperature": self.settings.temperature,
                "num_ctx": num_ctx,
                "num_thread": 8,
            },
        }
        if json_format:
            payload["format"] = "json"

        with httpx.Client(timeout=600) as client:
            response = client.post(f"{self._base_url}/api/chat", json=payload)
            response.raise_for_status()

        return response.json().get("message", {}).get("content", "")

    def understand_page(self, html: str, page_url: str) -> str:
        """Phase 2: SLM reads HTML and produces clean markdown."""
        system, user = self._build_phase2_messages(html, page_url)
        try:
            return self._chat(system, user, json_format=False, num_ctx=16384)
        except Exception as exc:
            logger.error("Ollama understand_page failed: %s", exc)
            raise ExtractionError(f"Ollama understand_page failed: {exc}") from exc

    def analyze_page(
        self,
        html: str,
        user_prompt: str,
        page_url: str,
    ) -> PageResult:
        """Phase 3: Extract structured JSON data."""
        system, user = self._build_messages(html, user_prompt, page_url)
        try:
            raw = self._chat(system, user, json_format=True)
            return self._parse_response(raw)
        except ExtractionError:
            raise
        except Exception as exc:
            logger.error("Ollama request failed: %s", exc)
            raise ExtractionError(f"Ollama request failed: {exc}") from exc
