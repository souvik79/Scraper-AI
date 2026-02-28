"""Pydantic models for the scraping pipeline."""

from __future__ import annotations

from pydantic import BaseModel, Field


class PageResult(BaseModel):
    """What the AI returns for each page it analyzes."""

    data: list[dict] = Field(
        default_factory=list,
        description="Extracted data matching the user's request",
    )
    next_urls: list[str] = Field(
        default_factory=list,
        description="Pagination URLs to visit next (same level)",
    )
    detail_urls: list[str] = Field(
        default_factory=list,
        description="Detail/item page URLs for deeper scraping (next level)",
    )
    summary: str = Field(
        default="",
        description="Brief description of what was found on this page",
    )


class CrawlResult(BaseModel):
    """Final aggregated output from a crawl session."""

    url: str = Field(description="Starting URL")
    prompt: str = Field(description="User's natural language prompt")
    provider: str = Field(description="AI provider used")
    pages_crawled: int = Field(default=0)
    data: list[dict] = Field(
        default_factory=list,
        description="All extracted data aggregated across pages",
    )
