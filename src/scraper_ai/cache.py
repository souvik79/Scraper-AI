"""Simple JSON file cache for resuming interrupted crawls."""

from __future__ import annotations

import hashlib
import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

DEFAULT_CACHE_DIR = Path(".scraper_cache")


class CrawlCache:
    """Stores per-URL crawl results as JSON files in a cache directory."""

    def __init__(self, cache_dir: Path | None = None) -> None:
        self._dir = cache_dir or DEFAULT_CACHE_DIR
        self._dir.mkdir(parents=True, exist_ok=True)

    def _key(self, url: str) -> str:
        return hashlib.sha256(url.encode()).hexdigest()[:16]

    def _path(self, url: str) -> Path:
        return self._dir / f"{self._key(url)}.json"

    def has(self, url: str) -> bool:
        return self._path(url).exists()

    def get(self, url: str) -> dict | None:
        path = self._path(url)
        if not path.exists():
            return None
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return None

    def put(self, url: str, data: dict) -> None:
        path = self._path(url)
        path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        logger.debug("Cached result for %s", url)

    def clear(self) -> None:
        """Remove all cached files."""
        for f in self._dir.glob("*.json"):
            f.unlink()
        logger.info("Cache cleared")
