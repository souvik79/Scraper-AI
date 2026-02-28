"""Tests for scraper_ai.cache module."""

from __future__ import annotations

from scraper_ai.cache import CrawlCache


class TestCrawlCache:
    def test_put_and_get(self, tmp_path):
        cache = CrawlCache(cache_dir=tmp_path / "cache")
        entry = {"url": "https://example.com", "data": [{"name": "Item"}], "pagination_urls": [], "detail_urls": []}
        cache.put("https://example.com", entry)
        result = cache.get("https://example.com")
        assert result == entry

    def test_has_returns_false_for_missing(self, tmp_path):
        cache = CrawlCache(cache_dir=tmp_path / "cache")
        assert cache.has("https://example.com/missing") is False

    def test_get_returns_none_for_missing(self, tmp_path):
        cache = CrawlCache(cache_dir=tmp_path / "cache")
        assert cache.get("https://example.com/missing") is None

    def test_has_returns_true_after_put(self, tmp_path):
        cache = CrawlCache(cache_dir=tmp_path / "cache")
        cache.put("https://example.com", {"data": []})
        assert cache.has("https://example.com") is True

    def test_clear_removes_all(self, tmp_path):
        cache = CrawlCache(cache_dir=tmp_path / "cache")
        cache.put("https://example.com/1", {"data": [1]})
        cache.put("https://example.com/2", {"data": [2]})
        assert cache.has("https://example.com/1")
        assert cache.has("https://example.com/2")

        cache.clear()

        assert cache.has("https://example.com/1") is False
        assert cache.has("https://example.com/2") is False

    def test_cache_dir_created_on_init(self, tmp_path):
        cache_dir = tmp_path / "new_cache_dir"
        assert not cache_dir.exists()
        CrawlCache(cache_dir=cache_dir)
        assert cache_dir.exists()

    def test_corrupted_file_returns_none(self, tmp_path):
        cache = CrawlCache(cache_dir=tmp_path / "cache")
        # Write a valid entry first to get the file path
        cache.put("https://example.com", {"data": []})
        # Corrupt the file
        path = cache._path("https://example.com")
        path.write_text("not valid json{{{", encoding="utf-8")
        assert cache.get("https://example.com") is None

    def test_different_urls_have_different_keys(self, tmp_path):
        cache = CrawlCache(cache_dir=tmp_path / "cache")
        cache.put("https://example.com/a", {"data": [1]})
        cache.put("https://example.com/b", {"data": [2]})
        assert cache.get("https://example.com/a")["data"] == [1]
        assert cache.get("https://example.com/b")["data"] == [2]
