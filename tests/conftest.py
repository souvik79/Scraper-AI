"""Shared fixtures for ScraperAI tests."""

from __future__ import annotations

import pytest

from scraper_ai.config import Settings


@pytest.fixture()
def settings() -> Settings:
    """Minimal settings with dummy keys for testing."""
    return Settings(
        scraper_api_key="test-scraper-key",
        openai_api_key="test-openai-key",
        anthropic_api_key="test-anthropic-key",
        groq_api_key="test-groq-key",
        gemini_api_key="test-gemini-key",
    )


SAMPLE_HTML = """\
<!DOCTYPE html>
<html>
<head>
    <title>Test Page</title>
    <script>var x = 1; console.log("hello");</script>
    <style>body { color: red; }</style>
</head>
<body>
    <nav><a href="/home">Home</a><a href="/about">About</a></nav>
    <div class="content">
        <h1>Hello World</h1>
        <p>This is a test page with <a href="https://example.com">a link</a>.</p>
        <img src="https://example.com/image.jpg" alt="test">
    </div>
    <footer>Copyright 2024</footer>
    <!-- This is a comment -->
    <noscript>Please enable JavaScript</noscript>
    <iframe src="https://ads.example.com"></iframe>
</body>
</html>
"""

SAMPLE_AI_RESPONSE = """\
{
    "data": [
        {"name": "Product 1", "price": "$10.00"},
        {"name": "Product 2", "price": "$20.00"}
    ],
    "next_urls": ["https://example.com/page/2"],
    "detail_urls": ["https://example.com/product/1", "https://example.com/product/2"],
    "summary": "Found 2 products on the listing page"
}
"""
