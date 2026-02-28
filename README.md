# scraperAI

**Prompt-driven web scraping powered by AI.** No selectors. No CSS paths. Just describe what you want in plain English.

scraperAI uses a 3-phase pipeline — **Fetch**, **Understand**, **Extract** — to scrape any website intelligently.

```
Fetch (ScraperAPI)  →  Understand (AI)  →  Extract (AI)  →  Structured JSON
```

## How It Works

1. **You write a prompt** describing what to scrape, how to navigate, and what data you want
2. **ScraperAPI** fetches the rendered HTML (handles JS, bot protection, geo-restrictions)
3. **Phase 2 AI** reads the HTML and produces clean markdown — finding all content, links, and images regardless of where they're hidden
4. **Phase 3 AI** extracts structured JSON data from the clean markdown based on your prompt

The AI handles pagination, detail pages, and multi-level crawling automatically based on your prompt.

## Features

- **Prompt-driven** — No code changes needed for different sites. Write a prompt, get data.
- **Multi-level crawling** — Listing pages → Detail pages → Sub-pages. BFS with automatic pagination.
- **Dual-model architecture** — Free Phase 2 model for page understanding + cloud LLM for precise extraction
- **Single-model mode** — Use one provider for everything (skip Phase 2)
- **Image discovery** — Finds images hidden in JavaScript galleries, CSS `background-image`, carousels
- **Data merging** — Detail page data automatically merged into parent listing items
- **Retry + fallback** — Per-chunk retry with exponential backoff; automatic failover to a backup provider
- **Crawl cache** — Resume interrupted crawls without re-fetching already-processed pages
- **Request pacing** — Configurable delay between fetches to respect rate limits
- **6 providers** — Anthropic Claude, OpenAI GPT-4o, Google Gemini, Groq, Ollama (local), mix & match

## Quick Start

### 1. Install

```bash
pip install -e ".[all]"
```

### 2. Configure

Copy `.env.example` to `.env` and add your API keys:

```env
SCRAPER_API_KEY=your_scraper_api_key

# Cloud LLM for extraction (pick one or more)
ANTHROPIC_API_KEY=your_anthropic_key
OPENAI_API_KEY=your_openai_key

# Free Phase 2 processors (pick one)
GEMINI_API_KEY=your_gemini_key        # Recommended — free, fast, large context
# OLLAMA_BASE_URL=http://localhost:11434
# OLLAMA_MODEL=qwen2.5:14b

# Defaults
DEFAULT_PROVIDER=anthropic
CLAUDE_MODEL=claude-haiku-4-5-20251001
GEMINI_MODEL=gemini-2.5-flash

# Resilience (optional)
EXTRACTION_RETRIES=2              # retry attempts per chunk (default: 2)
FALLBACK_PROVIDER=openai          # try this provider if primary fails
FETCH_DELAY=1.0                   # seconds between page fetches
```

### 3. Write a prompt

Create `prompts/my_scrape.txt`:

```
You are scraping a product catalog website.

Step 1 - Listing pages:
Go to the catalog page. You will find products displayed as cards.
Each card has a product name, price, and link to its detail page.
Follow all pagination links until the last page.

For each product, extract:
{
  "name": "Example Product",
  "price": "$29.99",
  "detail_url": "https://example.com/product/123"
}

Put pagination links in next_urls.
Put product detail URLs in detail_urls.

Step 2 - Detail pages:
Visit each product's detail page. Extract full specs:
{
  "name": "Example Product",
  "price": "$29.99",
  "detail_url": "https://example.com/product/123",
  "images": ["https://example.com/img1.jpg"],
  "description": "Full product description...",
  "sku": "ABC-123",
  "category": "Electronics"
}
```

### 4. Run

```bash
# Single-model mode (cloud LLM handles everything)
scraper-ai "https://example.com/catalog" prompts/my_scrape.txt \
  --provider anthropic -o data/output.json

# Dual-model mode (Gemini understands pages, Anthropic extracts data)
scraper-ai "https://example.com/catalog" prompts/my_scrape.txt \
  --provider anthropic --processor gemini -o data/output.json
```

## Providers

| Provider | Use as | Key needed | Free tier |
|---|---|---|---|
| **Anthropic** (Claude Haiku) | Phase 3 extractor | `ANTHROPIC_API_KEY` | No (pay per token) |
| **OpenAI** (GPT-4o) | Phase 3 extractor | `OPENAI_API_KEY` | No (pay per token) |
| **Gemini** (Flash) | Phase 2 processor | `GEMINI_API_KEY` | Yes — 250K TPM, 250 RPD |
| **Groq** (Llama) | Phase 2/3 | `GROQ_API_KEY` | Yes — 6K TPM (limited) |
| **Ollama** (any model) | Phase 2 processor | None (local) | Yes (runs on your machine) |

