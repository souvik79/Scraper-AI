"""Tests for scraper_ai.cleaner module."""

from __future__ import annotations

from scraper_ai.cleaner import chunk_text, clean_html

from .conftest import SAMPLE_HTML


class TestCleanHtml:
    def test_removes_script_tags(self):
        html = '<div>Hello</div><script>alert("xss")</script><p>World</p>'
        result = clean_html(html)
        assert "alert" not in result
        assert "Hello" in result
        assert "World" in result

    def test_removes_style_tags(self):
        html = "<div>Hello</div><style>body { color: red; }</style>"
        result = clean_html(html)
        assert "color: red" not in result
        assert "Hello" in result

    def test_removes_html_comments(self):
        html = "<div>Hello</div><!-- secret comment --><p>World</p>"
        result = clean_html(html)
        assert "secret comment" not in result
        assert "Hello" in result

    def test_removes_nav_tags(self):
        html = '<nav><a href="/">Home</a></nav><div>Content</div>'
        result = clean_html(html)
        assert "Home" not in result
        assert "Content" in result

    def test_removes_footer_tags(self):
        html = "<div>Content</div><footer>Copyright 2024</footer>"
        result = clean_html(html)
        assert "Copyright" not in result
        assert "Content" in result

    def test_removes_iframe_tags(self):
        html = '<div>Content</div><iframe src="https://ads.example.com">ad</iframe>'
        result = clean_html(html)
        assert "ads.example.com" not in result
        assert "Content" in result

    def test_removes_noscript_tags(self):
        html = "<div>Content</div><noscript>Enable JS</noscript>"
        result = clean_html(html)
        assert "Enable JS" not in result
        assert "Content" in result

    def test_preserves_regular_content(self):
        html = "<div><h1>Title</h1><p>Paragraph</p></div>"
        result = clean_html(html)
        assert "Title" in result
        assert "Paragraph" in result

    def test_preserves_img_attributes(self):
        html = '<img src="https://example.com/img.jpg" data-src="https://example.com/big.jpg">'
        result = clean_html(html)
        assert "https://example.com/img.jpg" in result
        assert "https://example.com/big.jpg" in result

    def test_collapses_whitespace(self):
        html = "<div>   lots    of    spaces   </div>"
        result = clean_html(html)
        assert "   " not in result

    def test_case_insensitive_tag_removal(self):
        html = '<SCRIPT type="text/javascript">alert(1)</SCRIPT><div>OK</div>'
        result = clean_html(html)
        assert "alert" not in result
        assert "OK" in result

    def test_sample_html(self):
        result = clean_html(SAMPLE_HTML)
        # Script content removed
        assert "console.log" not in result
        # Style content removed
        assert "color: red" not in result
        # Nav removed
        assert "About" not in result
        # Footer removed
        assert "Copyright" not in result
        # Comment removed
        assert "This is a comment" not in result
        # Real content preserved
        assert "Hello World" in result
        assert "https://example.com" in result

    def test_empty_input(self):
        assert clean_html("") == ""

    def test_no_tags_to_strip(self):
        html = "<div>Simple content</div>"
        result = clean_html(html)
        assert "Simple content" in result

    def test_reduces_size(self):
        result = clean_html(SAMPLE_HTML)
        assert len(result) < len(SAMPLE_HTML)


class TestChunkText:
    def test_short_text_returns_single_chunk(self):
        text = "Hello, world!"
        chunks = chunk_text(text, max_chars=100)
        assert len(chunks) == 1
        assert chunks[0] == text

    def test_splits_on_double_newline(self):
        text = "Part 1\n\nPart 2\n\nPart 3"
        chunks = chunk_text(text, max_chars=15)
        assert len(chunks) >= 2
        # All parts should be present in the chunks
        joined = "\n\n".join(chunks)
        assert "Part 1" in joined
        assert "Part 2" in joined
        assert "Part 3" in joined

    def test_falls_back_to_single_newline(self):
        text = "Line 1\nLine 2\nLine 3\nLine 4"
        chunks = chunk_text(text, max_chars=15)
        assert len(chunks) >= 2
        joined = "\n".join(chunks)
        assert "Line 1" in joined
        assert "Line 4" in joined

    def test_respects_max_chars(self):
        text = "\n\n".join([f"Paragraph {i}" for i in range(20)])
        chunks = chunk_text(text, max_chars=50)
        for chunk in chunks:
            # Each chunk should be roughly within the limit
            # (individual paragraphs that exceed the limit are allowed)
            assert len(chunk) <= 60  # small buffer for separator

    def test_default_max_chars(self):
        short_text = "Hello"
        chunks = chunk_text(short_text)
        assert len(chunks) == 1

    def test_html_with_only_single_newlines(self):
        """Cleaned HTML typically has only single newlines between tags."""
        lines = [f"<div>Content block {i}</div>" for i in range(50)]
        html = "\n".join(lines)
        chunks = chunk_text(html, max_chars=200)
        assert len(chunks) > 1
        # All content should be preserved
        all_content = "\n".join(chunks)
        assert "Content block 0" in all_content
        assert "Content block 49" in all_content

    def test_empty_text(self):
        chunks = chunk_text("", max_chars=100)
        assert len(chunks) == 1
        assert chunks[0] == ""
