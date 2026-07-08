"""OpenAlex works search (free, no key; polite pool via contact email)."""

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

OPENALEX_URL = "https://api.openalex.org/works"


def _reconstruct_abstract(inverted_index: dict | None) -> str | None:
    """Rebuild plain text from OpenAlex's abstract_inverted_index."""
    if not inverted_index:
        return None
    positions: list[tuple[int, str]] = []
    for word, idxs in inverted_index.items():
        for i in idxs:
            positions.append((i, word))
    if not positions:
        return None
    positions.sort(key=lambda p: p[0])
    return " ".join(word for _, word in positions)


def _parse(work: dict) -> NormalizedPaper:
    authorships = work.get("authorships") or []
    authors = [
        a.get("author", {}).get("display_name")
        for a in authorships
        if a.get("author", {}).get("display_name")
    ]
    venue = None
    primary = work.get("primary_location") or {}
    source = primary.get("source") or {}
    if source:
        venue = source.get("display_name")
    return NormalizedPaper(
        source="openalex",
        title=work.get("title") or work.get("display_name") or "(untitled)",
        authors=authors,
        year=work.get("publication_year"),
        venue=venue,
        doi=work.get("doi"),
        url=work.get("id"),
        abstract=_reconstruct_abstract(work.get("abstract_inverted_index")),
    )


@retry(
    reraise=True,
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=0.5, max=8),
    retry=retry_if_exception_type((httpx.TransportError, httpx.HTTPStatusError)),
)
async def _fetch(client: httpx.AsyncClient, params: dict) -> dict:
    resp = await client.get(OPENALEX_URL, params=params)
    resp.raise_for_status()
    return resp.json()


async def search(
    query: str,
    limit: int = 10,
    *,
    mailto: str | None = None,
    timeout: float = 15.0,
    client: httpx.AsyncClient | None = None,
) -> list[NormalizedPaper]:
    params: dict[str, object] = {"search": query, "per_page": limit}
    if mailto:
        params["mailto"] = mailto

    owns_client = client is None
    client = client or httpx.AsyncClient(timeout=timeout)
    try:
        data = await _fetch(client, params)
    finally:
        if owns_client:
            await client.aclose()

    results = data.get("results") or []
    return [_parse(w) for w in results[:limit]]
