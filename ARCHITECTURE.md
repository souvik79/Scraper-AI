# Architecture

## Pipeline Overview

scraperAI uses a 3-phase pipeline to turn any website into structured JSON data.

```
                    ┌─────────────────────────────────────────────────────────┐
                    │                   scraperAI Pipeline                    │
                    │                                                         │
  URL + Prompt ───▶ │  Phase 1       Phase 2          Phase 3                 │ ───▶ JSON
                    │  ┌───────┐    ┌──────────┐     ┌──────────┐            │
                    │  │ FETCH │───▶│UNDERSTAND│────▶│ EXTRACT  │            │
                    │  │       │    │          │     │          │            │
                    │  │Scraper│    │Local SLM │     │Cloud LLM │            │
                    │  │  API  │    │ (Ollama) │     │ (Claude) │            │
                    │  └───────┘    └──────────┘     └──────────┘            │
                    │   Raw HTML     Clean Markdown    Structured JSON        │
                    └─────────────────────────────────────────────────────────┘
```

### Phase 1 — Fetch

**What:** ScraperAPI fetches the fully rendered HTML page.

**Why:** Websites use JavaScript, bot protection, geo-restrictions. ScraperAPI handles all of this and returns the rendered DOM.

**How:** HTTP GET via ScraperAPI proxy. JS rendering enabled by default. A minimal regex cleanup strips `<script>` bodies, `<style>` bodies, and HTML comments to reduce size. All HTML tags and attributes are preserved.

**Output:** Cleaned HTML (~85% size reduction, but no data loss)

### Phase 2 — Understand (SLM)

**What:** A local Small Language Model reads the HTML and produces clean markdown.

**Why:** Raw HTML has images hidden in JavaScript galleries, CSS `background-image` styles, lazy-loading attributes, and non-standard patterns. A regex cleaner can't find them all. An AI can.

**How:** The SLM receives the HTML with a system prompt:
> "Read this HTML and produce a clean markdown representation. Include all text, all links as `[text](url)`, and ALL image URLs from any source."

**Output:** Clean markdown with all content, links, and image URLs preserved.

**Cost:** Free (runs locally on Ollama)

**Note:** Phase 2 is optional. In single-model mode, the cleaned HTML goes directly to Phase 3.

### Phase 3 — Extract (LLM)

**What:** A cloud LLM reads the content + user's prompt and extracts structured JSON.

**Why:** The user prompt describes exactly what data to extract and in what format. The LLM follows these instructions precisely, producing typed JSON with the exact field names and formats requested.

**How:** The LLM receives:
1. A system prompt explaining the response format (`data`, `next_urls`, `detail_urls`, `summary`)
2. The user's few-shot prompt with JSON examples
3. The page content (markdown from Phase 2, or HTML in single-model mode)

**Output:** `PageResult` JSON with extracted data and discovered URLs.

**Cost:** ~$0.005/page with Claude Haiku

---

## Multi-Level Crawling

The crawler uses Breadth-First Search (BFS) — process all pages at one level before going deeper.

```
Level 1: Listing Pages (BFS with pagination)
┌──────────┐     ┌──────────┐     ┌──────────┐
│  Page 1  │────▶│  Page 2  │────▶│  Page 3  │    next_urls (pagination)
│ 8 cars   │     │ 8 cars   │     │ 8 cars   │
└────┬─────┘     └────┬─────┘     └────┬─────┘
     │                │                │
     └────────────────┴────────────────┘
                      │
              24 detail_urls
                      │
                      ▼
Level 2: Detail Pages (one per car)
┌──────────┐ ┌──────────┐ ┌──────────┐     ┌──────────┐
│  Car 1   │ │  Car 2   │ │  Car 3   │ ... │  Car 24  │
│ +images  │ │ +images  │ │ +images  │     │ +images  │
│ +VIN     │ │ +VIN     │ │ +VIN     │     │ +VIN     │
│ +specs   │ │ +specs   │ │ +specs   │     │ +specs   │
└──────────┘ └──────────┘ └──────────┘     └──────────┘
      │            │            │                │
      └────────────┴────────────┴────────────────┘
                         │
                   Merge into parents
                         │
                         ▼
                 Final JSON output
              (24 fully enriched cars)
```

### URL Routing

The AI returns two types of URLs per page:

| Field | Purpose | When processed |
|---|---|---|
| `next_urls` | Pagination links (page 2, page 3, ...) | Immediately (same level, BFS queue) |
| `detail_urls` | Item detail pages (car 1, car 2, ...) | After current level completes (next level) |

The user's prompt tells the AI which URLs go where:
> "Put pagination links in next_urls. Put each car's detail page URL in detail_urls."

### Merge Logic

When a detail page is processed, its extracted data is merged into the parent item:

```
Parent (Level 1):   { year: 2020, make: "Toyota", price: "$34,995", detail_url: "..." }
                                         +
Detail (Level 2):   { images: [...67 photos], vin: "JTEB...", transmission: "Auto" }
                                         =
Merged result:      { year: 2020, make: "Toyota", price: "$34,995", detail_url: "...",
                      images: [...67 photos], vin: "JTEB...", transmission: "Auto" }
```

