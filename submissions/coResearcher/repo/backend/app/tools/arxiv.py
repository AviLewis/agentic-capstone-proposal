"""arXiv Atom API search (free, no key)."""

from __future__ import annotations

from xml.etree import ElementTree as ET

import httpx
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from app.logging import get_logger
from app.tools.schemas import NormalizedPaper

log = get_logger(__name__)

ARXIV_URL = "https://export.arxiv.org/api/query"

_ATOM = "{http://www.w3.org/2005/Atom}"
_ARXIV = "{http://arxiv.org/schemas/atom}"


def _text(node: ET.Element | None) -> str | None:
    if node is None or node.text is None:
        return None
    return " ".join(node.text.split())


def _parse_entry(entry: ET.Element) -> NormalizedPaper:
    authors = [
        _text(a.find(f"{_ATOM}name"))
        for a in entry.findall(f"{_ATOM}author")
        if _text(a.find(f"{_ATOM}name"))
    ]
    published = _text(entry.find(f"{_ATOM}published"))
    year = int(published[:4]) if published and published[:4].isdigit() else None
    doi = _text(entry.find(f"{_ARXIV}doi"))
    return NormalizedPaper(
        source="arxiv",
        title=_text(entry.find(f"{_ATOM}title")) or "(untitled)",
        authors=[a for a in authors if a],
        year=year,
        venue="arXiv",
        doi=doi,
        url=_text(entry.find(f"{_ATOM}id")),
        abstract=_text(entry.find(f"{_ATOM}summary")),
    )


@retry(
    reraise=True,
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=0.5, max=8),
    retry=retry_if_exception_type((httpx.TransportError, httpx.HTTPStatusError)),
)
async def _fetch(client: httpx.AsyncClient, params: dict) -> str:
    resp = await client.get(ARXIV_URL, params=params)
    resp.raise_for_status()
    return resp.text


async def search(
    query: str,
    limit: int = 10,
    *,
    timeout: float = 15.0,
    client: httpx.AsyncClient | None = None,
) -> list[NormalizedPaper]:
    params = {"search_query": f"all:{query}", "start": 0, "max_results": limit}

    owns_client = client is None
    client = client or httpx.AsyncClient(timeout=timeout, follow_redirects=True)
    try:
        xml = await _fetch(client, params)
    finally:
        if owns_client:
            await client.aclose()

    root = ET.fromstring(xml)
    entries = root.findall(f"{_ATOM}entry")
    return [_parse_entry(e) for e in entries[:limit]]
