"""Tests for scraper_ai.crawler module."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from scraper_ai.config import Settings
from scraper_ai.crawler import _elapsed, _extract_chunk, _same_domain, crawl
from scraper_ai.models import CrawlResult, PageResult
from scraper_ai.providers.base import ExtractionError


class TestSameDomain:
    def test_same_domain(self):
        assert _same_domain("https://example.com/page2", "https://example.com/page1")

    def test_different_domain(self):
        assert not _same_domain("https://other.com/page", "https://example.com/page")

    def test_subdomain_different(self):
        assert not _same_domain("https://sub.example.com/page", "https://example.com/page")

    def test_invalid_url(self):
        assert not _same_domain("not-a-url", "https://example.com")

    def test_same_domain_with_paths(self):
        assert _same_domain(
            "https://example.com/a/b/c", "https://example.com/x/y/z"
        )

    def test_different_schemes(self):
        assert _same_domain("http://example.com/page", "https://example.com/page")


class TestElapsed:
    def test_seconds_format(self):
        import time
        t = time.time() - 5  # 5 seconds ago
        result = _elapsed(t)
        assert result.endswith("s")
        assert "m" not in result

    def test_minutes_format(self):
        import time
        t = time.time() - 120  # 2 minutes ago
        result = _elapsed(t)
        assert result.endswith("m")


class TestCrawl:
    @pytest.fixture()
    def mock_settings(self):
        return Settings(
            scraper_api_key="test-key",
            default_provider="ollama",
            max_pages=5,
        )

    @pytest.fixture()
    def mock_provider(self):
        provider = MagicMock()
        provider.name = "ollama"
        provider.max_chunk_chars = 48_000
        provider.analyze_page.return_value = PageResult(
            data=[{"name": "Item 1"}],
            next_urls=[],
            detail_urls=[],
            summary="Found 1 item",
        )
        return provider

    def test_single_page_crawl(self, mock_settings, mock_provider):
        with patch("scraper_ai.crawler.get_provider", return_value=mock_provider), \
             patch("scraper_ai.crawler.fetch_html", return_value="<html>Test</html>"):
            result = crawl(
                start_url="https://example.com",
                user_prompt="Extract products",
                settings=mock_settings,
            )

        assert isinstance(result, CrawlResult)
        assert result.url == "https://example.com"
        assert result.pages_crawled == 1
        assert len(result.data) == 1
        assert result.data[0]["name"] == "Item 1"

    def test_crawl_with_pagination(self, mock_settings, mock_provider):
        call_count = 0

        def side_effect(html, prompt, url):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return PageResult(
                    data=[{"name": "Item 1"}],
                    next_urls=["https://example.com/page/2"],
                    detail_urls=[],
                    summary="Page 1",
                )
            return PageResult(
                data=[{"name": "Item 2"}],
                next_urls=[],
                detail_urls=[],
                summary="Page 2",
            )

        mock_provider.analyze_page.side_effect = side_effect

        with patch("scraper_ai.crawler.get_provider", return_value=mock_provider), \
             patch("scraper_ai.crawler.fetch_html", return_value="<html>Test</html>"):
            result = crawl(
                start_url="https://example.com",
                user_prompt="Extract products",
                settings=mock_settings,
            )

        assert result.pages_crawled == 2
        assert len(result.data) == 2

    def test_crawl_respects_max_pages(self, mock_settings, mock_provider):
        """Crawl should stop after max_pages."""
        from dataclasses import replace
        settings = replace(mock_settings, max_pages=2)

        mock_provider.analyze_page.return_value = PageResult(
            data=[{"name": "Item"}],
            next_urls=["https://example.com/page/next"],
            detail_urls=[],
            summary="More pages",
        )

        with patch("scraper_ai.crawler.get_provider", return_value=mock_provider), \
             patch("scraper_ai.crawler.fetch_html", return_value="<html>Test</html>"):
            result = crawl(
                start_url="https://example.com",
                user_prompt="Extract products",
                settings=settings,
            )

        assert result.pages_crawled <= 2

    def test_crawl_skips_off_domain_urls(self, mock_settings, mock_provider):
        mock_provider.analyze_page.return_value = PageResult(
            data=[{"name": "Item"}],
            next_urls=["https://other-domain.com/page"],
            detail_urls=[],
            summary="Has off-domain link",
        )

        with patch("scraper_ai.crawler.get_provider", return_value=mock_provider), \
             patch("scraper_ai.crawler.fetch_html", return_value="<html>Test</html>"):
            result = crawl(
                start_url="https://example.com",
                user_prompt="Extract products",
                settings=mock_settings,
            )

        # Should only crawl the start URL, not follow off-domain links
        assert result.pages_crawled == 1

    def test_crawl_skips_visited_urls(self, mock_settings, mock_provider):
        mock_provider.analyze_page.return_value = PageResult(
            data=[{"name": "Item"}],
            next_urls=["https://example.com"],  # Same as start URL
            detail_urls=[],
            summary="Self-referencing",
        )

        with patch("scraper_ai.crawler.get_provider", return_value=mock_provider), \
             patch("scraper_ai.crawler.fetch_html", return_value="<html>Test</html>"):
            result = crawl(
                start_url="https://example.com",
                user_prompt="Extract products",
                settings=mock_settings,
            )

        assert result.pages_crawled == 1

    def test_crawl_with_detail_pages(self, mock_settings, mock_provider):
        call_count = 0

        def side_effect(html, prompt, url):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return PageResult(
                    data=[{"name": "Car", "detail_url": "https://example.com/car/1"}],
                    next_urls=[],
                    detail_urls=["https://example.com/car/1"],
                    summary="Found listing",
                )
            return PageResult(
                data=[{"name": "Car", "vin": "ABC123", "images": ["img1.jpg"]}],
                next_urls=[],
                detail_urls=[],
                summary="Detail page",
            )

        mock_provider.analyze_page.side_effect = side_effect

        with patch("scraper_ai.crawler.get_provider", return_value=mock_provider), \
             patch("scraper_ai.crawler.fetch_html", return_value="<html>Test</html>"):
            result = crawl(
                start_url="https://example.com",
                user_prompt="Extract cars",
                settings=mock_settings,
            )

        assert result.pages_crawled == 2
        # Detail data should be merged into the parent item
        assert any("vin" in item for item in result.data)

    def test_crawl_dual_model_mode(self, mock_settings):
        extractor = MagicMock()
        extractor.name = "anthropic"
        extractor.max_chunk_chars = 48_000
        extractor.analyze_page.return_value = PageResult(
            data=[{"name": "Item"}],
            next_urls=[],
            detail_urls=[],
            summary="Extracted",
        )

        processor = MagicMock()
        processor.name = "gemini"
        processor.max_chunk_chars = 500_000
        processor.understand_page.return_value = "# Clean Markdown\nContent here"

        def provider_factory(name, settings):
            if name == "anthropic":
                return extractor
            return processor

        with patch("scraper_ai.crawler.get_provider", side_effect=provider_factory), \
             patch("scraper_ai.crawler.fetch_html", return_value="<html>Test</html>"):
            result = crawl(
                start_url="https://example.com",
                user_prompt="Extract products",
                provider_name="anthropic",
                processor_name="gemini",
                settings=mock_settings,
            )

        # Processor should have been called for Phase 2
        processor.understand_page.assert_called_once()
        # Extractor should have been called for Phase 3
        extractor.analyze_page.assert_called_once()
        assert result.pages_crawled == 1

    def test_crawl_provider_defaults_to_settings(self, mock_settings, mock_provider):
        with patch("scraper_ai.crawler.get_provider", return_value=mock_provider) as mock_get, \
             patch("scraper_ai.crawler.fetch_html", return_value="<html></html>"):
            crawl(
                start_url="https://example.com",
                user_prompt="test",
                settings=mock_settings,
            )

        # Should use default_provider from settings
        mock_get.assert_called_with("ollama", mock_settings)

    def test_crawl_returns_crawl_result(self, mock_settings, mock_provider):
        with patch("scraper_ai.crawler.get_provider", return_value=mock_provider), \
             patch("scraper_ai.crawler.fetch_html", return_value="<html></html>"):
            result = crawl(
                start_url="https://example.com",
                user_prompt="test",
                settings=mock_settings,
            )

        assert result.provider == "ollama"
        assert result.prompt == "test"


class TestExtractChunk:
    @pytest.fixture()
    def default_settings(self):
        return Settings(scraper_api_key="test-key", extraction_retries=2)

    def test_succeeds_on_first_attempt(self, default_settings):
        extractor = MagicMock()
        expected = PageResult(data=[{"name": "Item"}], next_urls=[], detail_urls=[], summary="ok")
        extractor.analyze_page.return_value = expected

        result = _extract_chunk("html", 1, 1, extractor, None, "prompt", "https://example.com", default_settings)

        assert result == expected
        assert extractor.analyze_page.call_count == 1

    @patch("scraper_ai.crawler.time.sleep")
    def test_retry_succeeds_on_second_attempt(self, mock_sleep, default_settings):
        extractor = MagicMock()
        expected = PageResult(data=[{"name": "Item"}], next_urls=[], detail_urls=[], summary="ok")
        extractor.analyze_page.side_effect = [
            ExtractionError("bad JSON"),
            expected,
        ]

        result = _extract_chunk("html", 1, 1, extractor, None, "prompt", "https://example.com", default_settings)

        assert result == expected
        assert extractor.analyze_page.call_count == 2
        mock_sleep.assert_called_once_with(2)  # 2^1 = 2s backoff

    @patch("scraper_ai.crawler.time.sleep")
    def test_retry_exhausted_returns_none(self, _mock_sleep):
        settings = Settings(scraper_api_key="test-key", extraction_retries=1)
        extractor = MagicMock()
        extractor.analyze_page.side_effect = ExtractionError("always fails")

        result = _extract_chunk("html", 1, 1, extractor, None, "prompt", "https://example.com", settings)

        assert result is None
        assert extractor.analyze_page.call_count == 2  # 1 initial + 1 retry

    @patch("scraper_ai.crawler.time.sleep")
    def test_fallback_used_after_retries_fail(self, _mock_sleep):
        settings = Settings(scraper_api_key="test-key", extraction_retries=1)
        extractor = MagicMock()
        extractor.analyze_page.side_effect = ExtractionError("primary fails")

        fallback = MagicMock()
        expected = PageResult(data=[{"name": "Fallback Item"}], next_urls=[], detail_urls=[], summary="ok")
        fallback.analyze_page.return_value = expected

        result = _extract_chunk("html", 1, 1, extractor, fallback, "prompt", "https://example.com", settings)

        assert result == expected
        assert extractor.analyze_page.call_count == 2  # exhausted retries
        assert fallback.analyze_page.call_count == 1

    def test_no_fallback_when_primary_succeeds(self, default_settings):
        extractor = MagicMock()
        expected = PageResult(data=[{"name": "Item"}], next_urls=[], detail_urls=[], summary="ok")
        extractor.analyze_page.return_value = expected

        fallback = MagicMock()

        result = _extract_chunk("html", 1, 1, extractor, fallback, "prompt", "https://example.com", default_settings)

        assert result == expected
        fallback.analyze_page.assert_not_called()

    @patch("scraper_ai.crawler.time.sleep")
    def test_fallback_also_fails_returns_none(self, _mock_sleep):
        settings = Settings(scraper_api_key="test-key", extraction_retries=0)
        extractor = MagicMock()
        extractor.analyze_page.side_effect = ExtractionError("primary fails")

        fallback = MagicMock()
        fallback.analyze_page.side_effect = ExtractionError("fallback fails too")

        result = _extract_chunk("html", 1, 1, extractor, fallback, "prompt", "https://example.com", settings)

        assert result is None
        assert extractor.analyze_page.call_count == 1
        assert fallback.analyze_page.call_count == 1