Matching is done by URL: `parent.detail_url == visited_url`.

---

## Single-Model vs Dual-Model

```
Single-model (--provider only):
  Fetch ──▶ Regex Clean ──▶ LLM (extract) ──▶ JSON

Dual-model (--provider + --processor):
  Fetch ──▶ Regex Clean ──▶ SLM (understand) ──▶ LLM (extract) ──▶ JSON
```

| | Single-Model | Dual-Model |
|---|---|---|
| Command | `--provider anthropic` | `--provider anthropic --processor ollama` |
| Phase 2 | Skipped | Local SLM |
| Phase 3 input | Cleaned HTML | Clean markdown |
| Image discovery | Limited (only `<img>` tags) | Complete (JS, CSS, data attrs) |
| Cost per page | ~$0.005 | ~$0.005 (SLM is free) |
| Speed | Faster (1 AI call) | Slower (2 AI calls, SLM can be slow) |

---

## User Prompts

The prompt is the brain. It controls everything: what pages to visit, what data to extract, what format to use. The code never changes between different scraping targets — only the prompt changes.

### Anatomy of a Good Prompt

```
Step 1 - Listing pages:                     ← Navigation instructions
  Description of the page structure          ← Helps AI understand the HTML
  What to extract per item                   ← Data requirements

  Few-shot JSON example:                     ← CRITICAL: exact field names + formats
  {
    "year": 2020,
    "make": "Toyota",
    "price": "$34,995.00",
    "detail_url": "https://..."
  }

  URL routing instructions                   ← "Put pagination in next_urls"

Step 2 - Detail pages:                       ← Next level instructions
  Description of detail page structure
  What additional data to extract

  Few-shot JSON example:                     ← Complete merged shape
  {
    "year": 2020,
    "make": "Toyota",
    "price": "$34,995.00",
    "images": ["https://..."],
    "vin": "JTEBU5JR8L5123456"
  }
```

### Key Principles

1. **Few-shot examples are mandatory** — The AI needs to see exact field names (`year` not `Year`), exact formats (`"$34,995.00"` not `34995`), and the complete output shape
2. **Be explicit about levels** — "Step 1" for listings, "Step 2" for details. The crawler tells the AI which step it's on
3. **Describe the page visually** — "Cards with basic info", "Photo gallery/carousel", "Specs table"
4. **Route URLs explicitly** — "Put pagination links in next_urls. Put detail page URLs in detail_urls."

---

## File Structure

```
scraperAI/
├── src/scraper_ai/
│   ├── cli.py              CLI entry point, argument parsing
│   ├── config.py           Settings from .env (API keys, models, limits)
│   ├── cleaner.py          Minimal regex HTML cleanup (no BS4)
│   ├── crawler.py          Multi-level BFS crawl loop + merge logic
│   ├── fetcher.py          ScraperAPI HTML fetching
│   ├── models.py           Pydantic models (PageResult, CrawlResult)
│   └── providers/
│       ├── __init__.py     Provider registry + lazy factory
│       ├── base.py         Abstract base, system prompts, JSON parsing
│       ├── anthropic.py    Claude Haiku provider
│       ├── ollama.py       Local Ollama SLM provider
│       └── openai.py       GPT-4o provider
├── prompts/                User prompt files (.txt)
├── data/                   Output JSON files
├── .env                    API keys and configuration
└── pyproject.toml          Package config
```

---

## Data Flow (Detailed)

```
User runs:
  scraper-ai "https://site.com" prompts/cars.txt --provider anthropic --processor ollama

1. cli.py
   ├── Parses arguments
   ├── Loads settings from .env
   ├── Reads prompt from prompts/cars.txt
   └── Calls crawler.crawl()

2. crawler.py — Level 1 (Listing Pages)
   ├── Queue: [https://site.com]
   │
   ├── For each URL in queue:
   │   ├── fetcher.py      → ScraperAPI → raw HTML (87KB)
   │   ├── cleaner.py      → regex strip → cleaned HTML (15KB)
   │   ├── ollama.py       → SLM understand_page() → markdown (5KB)
   │   ├── anthropic.py    → LLM analyze_page() → PageResult
   │   │   ├── data: [{year, make, model, price, detail_url}, ...]
   │   │   ├── next_urls: [page2, page3]          → add to queue
   │   │   └── detail_urls: [car1, car2, ...]      → save for Level 2
   │   └── Dedup items by detail_url
   │
   └── All pagination exhausted → 24 cars collected

3. crawler.py — Level 2 (Detail Pages)
   ├── Queue: [car1_url, car2_url, ..., car24_url]
   │
   ├── For each URL:
   │   ├── fetcher.py      → ScraperAPI → raw HTML
   │   ├── cleaner.py      → regex strip
   │   ├── ollama.py       → SLM → markdown with ALL images
   │   ├── anthropic.py    → LLM → PageResult with enriched data
   │   └── Merge into parent: parent.update(detail_data)
   │
   └── All detail pages done → 24 fully enriched cars

4. cli.py
   └── Writes JSON to data/cars.json
```
