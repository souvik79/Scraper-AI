"""Tests for scraper_ai.models module."""

from __future__ import annotations

from scraper_ai.models import CrawlResult, PageResult


class TestPageResult:
    def test_default_values(self):
        pr = PageResult()
        assert pr.data == []
        assert pr.next_urls == []
        assert pr.detail_urls == []
        assert pr.summary == ""

    def test_with_data(self):
        pr = PageResult(
            data=[{"name": "Product 1", "price": "$10"}],
            next_urls=["https://example.com/page/2"],
            detail_urls=["https://example.com/product/1"],
            summary="Found 1 product",
        )
        assert len(pr.data) == 1
        assert pr.data[0]["name"] == "Product 1"
        assert len(pr.next_urls) == 1
        assert len(pr.detail_urls) == 1
        assert pr.summary == "Found 1 product"

    def test_model_validate_from_dict(self):
        data = {
            "data": [{"key": "value"}],
            "next_urls": [],
            "detail_urls": [],
            "summary": "Test",
        }
        pr = PageResult.model_validate(data)
        assert pr.data == [{"key": "value"}]
        assert pr.summary == "Test"

    def test_model_validate_partial(self):
        """Missing fields should get defaults."""
        data = {"data": [{"a": 1}]}
        pr = PageResult.model_validate(data)
        assert pr.next_urls == []
        assert pr.detail_urls == []
        assert pr.summary == ""

    def test_empty_data_list(self):
        pr = PageResult(data=[])
        assert pr.data == []

    def test_multiple_data_items(self):
        items = [{"id": i} for i in range(5)]
        pr = PageResult(data=items)
        assert len(pr.data) == 5


class TestCrawlResult:
    def test_required_fields(self):
        cr = CrawlResult(url="https://example.com", prompt="scrape it", provider="anthropic")
        assert cr.url == "https://example.com"
        assert cr.prompt == "scrape it"
        assert cr.provider == "anthropic"
        assert cr.pages_crawled == 0
        assert cr.data == []

    def test_with_all_fields(self):
        cr = CrawlResult(
            url="https://example.com",
            prompt="scrape products",
            provider="openai",
            pages_crawled=5,
            data=[{"name": "Item"}],
        )
        assert cr.pages_crawled == 5
        assert len(cr.data) == 1

    def test_model_dump(self):
        cr = CrawlResult(
            url="https://example.com",
            prompt="test",
            provider="anthropic",
            pages_crawled=2,
            data=[{"x": 1}],
        )
        dumped = cr.model_dump()
        assert dumped["url"] == "https://example.com"
        assert dumped["pages_crawled"] == 2
        assert dumped["data"] == [{"x": 1}]

    def test_json_serialization(self):
        cr = CrawlResult(url="https://example.com", prompt="test", provider="anthropic")
        json_str = cr.model_dump_json()
        assert "example.com" in json_str