**Recommended setup:** Gemini Flash for Phase 2 (free, fast, 1M token context) + Claude Haiku for Phase 3 (cheap, accurate).

## CLI Reference

```
scraper-ai <url> <prompt> [options]

Arguments:
  url                   Starting URL to scrape
  prompt                Prompt text or path to a .txt/.md file

Options:
  -p, --provider        AI provider for extraction: anthropic, openai, gemini, groq, ollama
  --processor           AI provider for page understanding (dual-model mode)
  --fallback            Fallback provider if primary extraction fails (e.g. openai)
  --max-pages N         Safety limit on pages to crawl (default: 100)
  --delay SECONDS       Seconds between page fetches (default: 1.0)
  --cache               Enable URL result caching for resume on interrupted crawls
  --clear-cache         Clear the cache before starting
  --auto-scroll         Enable infinite scroll handling
  --no-render           Disable JavaScript rendering
  -o, --output FILE     Output file path (default: stdout)
  -v, --verbose         Enable debug logging
```

## Examples

### Car Dealership (multi-level with detail pages)

```bash
scraper-ai "https://narrowpath.autos/inventory" prompts/cars_test.txt \
  --provider anthropic --processor gemini -o data/cars.json
```

Output:
```json
{
  "pages_crawled": 3,
  "data": [
    {
      "year": 2020,
      "make": "Toyota",
      "model": "4Runner",
      "price": "$34,995.00",
      "images": ["https://...img1", "https://...img2", "...71 total images"],
      "vin": "JTEBU5JR7L5756242",
      "transmission": "Auto",
      "exterior_color": "BLACK",
      "drivetrain": "4WD",
      "fuel_type": "Gas",
      "mileage": "141,960"
    }
  ]
}
```

### Ollama Model Search (single page, no detail pages)

```bash
scraper-ai "https://ollama.com/search?q=scrapping" prompts/ollama_models.txt \
  --provider anthropic -o data/ollama_models.json
```

## Writing Good Prompts

The prompt is the brain of scraperAI. Tips:

1. **Use few-shot JSON examples** — Show the exact field names and formats you want
2. **Describe each level** — Step 1 for listing pages, Step 2 for detail pages
3. **Be explicit about URLs** — "Put pagination in next_urls, detail URLs in detail_urls"
4. **Describe the page structure** — "Cards with basic info", "Gallery with multiple images"
5. **Specify what NOT to do** — "Do NOT follow pagination" for test runs

See [prompts/](prompts/) for examples.

## Architecture

```
Single model (--provider only):
  Fetch → Clean → LLM (extract) → Structured JSON

Dual model (--provider + --processor):
  Fetch → Clean → Processor (understand) → LLM (extract) → Structured JSON
                       ↓                        ↓
                 Clean markdown           Structured JSON
                 with ALL images,         per user prompt
                 links, content
```

**3-Phase Pipeline:**

| Phase | What | Who | Input | Output |
|---|---|---|---|---|
| 1. Fetch | Get rendered HTML | ScraperAPI | URL | Raw HTML |
| 1.5 Clean | Strip boilerplate | Regex | Raw HTML | Cleaned HTML |
| 2. Understand | Read HTML → markdown | Gemini / Ollama | Cleaned HTML | Clean markdown |
| 3. Extract | Follow prompt → JSON | Claude / GPT-4o | Markdown + prompt | Structured data |

See [ARCHITECTURE.md](ARCHITECTURE.md) for the full technical details.

## Limitations & Troubleshooting

scraperAI depends on ScraperAPI for fetching and AI models for extraction. Both can fail in predictable ways.

### Fetch failures

| Symptom | Cause | Fix |
|---|---|---|
| `FetchError` / empty HTML | Bot protection (Cloudflare, Akamai) blocking ScraperAPI | ScraperAPI handles most bot protection, but some sites block all proxies. Try adding `--auto-scroll` or check ScraperAPI dashboard for errors. |
| HTML returned but content missing | SPA loads data via XHR after initial render | JS rendering is on by default (`--no-render` disables it). If content still missing, the site may require authentication or specific cookies. |
| Different HTML than browser | Site serves different content to headless browsers | Some sites detect headless Chrome. ScraperAPI rotates user agents, but geo-restricted content may need a specific country proxy (not yet supported). |
| Timeout errors | Page takes too long to render | Increase timeout via `SCRAPER_TIMEOUT` in `.env` (default: 60s). Heavy SPAs with many API calls may need 90-120s. |

