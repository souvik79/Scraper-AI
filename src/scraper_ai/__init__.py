"""ScraperAI - Prompt-driven web scraping agent powered by AI."""

__version__ = "0.1.0"

from scraper_ai.crawler import crawl
from scraper_ai.models import CrawlResult, PageResult

__all__ = ["CrawlResult", "PageResult", "crawl"]
