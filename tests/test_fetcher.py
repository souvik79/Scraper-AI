"""Tests for scraper_ai.fetcher module."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import httpx
import pytest

from scraper_ai.config import Settings
from scraper_ai.fetcher import FetchError, fetch_html


@pytest.fixture()
def fetch_settings() -> Settings:
    return Settings(scraper_api_key="test-api-key", scraper_timeout=10)


class TestFetchHtml:
    def test_sends_correct_headers(self, fetch_settings):
        mock_response = MagicMock()
        mock_response.text = "<html>Hello</html>"
        mock_response.raise_for_status = MagicMock()

        with patch("scraper_ai.fetcher.httpx.Client") as mock_client:
            mock_client.return_value.__enter__ = MagicMock(return_value=mock_client)
            mock_client.return_value.__exit__ = MagicMock(return_value=False)
            mock_client.get = MagicMock(return_value=mock_response)
            mock_client.return_value.__enter__.return_value = mock_client

            result = fetch_html("https://example.com", fetch_settings)

            mock_client.get.assert_called_once()
            call_kwargs = mock_client.get.call_args
            headers = call_kwargs.kwargs.get("headers", call_kwargs[1].get("headers", {}))
            assert headers["x-sapi-api_key"] == "test-api-key"
            assert headers["x-sapi-render"] == "true"
            assert result == "<html>Hello</html>"

    def test_auto_scroll_adds_instruction_set(self, fetch_settings):
        from dataclasses import replace
        settings = replace(fetch_settings, auto_scroll=True)

        mock_response = MagicMock()
        mock_response.text = "<html></html>"
        mock_response.raise_for_status = MagicMock()

        with patch("scraper_ai.fetcher.httpx.Client") as mock_client:
            mock_client.return_value.__enter__ = MagicMock(return_value=mock_client)
            mock_client.return_value.__exit__ = MagicMock(return_value=False)
            mock_client.get = MagicMock(return_value=mock_response)
            mock_client.return_value.__enter__.return_value = mock_client

            fetch_html("https://example.com", settings)

            call_kwargs = mock_client.get.call_args
            headers = call_kwargs.kwargs.get("headers", call_kwargs[1].get("headers", {}))
            assert "x-sapi-instruction_set" in headers
            instructions = json.loads(headers["x-sapi-instruction_set"])
            assert instructions[0]["type"] == "loop"

    def test_no_render_sends_false(self, fetch_settings):
        from dataclasses import replace
        settings = replace(fetch_settings, render_js=False)

        mock_response = MagicMock()
        mock_response.text = "<html></html>"
        mock_response.raise_for_status = MagicMock()

        with patch("scraper_ai.fetcher.httpx.Client") as mock_client:
            mock_client.return_value.__enter__ = MagicMock(return_value=mock_client)
            mock_client.return_value.__exit__ = MagicMock(return_value=False)
            mock_client.get = MagicMock(return_value=mock_response)
            mock_client.return_value.__enter__.return_value = mock_client

            fetch_html("https://example.com", settings)

            call_kwargs = mock_client.get.call_args
            headers = call_kwargs.kwargs.get("headers", call_kwargs[1].get("headers", {}))
            assert headers["x-sapi-render"] == "false"

    def test_fetch_error_on_exception(self, fetch_settings):
        with patch("scraper_ai.fetcher.httpx.Client") as mock_client:
            mock_client.return_value.__enter__ = MagicMock(return_value=mock_client)
            mock_client.return_value.__exit__ = MagicMock(return_value=False)
            mock_client.get = MagicMock(
                side_effect=httpx.ConnectError("Connection refused")
            )
            mock_client.return_value.__enter__.return_value = mock_client

            with pytest.raises(FetchError, match="Failed to fetch"):
                fetch_html("https://example.com", fetch_settings)


class TestFetchError:
    def test_is_exception(self):
        assert issubclass(FetchError, Exception)

    def test_message(self):
        err = FetchError("something went wrong")
        assert str(err) == "something went wrong"
