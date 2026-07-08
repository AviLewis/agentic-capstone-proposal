"""Unit tests for literature tools (mocked HTTP) and normalize/dedupe."""

from __future__ import annotations

import httpx
import pytest
import respx

from app.tools import arxiv, openalex, semantic_scholar
from app.tools.normalize import clean_doi, dedupe, normalize_title
from app.tools.schemas import NormalizedPaper

# --- normalize / dedupe -----------------------------------------------------


def test_normalize_title():
    assert normalize_title("Deep Learning: A Survey!") == "deep learning a survey"


def test_clean_doi_strips_prefixes():
    assert clean_doi("https://doi.org/10.1/ABC") == "10.1/abc"
    assert clean_doi("doi:10.2/x") == "10.2/x"
    assert clean_doi(None) is None


def test_dedupe_by_doi_and_title_prefers_abstract():
    papers = [
        NormalizedPaper(source="a", title="Same Paper", doi="10.1/x"),
        NormalizedPaper(source="b", title="same paper", doi="https://doi.org/10.1/X",
                        abstract="has abstract"),
        NormalizedPaper(source="c", title="Another"),
    ]
    out = dedupe(papers)
    assert len(out) == 2
    # The DOI-collision winner should be the one carrying an abstract.
    doi_paper = next(p for p in out if p.doi)
    assert doi_paper.abstract == "has abstract"


# --- OpenAlex ---------------------------------------------------------------


@pytest.mark.asyncio
@respx.mock
async def test_openalex_parses_and_reconstructs_abstract():
    route = respx.get("https://api.openalex.org/works").mock(
        return_value=httpx.Response(
            200,
            json={
                "results": [
                    {
                        "title": "A Study",
                        "publication_year": 2022,
                        "doi": "https://doi.org/10.1/abc",
                        "id": "https://openalex.org/W1",
                        "authorships": [
                            {"author": {"display_name": "Ada Lovelace"}},
                        ],
                        "primary_location": {"source": {"display_name": "Nature"}},
                        "abstract_inverted_index": {"Hello": [0], "world": [1]},
                    }
                ]
            },
        )
    )
    papers = await openalex.search("test", limit=5, mailto="me@example.com")
    assert route.called
    assert len(papers) == 1
    p = papers[0]
    assert p.title == "A Study"
    assert p.authors == ["Ada Lovelace"]
    assert p.venue == "Nature"
    assert p.abstract == "Hello world"


@pytest.mark.asyncio
@respx.mock
async def test_openalex_retries_then_raises_on_persistent_error():
    respx.get("https://api.openalex.org/works").mock(
        return_value=httpx.Response(500)
    )
    with pytest.raises(httpx.HTTPStatusError):
        await openalex.search("test", limit=1)


# --- arXiv ------------------------------------------------------------------

_ARXIV_FEED = """<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <entry>
    <id>http://arxiv.org/abs/1234.5678</id>
    <title>Transformer Models</title>
    <summary>We study transformers.</summary>
    <published>2021-05-01T00:00:00Z</published>
    <author><name>Grace Hopper</name></author>
  </entry>
</feed>"""


@pytest.mark.asyncio
@respx.mock
async def test_arxiv_parses_atom_feed():
    respx.get("https://export.arxiv.org/api/query").mock(
        return_value=httpx.Response(200, text=_ARXIV_FEED)
    )
    papers = await arxiv.search("transformers", limit=5)
    assert len(papers) == 1
    p = papers[0]
    assert p.title == "Transformer Models"
    assert p.authors == ["Grace Hopper"]
    assert p.year == 2021
    assert p.abstract == "We study transformers."


# --- Semantic Scholar -------------------------------------------------------


@pytest.mark.asyncio
@respx.mock
async def test_semantic_scholar_parses_results():
    respx.get("https://api.semanticscholar.org/graph/v1/paper/search").mock(
        return_value=httpx.Response(
            200,
            json={
                "data": [
                    {
                        "title": "Graph Networks",
                        "year": 2020,
                        "abstract": "About graphs.",
                        "venue": "ICML",
                        "externalIds": {"DOI": "10.9/xyz"},
                        "authors": [{"name": "Alan Turing"}],
                        "url": "https://s2.org/1",
                    }
                ]
            },
        )
    )
    papers = await semantic_scholar.search("graphs", limit=5)
    assert len(papers) == 1
    p = papers[0]
    assert p.doi == "10.9/xyz"
    assert p.venue == "ICML"
    assert p.authors == ["Alan Turing"]
