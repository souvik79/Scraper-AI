"""Minimal HTML size reduction for the AI pipeline.

Phase 2 (SLM) does the real understanding. This module just strips
script/style bodies, comments, and whitespace to reduce token cost.
All HTML tags and attributes are preserved so the AI can see everything.
"""

from __future__ import annotations

import re


def clean_html(raw_html: str) -> str:
    """Strip script/style bodies, boilerplate elements, comments, and whitespace."""
    text = raw_html
    # Remove script bodies
    text = re.sub(r"<script[^>]*>.*?</script>", "", text, flags=re.DOTALL | re.IGNORECASE)
    # Remove style bodies
    text = re.sub(r"<style[^>]*>.*?</style>", "", text, flags=re.DOTALL | re.IGNORECASE)
    # Remove HTML comments
    text = re.sub(r"<!--.*?-->", "", text, flags=re.DOTALL)
    # Remove boilerplate elements (nav, footer, iframe, noscript)
    text = re.sub(r"<nav[^>]*>.*?</nav>", "", text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<footer[^>]*>.*?</footer>", "", text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<iframe[^>]*>.*?</iframe>", "", text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<noscript[^>]*>.*?</noscript>", "", text, flags=re.DOTALL | re.IGNORECASE)
    # Collapse whitespace
    text = re.sub(r"\s+", " ", text)
    # Add newlines around block elements for readability
    text = re.sub(r">\s*<", ">\n<", text)
    return text.strip()


def chunk_text(text: str, max_chars: int = 48000) -> list[str]:
    """
    Split text into chunks that fit within token limits.

    Uses ~4 chars/token heuristic. max_chars=48000 ~ 12k tokens.
    Splits on double-newline boundaries first, then single-newline
    (for cleaned HTML which only has \\n between tags).
    """
    if len(text) <= max_chars:
        return [text]

    # Try double-newline split first, fall back to single-newline for HTML
    lines = text.split("\n\n")
    if len(lines) == 1:
        lines = text.split("\n")

    sep = "\n\n" if "\n\n" in text else "\n"
    sep_len = len(sep)

    chunks: list[str] = []
    current_chunk: list[str] = []
    current_size = 0

    for line in lines:
        line_size = len(line) + sep_len
        if current_size + line_size > max_chars and current_chunk:
            chunks.append(sep.join(current_chunk))
            current_chunk = [line]
            current_size = line_size
        else:
            current_chunk.append(line)
            current_size += line_size

    if current_chunk:
        chunks.append(sep.join(current_chunk))

    return chunks
