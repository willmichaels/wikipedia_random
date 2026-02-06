"""
Fetch Wikipedia article content and extract body text and references.
"""

import requests
from bs4 import BeautifulSoup

DEFAULT_HEADERS = {"User-Agent": "VitalArticleScraper/1.0 (science_fan@example.com)"}


def _clean_reference_text(raw: str) -> str:
    """Remove Wikipedia backlink cruft (^ a b c, Jump to, etc.) from reference text."""
    text = raw.strip()
    # Strip leading "^" and following "a b c" backlink labels
    if text.startswith("^"):
        text = text[1:].lstrip()
    # Remove leading run of single letters and spaces (backlink labels)
    while text:
        i = 0
        while i < len(text) and text[i] in "abcdefghijklmnopqrstuvwxyz ":
            i += 1
        if i > 0 and (i == len(text) or text[i] == ">" or (text[i:i+1].strip() == "" and ">" in text[:20])):
            text = text[i:].strip().lstrip(">").strip()
        else:
            break
    return text


def _extract_references_from_soup(soup: BeautifulSoup) -> list[str]:
    """
    Extract the References section as a list of "[n] reference_text" strings.
    Finds all citation <li> elements in document order within #mw-content-text.
    """
    refs: list[str] = []
    content = soup.find(id="mw-content-text")
    if not content:
        return refs

    for li in content.find_all("li", id=lambda x: x and x.startswith("cite_note-")):
        text = li.get_text(separator=" ", strip=True)
        text = _clean_reference_text(text)
        if text:
            refs.append(f"[{len(refs) + 1}] {text}")
    return refs


def _body_stops_at_heading(heading_text: str) -> bool:
    """Return True if we should stop collecting body at this section heading."""
    lower = heading_text.strip().lower()
    return lower in ("see also", "references", "further reading", "external links")


# Type for one block of body content: heading (h2/h3) or paragraph (p).
BodyBlock = dict  # {"type": "h2"|"h3"|"p", "text": str}


def fetch_article_content(article_url: str) -> tuple[str | None, list[BodyBlock], list[str]]:
    """
    Fetch a Wikipedia article and return (title, body_blocks, references).
    body_blocks: list of {"type": "h2"|"h3"|"p", "text": str} for TOC and PDF structure.
    Body stops at "See also", "References", "Further reading", or "External links".
    On failure returns (None, [], []).
    """
    try:
        response = requests.get(article_url, headers=DEFAULT_HEADERS)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, "html.parser")

        title_el = soup.find(id="firstHeading")
        title = title_el.get_text(strip=True) if title_el else "Untitled"

        content_div = soup.find(id="mw-content-text")
        if not content_div:
            return title, [], []

        # Remove non-content elements but keep structure for references extraction
        for tag in content_div.find_all(["script", "style", "nav", "table", "figure"]):
            tag.decompose()

        body_blocks: list[BodyBlock] = []
        for el in content_div.find_all(["h2", "h3", "p"]):
            if el.name in ("h2", "h3"):
                text = el.get_text(separator=" ", strip=True)
                if text and _body_stops_at_heading(text):
                    break
                if text:
                    body_blocks.append({"type": el.name, "text": text})
                continue
            text = el.get_text(separator=" ", strip=True)
            if text:
                body_blocks.append({"type": "p", "text": text})

        references = _extract_references_from_soup(soup)
        return title, body_blocks, references

    except Exception as e:
        print(f"Error fetching article {article_url}: {e}")
        return None, [], []


def body_blocks_to_plain_text(body_blocks: list[BodyBlock]) -> str:
    """Convert body_blocks to a single plain-text string (headings and paragraphs)."""
    parts: list[str] = []
    for b in body_blocks:
        if b["type"] in ("h2", "h3"):
            parts.append("\n\n" + b["text"] + "\n")
        else:
            parts.append(b["text"])
    return "\n".join(parts).strip() if parts else ""


def format_plain_text_with_references(
    title: str, body_blocks: list[BodyBlock], references: list[str]
) -> str:
    """Build full plain text: title, body, then References section."""
    body = body_blocks_to_plain_text(body_blocks)
    sections = [title, "=" * len(title), "", body]
    if references:
        sections.extend(["", "References", "", "\n\n".join(references)])
    return "\n".join(sections)


def safe_filename(title: str, max_len: int = 80) -> str:
    """Return a safe filename stem from the article title."""
    return "".join(c if c.isalnum() or c in " -_" else "_" for c in title)[:max_len]