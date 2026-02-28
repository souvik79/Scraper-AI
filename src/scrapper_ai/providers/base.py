"""Abstract base class for all AI providers."""

from __future__ import annotations

import json
import logging
from abc import ABC, abstractmethod

from scrapper_ai.config import Settings
from scrapper_ai.models import PageResult

logger = logging.getLogger(__name__)

# Phase 2: SLM reads raw HTML and produces clean markdown
PHASE2_SYSTEM_PROMPT = """\
You are a web page analyzer. Read the HTML below and produce a clean, \
structured markdown representation of the page content.

Include:
- All visible text content, preserving the page hierarchy
- All links as [text](url) markdown — use absolute URLs
- ALL image URLs from ANY source: <img> src/data-src/srcset, \
style="background-image: url(...)", data attributes, picture/source tags. \
Format each as ![image](url)
- Do NOT include navigation menus, footers, cookie banners, or boilerplate

Current page URL (for resolving relative URLs): {page_url}

Output clean markdown text. No JSON. No code fences."""

# Phase 3: LLM extracts structured data from markdown
EXTRACT_SYSTEM_PROMPT = """\
You are an intelligent web scraping assistant. The user will give you a detailed \
prompt describing what to scrape and how to navigate the site. Follow their \
instructions carefully.

For each page you analyze, return:

1. "data": Extract items matching the user's request. Each item is a JSON object.

2. "next_urls": Pagination links ONLY (next page, page 2, etc.). These are \
processed immediately. All URLs must be absolute.

3. "detail_urls": URLs to individual item/detail pages that need deeper scraping. \
These are processed AFTER all pagination is done. All URLs must be absolute.

4. "summary": Brief description of what was found.

Rules:
- Only extract data actually present on the page. Do not invent data.
- Convert relative URLs to absolute using the current page URL.
- Do not include the current page URL in next_urls or detail_urls.
- Pagination links go in "next_urls". Detail/item page links go in "detail_urls".

Current page URL: {page_url}

Return ONLY valid JSON: \
{{"data": [...], "next_urls": [...], "detail_urls": [...], "summary": "..."}}"""


class ExtractionError(Exception):
    """Raised when AI extraction fails."""


class AIProvider(ABC):
    """Contract for AI-powered page analysis providers."""

    name: str
    max_chunk_chars: int = 48_000  # ~12K tokens; providers can override

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    @abstractmethod
    def analyze_page(
        self,
        html: str,
        user_prompt: str,
        page_url: str,
    ) -> PageResult:
        """
        Phase 3: Extract structured data from page content.

        Args:
            html: Page content (clean markdown from Phase 2, or HTML in single-model mode).
            user_prompt: The user's natural language request.
            page_url: The URL of the current page (for resolving relative links).

        Returns:
            PageResult with extracted data and URLs to visit next.
        """
        ...

    @abstractmethod
    def understand_page(self, html: str, page_url: str) -> str:
        """
        Phase 2: Read HTML and produce a clean markdown representation.

        Args:
            html: Minimally cleaned HTML content.
            page_url: The URL of the current page (for resolving relative URLs).

        Returns:
            Clean markdown text with all content, links, and image URLs preserved.
        """
        ...

    def _build_messages(
        self, html: str, user_prompt: str, page_url: str
    ) -> tuple[str, str]:
        """Build system and user messages for Phase 3 extraction."""
        system = EXTRACT_SYSTEM_PROMPT.format(page_url=page_url)
        user = f"{user_prompt}\n\n---PAGE CONTENT---\n{html}\n---END PAGE CONTENT---"
        return system, user

    def _build_phase2_messages(self, html: str, page_url: str) -> tuple[str, str]:
        """Build system and user messages for Phase 2 understanding."""
        system = PHASE2_SYSTEM_PROMPT.format(page_url=page_url)
        user = f"---HTML---\n{html}\n---END HTML---"
        return system, user

    def _parse_response(self, raw_json: str) -> PageResult:
        """Parse AI response JSON into PageResult."""
        text = raw_json.strip()

        # Strip markdown code fences if present (```json ... ```)
        if text.startswith("```"):
            first_nl = text.find("\n")
            if first_nl != -1:
                text = text[first_nl + 1:]
            if text.rstrip().endswith("```"):
                text = text.rstrip()[:-3].rstrip()

        # Try direct parse first
        try:
            parsed = json.loads(text)
            return PageResult.model_validate(parsed)
        except (json.JSONDecodeError, ValueError):
            pass

        # AI sometimes returns two concatenated JSON objects:
        # {"data":[], ...} {"year":2020, ...}
        # Use raw_decode to parse the first object, then check for trailing data.
        decoder = json.JSONDecoder()
        try:
            first_obj, end_idx = decoder.raw_decode(text)
            remainder = text[end_idx:].strip()

            if remainder:
                try:
                    second_obj = json.loads(remainder)
                    # If first is a PageResult with empty data, put second into data
                    if isinstance(first_obj, dict) and isinstance(second_obj, dict):
                        if not first_obj.get("data"):
                            first_obj["data"] = [second_obj]
                        else:
                            first_obj["data"].append(second_obj)
                except json.JSONDecodeError:
                    pass

            return PageResult.model_validate(first_obj)
        except (json.JSONDecodeError, ValueError):
            pass

        raise ExtractionError(f"Failed to parse AI response: {text[:200]}")