### Extraction failures

| Symptom | Cause | Fix |
|---|---|---|
| Empty `data` array | AI couldn't match your prompt to the page content | Run with `-v` to see the HTML/markdown being sent. Update your prompt to match the actual page structure. |
| Missing fields | Data exists on page but AI didn't extract it | Add explicit field descriptions and few-shot examples to your prompt. Dual-model mode (`--processor gemini`) often captures more content. |
| Hallucinated data | AI invented data not on the page | Lower temperature (already 0.0 by default). Use more specific prompts. Check that the fetched HTML actually contains the expected content. |
| `ExtractionError: Failed to parse` | AI returned malformed JSON | Automatic retry (2 attempts by default). Add `--fallback openai` to try a second provider. If persistent, simplify your prompt's JSON schema. |

### Crawl issues

| Symptom | Cause | Fix |
|---|---|---|
| Crawl never stops | AI keeps finding pagination links | Use `--max-pages N` to set a safety limit. Also add "Do NOT follow pagination" in your prompt for test runs. |
| Detail data not merging | Detail URL doesn't match `detail_url` field in listing data | Ensure your prompt extracts `detail_url` with the exact URL format the site uses (trailing slashes, query params, etc.). |
| Duplicate items | Same item appears on multiple pagination pages | Deduplication by `detail_url` is automatic for Level 1. If items lack a `detail_url`, duplicates may appear. |
| 413 / rate limit errors | Provider's token or request limit exceeded | Use Gemini for Phase 2 (250K TPM). Groq free tier (6K TPM) is too small for most HTML pages. Check provider logs with `-v`. |

### Sites that don't work well

- **Login-required pages** — ScraperAPI doesn't support authenticated sessions. You'd need to pass cookies manually (not yet supported).
- **CAPTCHAs** — ScraperAPI solves some CAPTCHAs, but interactive ones (drag-to-verify, puzzle) will fail.
- **Infinite scroll without pagination URLs** — Use `--auto-scroll` to trigger scroll-based loading. Works for 3 scroll cycles; deeply nested infinite scroll may need multiple runs.
- **Iframed content** — Content inside `<iframe>` tags is stripped by the cleaner. Cross-origin iframe content isn't accessible via the main page fetch.
- **PDF / non-HTML content** — Only HTML pages are supported. PDFs, images, or API endpoints returning raw JSON are not processed.

## Cost

scraperAI is designed to be cheap:

| Component | Cost |
|---|---|
| Gemini Flash (Phase 2) | Free (250 requests/day) |
| Ollama (Phase 2) | Free (local) |
| Claude Haiku (Phase 3) | ~$0.005/page |
| ScraperAPI | Free tier: 1000 calls/month |

A full 24-car scrape with detail pages (~27 pages) costs approximately **$0.10-0.15** with dual-model mode (Gemini + Claude).

## Development

### Install dev dependencies

```bash
pip install -e ".[dev,all]"
```

### Linting

Uses [Ruff](https://docs.astral.sh/ruff/) for linting and import sorting (replaces flake8, isort, pyupgrade).

```bash
# Check for issues
ruff check src/ tests/

# Auto-fix what it can
ruff check src/ tests/ --fix
```

Rules enabled: pycodestyle, pyflakes, isort, pep8-naming, pyupgrade, flake8-bugbear, flake8-simplify, ruff-specific. Configuration is in `pyproject.toml` under `[tool.ruff]`.

### Testing

Uses [pytest](https://docs.pytest.org/) with 98 tests across 7 modules.

```bash
# Run all tests
pytest

# Verbose output
pytest -v

# Run a specific test file
pytest tests/test_cleaner.py

# Run a specific test
pytest tests/test_providers.py::TestProviderInit::test_gemini_requires_api_key
```

Test coverage:

| Module | Tests |
|---|---|
| `test_cleaner.py` | HTML cleaning, tag stripping, chunking |
| `test_config.py` | Settings defaults, env loading, validation |
| `test_models.py` | PageResult, CrawlResult serialization |
| `test_providers.py` | Provider registry, base class, API key checks |
| `test_fetcher.py` | ScraperAPI headers, scroll, error handling |
| `test_crawler.py` | BFS crawl, pagination, detail merge, dual-model |
| `test_cli.py` | Argument parsing, file output, prompt loading |

## License

MIT
