"""Tests for scraper_ai.cli module."""

from __future__ import annotations

import json
from io import StringIO
from unittest.mock import MagicMock, patch

import pytest

from scraper_ai.cli import build_parser, main
from scraper_ai.models import CrawlResult


class TestBuildParser:
    def test_requires_url_and_prompt(self):
        parser = build_parser()
        with pytest.raises(SystemExit):
            parser.parse_args([])

    def test_parses_url_and_prompt(self):
        parser = build_parser()
        args = parser.parse_args(["https://example.com", "scrape products"])
        assert args.url == "https://example.com"
        assert args.prompt == "scrape products"

    def test_provider_flag(self):
        parser = build_parser()
        args = parser.parse_args([
            "https://example.com", "test", "--provider", "anthropic"
        ])
        assert args.provider == "anthropic"

    def test_provider_short_flag(self):
        parser = build_parser()
        args = parser.parse_args([
            "https://example.com", "test", "-p", "ollama"
        ])
        assert args.provider == "ollama"

    def test_processor_flag(self):
        parser = build_parser()
        args = parser.parse_args([
            "https://example.com", "test", "--processor", "gemini"
        ])
        assert args.processor == "gemini"

    def test_max_pages_flag(self):
        parser = build_parser()
        args = parser.parse_args([
            "https://example.com", "test", "--max-pages", "50"
        ])
        assert args.max_pages == 50

    def test_auto_scroll_flag(self):
        parser = build_parser()
        args = parser.parse_args([
            "https://example.com", "test", "--auto-scroll"
        ])
        assert args.auto_scroll is True

    def test_no_render_flag(self):
        parser = build_parser()
        args = parser.parse_args([
            "https://example.com", "test", "--no-render"
        ])
        assert args.no_render is True

    def test_output_flag(self):
        parser = build_parser()
        args = parser.parse_args([
            "https://example.com", "test", "-o", "output.json"
        ])
        assert args.output == "output.json"

    def test_verbose_flag(self):
        parser = build_parser()
        args = parser.parse_args([
            "https://example.com", "test", "-v"
        ])
        assert args.verbose is True

    def test_default_values(self):
        parser = build_parser()
        args = parser.parse_args(["https://example.com", "test"])
        assert args.provider is None
        assert args.processor is None
        assert args.max_pages is None
        assert args.auto_scroll is False
        assert args.no_render is False
        assert args.output is None
        assert args.verbose is False


class TestMain:
    @pytest.fixture()
    def mock_crawl_result(self):
        return CrawlResult(
            url="https://example.com",
            prompt="test prompt",
            provider="anthropic",
            pages_crawled=1,
            data=[{"name": "Item"}],
        )

    def test_main_outputs_json_to_stdout(self, mock_crawl_result, tmp_path):
        with patch("scraper_ai.cli.Settings.from_env") as mock_settings, \
             patch("scraper_ai.cli.crawl", return_value=mock_crawl_result), \
             patch("sys.stdout", new_callable=StringIO) as mock_stdout:
            mock_settings.return_value = MagicMock(
                max_pages=100, auto_scroll=False, render_js=True
            )
            result = main(["https://example.com", "test prompt"])

        assert result == 0
        output = mock_stdout.getvalue()
        parsed = json.loads(output)
        assert parsed["url"] == "https://example.com"
        assert parsed["pages_crawled"] == 1

    def test_main_writes_to_file(self, mock_crawl_result, tmp_path):
        outfile = tmp_path / "output.json"
        with patch("scraper_ai.cli.Settings.from_env") as mock_settings, \
             patch("scraper_ai.cli.crawl", return_value=mock_crawl_result):
            mock_settings.return_value = MagicMock(
                max_pages=100, auto_scroll=False, render_js=True
            )
            result = main([
                "https://example.com", "test prompt",
                "-o", str(outfile)
            ])

        assert result == 0
        assert outfile.exists()
        parsed = json.loads(outfile.read_text())
        assert parsed["data"] == [{"name": "Item"}]

    def test_main_loads_prompt_from_file(self, mock_crawl_result, tmp_path):
        prompt_file = tmp_path / "prompt.txt"
        prompt_file.write_text("Extract all products")

        with patch("scraper_ai.cli.Settings.from_env") as mock_settings, \
             patch("scraper_ai.cli.crawl", return_value=mock_crawl_result) as mock_crawl:
            mock_settings.return_value = MagicMock(
                max_pages=100, auto_scroll=False, render_js=True
            )
            main(["https://example.com", str(prompt_file)])

        # The prompt passed to crawl should be the file contents
        call_kwargs = mock_crawl.call_args
        assert call_kwargs.kwargs["user_prompt"] == "Extract all products"

    def test_main_passes_provider(self, mock_crawl_result):
        with patch("scraper_ai.cli.Settings.from_env") as mock_settings, \
             patch("scraper_ai.cli.crawl", return_value=mock_crawl_result) as mock_crawl:
            mock_settings.return_value = MagicMock(
                max_pages=100, auto_scroll=False, render_js=True
            )
            main([
                "https://example.com", "test",
                "--provider", "anthropic"
            ])

        call_kwargs = mock_crawl.call_args
        assert call_kwargs.kwargs["provider_name"] == "anthropic"

    def test_main_passes_processor(self, mock_crawl_result):
        with patch("scraper_ai.cli.Settings.from_env") as mock_settings, \
             patch("scraper_ai.cli.crawl", return_value=mock_crawl_result) as mock_crawl:
            mock_settings.return_value = MagicMock(
                max_pages=100, auto_scroll=False, render_js=True
            )
            main([
                "https://example.com", "test",
                "--processor", "gemini"
            ])

        call_kwargs = mock_crawl.call_args
        assert call_kwargs.kwargs["processor_name"] == "gemini"
