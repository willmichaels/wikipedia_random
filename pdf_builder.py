"""
Build a PDF from article title, structured body blocks, and references.
Includes an interactive table of contents with clickable section headings.
"""

from io import BytesIO
import re
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import AnchorFlowable, SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.units import inch

# Type for one block: {"type": "h2"|"h3"|"p", "text": str}
BodyBlock = dict


def _escape(s: str) -> str:
    """Escape for ReportLab Paragraph (HTML-like)."""
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _slug(text: str) -> str:
    """Produce a short anchor-safe id from heading text."""
    s = re.sub(r"[^\w\s-]", "", text.lower())
    s = re.sub(r"[-\s]+", "_", s).strip("_")
    return s[:50] if s else "section"


def _unique_anchor_ids(body_blocks: list[BodyBlock]) -> list[tuple[BodyBlock, str]]:
    """Return list of (block, anchor_id) for each heading, with unique ids."""
    seen: dict[str, int] = {}
    result: list[tuple[BodyBlock, str]] = []
    for b in body_blocks:
        if b["type"] not in ("h2", "h3"):
            continue
        base = _slug(b["text"])
        count = seen.get(base, 0) + 1
        seen[base] = count
        anchor_id = f"{base}_{count}" if count > 1 else base
        result.append((b, anchor_id))
    return result


def build_pdf(title: str, body_blocks: list[BodyBlock], references: list[str]) -> bytes:
    """
    Build a PDF with title, interactive TOC (clickable section headings),
    body (with anchor targets at each heading), and references.
    """
    buf = BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=letter,
        rightMargin=inch,
        leftMargin=inch,
        topMargin=inch,
        bottomMargin=inch,
    )
    styles = getSampleStyleSheet()
    # Slightly smaller style for TOC entries
    toc_style = styles["Normal"]
    story = []

    story.append(Paragraph(_escape(title), styles["Title"]))
    story.append(Spacer(1, 0.15 * inch))

    # Table of contents: list of (block, anchor_id) for headings only
    toc_entries = _unique_anchor_ids(body_blocks)
    if toc_entries or references:
        story.append(Paragraph("Table of Contents", styles["Heading2"]))
        story.append(Spacer(1, 0.12 * inch))
        for block, anchor_id in toc_entries:
            level = block["type"]
            text = _escape(block["text"])
            indent = "&nbsp;" * (4 if level == "h3" else 0)
            link = f'<a href="#{anchor_id}" color="blue">{text}</a>'
            story.append(Paragraph(indent + link, toc_style))
            story.append(Spacer(1, 0.06 * inch))
        if references:
            story.append(
                Paragraph('<a href="#references" color="blue">References</a>', toc_style)
            )
            story.append(Spacer(1, 0.06 * inch))
        story.append(Spacer(1, 0.2 * inch))

    # Body: each heading gets an Anchor flowable (registers PDF destination), then heading text
    toc_index = 0
    for b in body_blocks:
        if b["type"] in ("h2", "h3"):
            anchor_id = toc_entries[toc_index][1] if toc_index < len(toc_entries) else None
            toc_index += 1
            text = _escape(b["text"])
            style = styles["Heading2"] if b["type"] == "h2" else styles["Heading3"]
            if anchor_id:
                story.append(AnchorFlowable(anchor_id))
            story.append(Paragraph(text, style))
            story.append(Spacer(1, 0.1 * inch))
        else:
            safe = _escape(b["text"]).replace("\n", "<br/>")
            story.append(Paragraph(safe, styles["Normal"]))
            story.append(Spacer(1, 0.1 * inch))

    if references:
        story.append(Spacer(1, 0.25 * inch))
        story.append(AnchorFlowable("references"))
        story.append(Paragraph("References", styles["Heading2"]))
        story.append(Spacer(1, 0.15 * inch))
        for ref in references:
            safe = _escape(ref).replace("\n", " ")
            story.append(Paragraph(safe, styles["Normal"]))
            story.append(Spacer(1, 0.08 * inch))

    doc.build(story)
    return buf.getvalue()
