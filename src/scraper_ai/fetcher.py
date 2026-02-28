"""Fetch HTML from URLs via ScraperAPI with retry logic and scroll support."""

from __future__ import annotations

import json
import logging

import httpx
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from scraper_ai.config import Settings

logger = logging.getLogger(__name__)

SCRAPERAPI_ENDPOINT = "https://api.scraperapi.com/"


class FetchError(Exception):
    """Raised when HTML fetching fails after all retries."""


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=2, min=4, max=30),
    retry=retry_if_exception_type((httpx.TimeoutException, httpx.HTTPStatusError)),
    reraise=True,
)
def fetch_html(url: str, settings: Settings) -> str:
    """
    Fetch the fully-rendered HTML for a URL via ScraperAPI.

    Supports optional auto-scroll for infinite scroll pages using
    ScraperAPI's Render Instruction Set.
    """
    headers: dict[str, str] = {
        "x-sapi-api_key": settings.scraper_api_key,
        "x-sapi-render": str(settings.render_js).lower(),
    }

    if settings.auto_scroll:
        instruction_set = [
            {
                "type": "loop",
                "for": 3,
                "instructions": [
                    {"type": "scroll", "direction": "y", "value": "bottom"},
                    {"type": "wait_for_event", "event": "networkidle", "timeout": 10},
                ],
            }
        ]
        headers["x-sapi-instruction_set"] = json.dumps(instruction_set)

    try:
        with httpx.Client(timeout=settings.scraper_timeout) as client:
            response = client.get(
                SCRAPERAPI_ENDPOINT,
                params={"url": url},
                headers=headers,
            )
            response.raise_for_status()
            logger.info("Fetched %d bytes from %s", len(response.text), url)
            return response.text
    except Exception as exc:
        logger.error("Fetch failed for %s: %s", url, exc)
        raise FetchError(f"Failed to fetch {url}: {exc}") from exc
