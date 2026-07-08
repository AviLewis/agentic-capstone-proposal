"""Render an approved research plan into Notion blocks.

Produces a page title plus a list of Notion block objects (headings, paragraphs,
bulleted lists) from a plan's ``content_json``, its judge scores, and the papers
discovered for the plan's question (rendered as linked sources).
"""

from __future__ import annotations

from typing import Any

# Ordered (key, heading) pairs for list-valued plan sections.
_LIST_SECTIONS: list[tuple[str, str]] = [
    ("hypotheses", "Hypotheses"),
    ("methods", "Methods"),
    ("data", "Data"),
    ("risks", "Risks"),
    ("resources", "Resources"),
]

# Sections whose items may cite the paper they were drawn from.
_SOURCED_SECTIONS: frozenset[str] = frozenset({"methods", "data"})

# Notion has a 2000-char limit per rich_text content chunk.
_MAX_TEXT = 1900


def _text_span(content: str, url: str | None = None) -> dict[str, Any]:
    span: dict[str, Any] = {
        "type": "text",
        "text": {"content": (content or "")[:_MAX_TEXT]},
    }
    if url:
        span["text"]["link"] = {"url": url}
    return span


def _rich_text(content: str) -> list[dict[str, Any]]:
    return [_text_span(content)]


def _heading(text: str, *, level: int = 2) -> dict[str, Any]:
    key = f"heading_{level}"
    return {
        "object": "block",
        "type": key,
        key: {"rich_text": _rich_text(text)},
    }


def _toggle_heading(
    text: str, children: list[dict[str, Any]], *, level: int = 2
) -> dict[str, Any]:
    """A heading that collapses/expands, with its content nested inside."""
    key = f"heading_{level}"
    return {
        "object": "block",
        "type": key,
        key: {
            "rich_text": _rich_text(text),
            "is_toggleable": True,
            "children": children,
        },
    }


def _paragraph(text: str) -> dict[str, Any]:
    return {
        "object": "block",
        "type": "paragraph",
        "paragraph": {"rich_text": _rich_text(text)},
    }


def _bullet(text: str) -> dict[str, Any]:
    return {
        "object": "block",
        "type": "bulleted_list_item",
        "bulleted_list_item": {"rich_text": _rich_text(text)},
    }


def _as_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(v) for v in value]
    if value in (None, ""):
        return []
    return [str(value)]


def _paper_link(paper: dict[str, Any]) -> str | None:
    """Resolve the best clickable URL for a paper (direct URL, else DOI)."""
    url = paper.get("url")
    if isinstance(url, str) and url.startswith(("http://", "https://")):
        return url
    doi = paper.get("doi")
    if isinstance(doi, str) and doi.strip():
        doi = doi.strip()
        if doi.startswith(("http://", "https://")):
            return doi
        return f"https://doi.org/{doi}"
    return None


def _paper_detail(paper: dict[str, Any]) -> str:
    """Build a short 'Authors, Year: relevance' suffix for a source bullet."""
    parts: list[str] = []
    authors = paper.get("authors") or []
    if isinstance(authors, list) and authors:
        first = str(authors[0])
        if len(authors) > 1:
            first += " et al."
        parts.append(first)
    year = paper.get("year")
    if year:
        parts.append(str(year))
    meta = ", ".join(parts)
    relevance = paper.get("relevance")
    if meta and relevance:
        return f"{meta}: {relevance}"
    return relevance or meta


def _source_bullet(paper: dict[str, Any]) -> dict[str, Any]:
    """A bulleted list item linking a paper's title, with an optional note."""
    title = str(paper.get("title") or paper.get("url") or "Untitled source")
    rich = [_text_span(title, _paper_link(paper))]
    detail = _paper_detail(paper)
    if detail:
        rich.append(_text_span(f" — {detail}"))
    return {
        "object": "block",
        "type": "bulleted_list_item",
        "bulleted_list_item": {"rich_text": rich},
    }


def _bullet_from_spans(spans: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "object": "block",
        "type": "bulleted_list_item",
        "bulleted_list_item": {"rich_text": spans},
    }


def _sourced_bullet(
    item: Any, papers_by_title: dict[str, dict[str, Any]]
) -> dict[str, Any]:
    """Render an entry, linking the paper it was cited from (if any).

    Used for both methods and data sources. Accepts either a plain string
    (legacy) or a ``{"description", "source"}`` object where ``source`` is the
    exact title of a paper from the run.
    """
    if not isinstance(item, dict):
        return _bullet(str(item))

    description = str(item.get("description") or "").strip()
    source = item.get("source")
    source = str(source).strip() if source else ""
    if not source:
        return _bullet(description or "—")

    paper = papers_by_title.get(source.lower())
    url = _paper_link(paper) if paper else None
    spans: list[dict[str, Any]] = []
    if description:
        spans.append(_text_span(f"{description} — "))
    spans.append(_text_span(source, url))
    return _bullet_from_spans(spans)


def plan_title(content: dict[str, Any], question_text: str = "") -> str:
    if question_text:
        return f"Research Plan: {question_text}"[:_MAX_TEXT]
    objective = content.get("objective")
    if objective:
        return f"Research Plan: {objective}"[:_MAX_TEXT]
    return "Research Plan"


def plan_to_blocks(
    content: dict[str, Any],
    scores: list[dict[str, Any]] | None = None,
    question_text: str = "",
    papers: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    """Build the ordered list of Notion blocks for a plan page."""
    blocks: list[dict[str, Any]] = []

    # Intro context stays visible so the page opens with the framing in view.
    if question_text:
        blocks.append(_heading("Research Question", level=1))
        blocks.append(_paragraph(question_text))

    objective = content.get("objective")
    if objective:
        blocks.append(_heading("Objective"))
        blocks.append(_paragraph(str(objective)))

    papers_by_title = {
        str(p.get("title") or "").strip().lower(): p
        for p in (papers or [])
        if p.get("title")
    }

    # Detail sections collapse into toggle headings for a compact, scannable page.
    for key, heading in _LIST_SECTIONS:
        if key in _SOURCED_SECTIONS:
            raw = content.get(key)
            sourced_items = raw if isinstance(raw, list) else _as_list(raw)
            if not sourced_items:
                continue
            bullets = [_sourced_bullet(it, papers_by_title) for it in sourced_items]
            blocks.append(_toggle_heading(heading, bullets))
            continue
        items = _as_list(content.get(key))
        if not items:
            continue
        blocks.append(_toggle_heading(heading, [_bullet(item) for item in items]))

    if scores:
        children: list[dict[str, Any]] = []
        total = 0.0
        for s in scores:
            criterion = str(s.get("criterion", "")).replace("_", " ").title()
            score = s.get("score", 0)
            weight = s.get("weight", 0)
            justification = s.get("justification", "")
            total += float(score) * float(weight)
            children.append(_bullet(f"{criterion}: {score}/5 — {justification}"))
        children.append(_paragraph(f"Weighted feasibility score: {total:.2f} / 5"))
        blocks.append(_toggle_heading("Feasibility assessment", children))

    # Linked sources carried over from the discovery step (papers for this
    # question), so the exported plan is traceable back to its evidence.
    if papers:
        source_bullets = [_source_bullet(p) for p in papers if p.get("title") or p.get("url")]
        if source_bullets:
            blocks.append(_toggle_heading("Sources", source_bullets))

    return blocks
