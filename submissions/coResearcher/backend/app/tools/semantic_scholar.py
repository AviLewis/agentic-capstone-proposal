"""Semantic Scholar Graph API search (free; optional API key for higher limits)."""

from __future__ import annotations

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

S2_URL = "https://api.semanticscholar.org/graph/v1/paper/search"
_FIELDS = "title,year,abstract,venue,externalIds,authors,url"


def _parse(paper: dict) -> NormalizedPaper:
    authors = [a.get("name") for a in (paper.get("authors") or []) if a.get("name")]
    doi = (paper.get("externalIds") or {}).get("DOI")
    return NormalizedPaper(
        source="semantic_scholar",
        title=paper.get("title") or "(untitled)",
        authors=authors,
        year=paper.get("year"),
        venue=paper.get("venue") or None,
        doi=doi,
        url=paper.get("url"),
        abstract=paper.get("abstract"),
    )


@retry(
    reraise=True,
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=0.5, max=8),
    retry=retry_if_exception_type((httpx.TransportError, httpx.HTTPStatusError)),
)
async def _fetch(client: httpx.AsyncClient, params: dict, headers: dict) -> dict:
    resp = await client.get(S2_URL, params=params, headers=headers)
    resp.raise_for_status()
    return resp.json()


async def search(
    query: str,
    limit: int = 10,
    *,
    api_key: str | None = None,
    timeout: float = 15.0,
    client: httpx.AsyncClient | None = None,
) -> list[NormalizedPaper]:
    params = {"query": query, "limit": limit, "fields": _FIELDS}
    headers = {"x-api-key": api_key} if api_key else {}

    owns_client = client is None
    client = client or httpx.AsyncClient(timeout=timeout)
    try:
        data = await _fetch(client, params, headers)
    finally:
        if owns_client:
            await client.aclose()

    results = data.get("data") or []
    return [_parse(p) for p in results[:limit]]
