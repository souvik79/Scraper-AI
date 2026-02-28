"""ScrapperAI - Prompt-driven web scraping agent powered by AI."""

__version__ = "0.1.0"

from scrapper_ai.crawler import crawl
from scrapper_ai.models import CrawlResult, PageResult

__all__ = ["crawl", "CrawlResult", "PageResult"]
