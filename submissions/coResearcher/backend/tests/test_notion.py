"""Tests for Notion export: renderer, tool selection, URL parse, export guard."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest

from app.db import repository
from app.db.models import Plan, Question
from app.notion import (
    ExportNotApprovedError,
    ExportPlanMismatchError,
    export_plan,
    extract_page_url,
    find_create_page_tool,
    plan_title,
    plan_to_blocks,
)

# --- renderer ---------------------------------------------------------------

PLAN_CONTENT = {
    "objective": "Study X",
    "hypotheses": ["H1", "H2"],
    "methods": ["survey"],
    "data": [],
    "risks": ["r1"],
    "resources": ["gpu"],
}


def test_plan_title_prefers_question():
    assert plan_title(PLAN_CONTENT, "What is X?") == "Research Plan: What is X?"
    assert plan_title(PLAN_CONTENT, "") == "Research Plan: Study X"
    assert plan_title({}, "") == "Research Plan"


def test_plan_to_blocks_structure():
    scores = [
        {"criterion": "data_availability", "score": 4, "weight": 0.25, "justification": "ok"}
    ]
    blocks = plan_to_blocks(PLAN_CONTENT, scores, "What is X?")
    types = [b["type"] for b in blocks]
    # Research Question is a top-level H1; other sections are H2.
    assert "heading_1" in types
    assert "heading_2" in types

    # List sections become collapsible toggle headings with bullets nested inside.
    toggles = {
        b["heading_2"]["rich_text"][0]["text"]["content"]: b
        for b in blocks
        if b["type"] == "heading_2" and b["heading_2"].get("is_toggleable")
    }
    assert "Hypotheses" in toggles
    hypotheses_children = toggles["Hypotheses"]["heading_2"]["children"]
    assert [c["type"] for c in hypotheses_children] == [
        "bulleted_list_item",
        "bulleted_list_item",
    ]

    # Empty 'data' section is skipped; Feasibility is a toggle too.
    assert "Data" not in toggles
    assert "Feasibility assessment" in toggles

    # Objective stays a plain (non-collapsible) H2 so it's visible on open.
    plain_headings = [
        b["heading_2"]["rich_text"][0]["text"]["content"]
        for b in blocks
        if b["type"] == "heading_2" and not b["heading_2"].get("is_toggleable")
    ]
    assert "Objective" in plain_headings


def test_plan_to_blocks_renders_linked_sources():
    papers = [
        {
            "title": "Deep Nets",
            "url": "https://arxiv.org/abs/1234.5678",
            "authors": ["Ada", "Bob"],
            "year": 2021,
            "relevance": "baseline architecture",
        },
        {"title": "DOI Only", "doi": "10.1000/xyz", "authors": [], "year": None},
        {"title": "No Link", "url": None, "doi": None},
    ]
    blocks = plan_to_blocks(PLAN_CONTENT, None, "What is X?", papers=papers)

    toggles = {
        b["heading_2"]["rich_text"][0]["text"]["content"]: b
        for b in blocks
        if b["type"] == "heading_2" and b["heading_2"].get("is_toggleable")
    }
    assert "Sources" in toggles
    bullets = toggles["Sources"]["heading_2"]["children"]
    assert len(bullets) == 3

    # Direct URL becomes the title link; the note carries authors + relevance.
    first = bullets[0]["bulleted_list_item"]["rich_text"]
    assert first[0]["text"]["content"] == "Deep Nets"
    assert first[0]["text"]["link"] == {"url": "https://arxiv.org/abs/1234.5678"}
    assert "Ada et al." in first[1]["text"]["content"]
    assert "baseline architecture" in first[1]["text"]["content"]

    # A bare DOI is turned into a doi.org link.
    second = bullets[1]["bulleted_list_item"]["rich_text"]
    assert second[0]["text"]["link"] == {"url": "https://doi.org/10.1000/xyz"}

    # A paper with no URL/DOI renders as plain (unlinked) text.
    third = bullets[2]["bulleted_list_item"]["rich_text"]
    assert "link" not in third[0]["text"]


def test_data_items_reference_cited_paper():
    content = {
        "objective": "Study X",
        "data": [
            {"description": "MRI scans", "source": "Brain Imaging Study"},
            {"description": "survey responses", "source": None},
            "legacy plain string dataset",
        ],
    }
    papers = [
        {"title": "Brain Imaging Study", "url": "https://example.com/brain"},
    ]
    blocks = plan_to_blocks(content, None, "What is X?", papers=papers)

    data_toggle = next(
        b
        for b in blocks
        if b["type"] == "heading_2"
        and b["heading_2"]["rich_text"][0]["text"]["content"] == "Data"
    )
    bullets = data_toggle["heading_2"]["children"]
    assert len(bullets) == 3

    # Cited paper title is linked and appended after the description.
    first = bullets[0]["bulleted_list_item"]["rich_text"]
    assert first[0]["text"]["content"] == "MRI scans — "
    assert first[1]["text"]["content"] == "Brain Imaging Study"
    assert first[1]["text"]["link"] == {"url": "https://example.com/brain"}

    # No source -> plain description bullet.
    second = bullets[1]["bulleted_list_item"]["rich_text"]
    assert second[0]["text"]["content"] == "survey responses"
    assert "link" not in second[0]["text"]

    # Legacy string data still renders.
    third = bullets[2]["bulleted_list_item"]["rich_text"]
    assert third[0]["text"]["content"] == "legacy plain string dataset"


def test_method_items_reference_cited_paper():
    content = {
        "objective": "Study X",
        "methods": [
            {"description": "fine-tune a CNN", "source": "Deep Nets"},
            {"description": "manual annotation", "source": None},
            "legacy plain string method",
        ],
    }
    papers = [
        {"title": "Deep Nets", "url": "https://arxiv.org/abs/1234.5678"},
    ]
    blocks = plan_to_blocks(content, None, "What is X?", papers=papers)

    methods_toggle = next(
        b
        for b in blocks
        if b["type"] == "heading_2"
        and b["heading_2"]["rich_text"][0]["text"]["content"] == "Methods"
    )
    bullets = methods_toggle["heading_2"]["children"]
    assert len(bullets) == 3

    # Cited paper title is linked and appended after the description.
    first = bullets[0]["bulleted_list_item"]["rich_text"]
    assert first[0]["text"]["content"] == "fine-tune a CNN — "
    assert first[1]["text"]["content"] == "Deep Nets"
    assert first[1]["text"]["link"] == {"url": "https://arxiv.org/abs/1234.5678"}

    # No source -> plain description bullet.
    second = bullets[1]["bulleted_list_item"]["rich_text"]
    assert second[0]["text"]["content"] == "manual annotation"
    assert "link" not in second[0]["text"]

    # Legacy string method still renders.
    third = bullets[2]["bulleted_list_item"]["rich_text"]
    assert third[0]["text"]["content"] == "legacy plain string method"


def test_data_source_without_matching_paper_shows_unlinked_reference():
    content = {"data": [{"description": "field notes", "source": "Unlisted Paper"}]}
    blocks = plan_to_blocks(content, None, papers=[])
    data_toggle = next(
        b
        for b in blocks
        if b["type"] == "heading_2"
        and b["heading_2"]["rich_text"][0]["text"]["content"] == "Data"
    )
    spans = data_toggle["heading_2"]["children"][0]["bulleted_list_item"]["rich_text"]
    # The paper is still referenced by name, just without a hyperlink.
    assert spans[-1]["text"]["content"] == "Unlisted Paper"
    assert "link" not in spans[-1]["text"]


def test_plan_to_blocks_no_sources_without_papers():
    blocks = plan_to_blocks(PLAN_CONTENT, None, "What is X?")
    headings = [
        b["heading_2"]["rich_text"][0]["text"]["content"]
        for b in blocks
        if b["type"] == "heading_2"
    ]
    assert "Sources" not in headings


# --- tool selection / url parse --------------------------------------------


def test_find_create_page_tool_known_name():
    assert find_create_page_tool(["API-post-search", "API-post-page"]) == "API-post-page"


def test_find_create_page_tool_fallback():
    assert find_create_page_tool(["create_a_page", "search"]) == "create_a_page"


def test_find_create_page_tool_none():
    assert find_create_page_tool(["API-post-search"]) is None


def test_extract_page_url_nested():
    assert extract_page_url({"a": {"url": "https://notion.so/p"}}) == "https://notion.so/p"
    assert extract_page_url([{"x": 1}, {"url": "https://n/2"}]) == "https://n/2"
    assert extract_page_url({"nope": 1}) is None


# --- export service guard ---------------------------------------------------


class _FakeState:
    def __init__(self, values):
        self.values = values
        self.tasks = []


class _FakeExporter:
    def __init__(self):
        self.called = None

    async def create_page(self, title, blocks):
        self.called = (title, blocks)
        return "https://notion.so/exported"


def _fake_graph(values):
    state = _FakeState(values)

    class G:
        async def aget_state(self, config):
            return state

    return G()


def _plan(plan_id):
    now = datetime.now(UTC)
    return Plan(
        id=plan_id,
        question_id=uuid4(),
        content_json=PLAN_CONTENT,
        created_at=now,
        updated_at=now,
    )


@pytest.fixture
def _stub_repo(monkeypatch):
    async def _get_scores(_pid):
        return []

    async def _get_question(_qid):
        return Question(
            id=uuid4(), run_id=uuid4(), text="What is X?", created_at=datetime.now(UTC)
        )

    async def _get_papers(_qid):
        return []

    saved = {}

    async def _set_url(pid, url):
        saved["pid"] = pid
        saved["url"] = url
        return None

    monkeypatch.setattr(repository, "get_scores_for_plan", _get_scores)
    monkeypatch.setattr(repository, "get_question", _get_question)
    monkeypatch.setattr(repository, "get_papers_for_question", _get_papers)
    monkeypatch.setattr(repository, "set_plan_notion_url", _set_url)
    return saved


@pytest.mark.asyncio
async def test_export_plan_success(monkeypatch, _stub_repo):
    plan_id = uuid4()

    async def _get_plan(pid):
        return _plan(pid)

    monkeypatch.setattr(repository, "get_plan", _get_plan)

    graph = _fake_graph(
        {"status": "completed", "approved_plan_id": str(plan_id)}
    )
    exporter = _FakeExporter()
    result = await export_plan("thread-1", graph=graph, exporter=exporter)

    assert result["notion_url"] == "https://notion.so/exported"
    assert exporter.called is not None
    assert _stub_repo["url"] == "https://notion.so/exported"


@pytest.mark.asyncio
async def test_export_plan_not_approved():
    graph = _fake_graph({"status": "judging", "approved_plan_id": None})
    with pytest.raises(ExportNotApprovedError):
        await export_plan("t", graph=graph, exporter=_FakeExporter())


@pytest.mark.asyncio
async def test_export_plan_mismatch():
    approved = str(uuid4())
    graph = _fake_graph({"status": "completed", "approved_plan_id": approved})
    with pytest.raises(ExportPlanMismatchError):
        await export_plan(
            "t", graph=graph, exporter=_FakeExporter(), requested_plan_id=str(uuid4())
        )
