"""Command-line interface for ScrapperAI."""

from __future__ import annotations

import argparse
import json
import logging
import sys

from scrapper_ai.config import Settings
from scrapper_ai.crawler import crawl
from scrapper_ai.providers import list_providers


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="scrapper-ai",
        description="Prompt-driven web scraping agent powered by AI.",
    )
    parser.add_argument("url", help="URL to start scraping from")
    parser.add_argument(
        "prompt",
        help="Prompt text or path to a .txt/.md file containing the prompt (e.g., prompts/cars.txt)",
    )
    parser.add_argument(
        "-p", "--provider",
        choices=list_providers(),
        default=None,
        help="AI provider to use (default: from .env DEFAULT_PROVIDER)",
    )
    parser.add_argument(
        "--processor",
        choices=list_providers(),
        default=None,
        help="AI provider for Phase 2 page understanding (e.g. ollama). "
             "If not set, --provider handles everything in single-model mode.",
    )
    parser.add_argument(
        "--max-pages",
        type=int,
        default=None,
        help="Safety limit on pages to crawl (default: 100). Crawl stops naturally when no more URLs are discovered.",
    )
    parser.add_argument(
        "--auto-scroll",
        action="store_true",
        help="Enable scroll-based loading for infinite scroll pages",
    )
    parser.add_argument(
        "--no-render",
        action="store_true",
        help="Disable JavaScript rendering",
    )
    parser.add_argument(
        "-o", "--output",
        default=None,
        help="Output file path (default: stdout)",
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose logging",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    settings = Settings.from_env()

    # Apply CLI overrides
    overrides = {}
    if args.max_pages is not None:
        overrides["max_pages"] = args.max_pages
    if args.auto_scroll:
        overrides["auto_scroll"] = True
    if args.no_render:
        overrides["render_js"] = False
    if overrides:
        from dataclasses import replace
        settings = replace(settings, **overrides)

    # Load prompt from file if it looks like a file path
    prompt = args.prompt
    from pathlib import Path
    prompt_path = Path(prompt)
    if prompt_path.is_file():
        prompt = prompt_path.read_text(encoding="utf-8").strip()
        print(f"Loaded prompt from {prompt_path}", file=sys.stderr)

    result = crawl(
        start_url=args.url,
        user_prompt=prompt,
        provider_name=args.provider,
        processor_name=args.processor,
        settings=settings,
    )

    output = json.dumps(result.model_dump(), indent=2, ensure_ascii=False)

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(output)
        print(f"Output written to {args.output}")
    else:
        print(output)

    return 0


if __name__ == "__main__":
    sys.exit(main())
