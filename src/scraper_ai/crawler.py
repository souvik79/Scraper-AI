"""Agentic crawl loop — multi-level BFS with AI-driven link discovery.

3-Phase Pipeline:
  Phase 1 — Fetch:       ScraperAPI gets raw HTML
  Phase 2 — Understand:  SLM reads HTML → clean markdown (optional, dual-model mode)
  Phase 3 — Extract:     LLM reads content + user prompt → structured JSON
"""

from __future__ import annotations

import logging
import sys
import time
from urllib.parse import urlparse

from scraper_ai.cleaner import chunk_text, clean_html
from scraper_ai.config import Settings
from scraper_ai.fetcher import FetchError, fetch_html
from scraper_ai.models import CrawlResult
from scraper_ai.providers import get_provider
from scraper_ai.providers.base import AIProvider, ExtractionError

logger = logging.getLogger(__name__)

LINE = "=" * 60
THIN = "-" * 55


def _out(msg: str = "") -> None:
    """Print a status message to stderr so it doesn't mix with JSON output."""
    print(msg, file=sys.stderr, flush=True)


def _same_domain(url: str, base_url: str) -> bool:
    """Check if a URL belongs to the same domain as the base URL."""
    try:
        return urlparse(url).netloc == urlparse(base_url).netloc
    except Exception:
        return False


def _elapsed(t: float) -> str:
    """Format elapsed seconds as human-readable string."""
    secs = time.time() - t
    if secs < 60:
        return f"{secs:.1f}s"
    return f"{secs / 60:.1f}m"


def _fetch_and_analyze(
    url: str,
    extractor: AIProvider,
    extractor_name: str,
    processor: AIProvider | None,
    processor_name: str | None,
    user_prompt: str,
    settings: Settings,
    start_url: str,
    visited: set[str],
):
    """3-phase pipeline for a single URL. Returns (data, pagination_urls, detail_urls)."""
    page_data = []
    pagination_urls = []
    detail_urls = []
    dual_mode = processor is not None

    total_steps = 4 if dual_mode else 3

    # Phase 1: Fetch
    _out(f"  Phase 1/{total_steps}  Fetching via ScraperAPI...")
    t0 = time.time()
    try:
        raw_html = fetch_html(url, settings)
    except FetchError as exc:
        _out(f"  [!] Failed to fetch: {exc}")
        logger.warning("Failed to fetch %s: %s", url, exc)
        return page_data, pagination_urls, detail_urls
    _out(f"             done ({_elapsed(t0)})")

    # Minimal cleanup (regex — strip script/style bodies, comments, whitespace)
    step = 2
    _out(f"  Phase {step}/{total_steps}  Cleaning HTML...")
    t0 = time.time()
    cleaned = clean_html(raw_html)
    reduction = (1 - len(cleaned) / max(len(raw_html), 1)) * 100
    _out(f"             {len(raw_html):,} -> {len(cleaned):,} bytes ({reduction:.0f}% reduction) ({_elapsed(t0)})")
    logger.info("Cleaned: %d -> %d bytes (%.0f%% reduction)", len(raw_html), len(cleaned), reduction)

    # Phase 2: SLM understands the page (dual-model mode only)
    if dual_mode:
        step = 3
        _out(f"  Phase {step}/{total_steps}  Understanding with {processor_name} (SLM)...")
        t0 = time.time()
        try:
            chunks = chunk_text(cleaned, max_chars=processor.max_chunk_chars)
            markdown_parts = []
            for i, chunk in enumerate(chunks):
                logger.info("Phase 2 chunk %d/%d (%d chars)", i + 1, len(chunks), len(chunk))
                md = processor.understand_page(chunk, url)
                markdown_parts.append(md)
            content = "\n\n".join(markdown_parts)
            _out(f"             done — {len(content):,} chars markdown ({_elapsed(t0)})")
            logger.info("Phase 2 produced %d chars markdown", len(content))
        except ExtractionError as exc:
            _out(f"             failed ({_elapsed(t0)})")
            _out(f"  [!] Phase 2 failed: {exc}, falling back to cleaned HTML")
            logger.warning("Phase 2 failed: %s, using cleaned HTML", exc)
            content = cleaned
    else:
        content = cleaned

    # Phase 3: LLM extracts structured data
    step = total_steps
    chunks = chunk_text(content, max_chars=extractor.max_chunk_chars)
    if len(chunks) > 1:
        _out(f"  Phase {step}/{total_steps}  Extracting with {extractor_name} ({len(chunks)} chunks)...")
    else:
        _out(f"  Phase {step}/{total_steps}  Extracting with {extractor_name}...")

    for i, chunk in enumerate(chunks):
        t0 = time.time()
        logger.info("Phase 3 chunk %d/%d (%d chars)", i + 1, len(chunks), len(chunk))
        try:
            result = extractor.analyze_page(chunk, user_prompt, url)
            page_data.extend(result.data)

            new_pagination = [
                u for u in result.next_urls
                if u not in visited and _same_domain(u, start_url)
            ]
            pagination_urls.extend(new_pagination)

            new_details = [
                u for u in result.detail_urls
                if u not in visited and _same_domain(u, start_url)
            ]
            detail_urls.extend(new_details)

            _out(f"             done ({_elapsed(t0)})")
            _out(f"  {THIN}")
            _out(f"  Results:  {len(result.data)} items extracted")
            if new_pagination:
                _out(f"  Next:     {len(new_pagination)} pagination links")
            if new_details:
                _out(f"  Details:  {len(new_details)} detail URLs to visit later")
            if result.summary:
                _out(f"  Summary:  {result.summary}")
            _out(f"  {THIN}")

            logger.info(
                "Found %d items, %d pagination, %d detail URLs. Summary: %s",
                len(result.data), len(new_pagination), len(new_details), result.summary,
            )
        except ExtractionError as exc:
            _out(f"             failed ({_elapsed(t0)})")
            _out(f"  [!] Extraction failed: {exc}")
            logger.warning("Extraction failed for chunk %d: %s", i + 1, exc)

    return page_data, pagination_urls, detail_urls


def crawl(
    start_url: str,
    user_prompt: str,
    provider_name: str | None = None,
    processor_name: str | None = None,
    settings: Settings | None = None,
) -> CrawlResult:
    """
    Multi-level crawl: BFS pagination at each level, then go deeper via detail URLs.
    The AI decides what goes where based on the user's prompt.

    Args:
        provider_name: Phase 3 extractor (LLM). Defaults to settings.default_provider.
        processor_name: Phase 2 understander (SLM). None = single-model mode.
    """
    if settings is None:
        settings = Settings.from_env()

    provider_name = provider_name or settings.default_provider
    extractor = get_provider(provider_name, settings)

    processor_name = processor_name or settings.processor_provider or None
    processor = get_provider(processor_name, settings) if processor_name else None

    visited: set[str] = set()
    all_data: list[dict] = []
    total_pages = 0
    crawl_start = time.time()

    # Header
    _out(f"\n{LINE}")
    _out("  ScraperAI - Agentic Web Scraper")
    _out(LINE)
    _out(f"  URL:      {start_url}")
    prompt_display = user_prompt[:50] + "..." if len(user_prompt) > 50 else user_prompt
    _out(f"  Prompt:   {prompt_display}")
    if processor_name:
        _out(f"  Phase 2:  {processor_name} (SLM)")
        _out(f"  Phase 3:  {provider_name} (LLM)")
    else:
        _out(f"  Provider: {provider_name}")
    _out(LINE)

    level = 1
    current_queue = [start_url]

    while current_queue:
        _out()
        _out(f"--- Level {level}: {'Listing Pages' if level == 1 else 'Detail Pages'} ({len(current_queue)} URLs) ---")
        _out()

        next_level_urls: list[str] = []
        level_data: list[dict] = []
        page_in_level = 0

        while current_queue and total_pages < settings.max_pages:
            url = current_queue.pop(0)

            if url in visited:
                continue
            if visited and not _same_domain(url, start_url):
                logger.debug("Skipping off-domain URL: %s", url)
                continue

            visited.add(url)
            total_pages += 1
            page_in_level += 1

            _out(f"[{page_in_level}] {url}")

            # Tell the AI which step it's on so it follows the right instructions
            effective_prompt = user_prompt
            if level > 1:
                effective_prompt = (
                    f"[CONTEXT: You are now viewing a DETAIL PAGE at {url}. "
                    f"Follow the Step 2 / detail page instructions from the prompt below. "
                    f"Extract all detailed data for this single item into the data array.]\n\n"
                    f"{user_prompt}"
                )

            page_data, pagination_urls, detail_urls = _fetch_and_analyze(
                url, extractor, provider_name, processor, processor_name,
                effective_prompt, settings, start_url, visited,
            )

            if level > 1 and page_data:
                # Merge detail data into parent item matched by URL
                for detail_item in page_data:
                    merged = False
                    for parent in all_data:
                        if parent.get("detail_url") == url:
                            new_fields = [k for k in detail_item if k not in parent]
                            parent.update(detail_item)
                            merged = True
                            if new_fields:
                                _out(f"  Merged:   +{len(new_fields)} fields ({', '.join(new_fields[:5])}{'...' if len(new_fields) > 5 else ''})")
                            break
                    if not merged:
                        all_data.append(detail_item)
                level_data.extend(page_data)
            else:
                level_data.extend(page_data)

            current_queue.extend(pagination_urls)
            next_level_urls.extend(detail_urls)

            _out(
                f"  Progress: {len(level_data)} items this level | "
                f"{total_pages} total pages | "
                f"{len(current_queue)} queued"
            )
            _out()

        # Dedup items by detail_url (same item from multiple pagination pages)
        if level == 1 and level_data:
            seen_detail_urls: set[str] = set()
            deduped: list[dict] = []
            for item in level_data:
                du = item.get("detail_url", "")
                if du and du in seen_detail_urls:
                    continue
                if du:
                    seen_detail_urls.add(du)
                deduped.append(item)

            if len(deduped) < len(level_data):
                _out(f"  Deduped: {len(level_data)} -> {len(deduped)} unique items")

            level_data = deduped
            all_data.extend(level_data)

        _out(f"  Level {level} complete: {len(level_data)} items")

        # Dedup next level URLs and remove visited
        next_level_urls = list(dict.fromkeys(next_level_urls))
        next_level_urls = [u for u in next_level_urls if u not in visited]

        if not next_level_urls:
            break

        level += 1
        current_queue = next_level_urls

    # Summary
    total_time = _elapsed(crawl_start)
    _out()
    _out(LINE)
    _out("  CRAWL COMPLETE")
    _out(LINE)
    _out(f"  Levels:           {level}")
    _out(f"  Pages crawled:    {total_pages}")
    _out(f"  Items extracted:  {len(all_data)}")
    _out(f"  Total time:       {total_time}")
    _out(LINE)
    _out()

    logger.info(
        "Crawl complete. Levels: %d, Pages: %d, Items: %d",
        level, total_pages, len(all_data),
    )

    return CrawlResult(
        url=start_url,
        prompt=user_prompt,
        provider=provider_name,
        pages_crawled=total_pages,
        data=all_data,
    )
