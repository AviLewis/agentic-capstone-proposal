"""Multi-source literature search aggregator.

Queries OpenAlex, arXiv, and Semantic Scholar concurrently, then normalizes and
dedupes the merged results. A failure in any single source is logged and skipped
so the search degrades gracefully.
"""

from __future__ import annotations

import asyncio

import httpx

from app.config import get_settings
from app.logging import get_logger
from app.tools import arxiv, openalex, semantic_scholar
from app.tools.normalize import dedupe
from app.tools.schemas import NormalizedPaper

log = get_logger(__name__)

# Every source the aggregator knows how to query. DEFAULT_SOURCES is the subset
# used when a run doesn't specify its own selection.
ALLOWED_SOURCES = ("openalex", "arxiv", "semantic_scholar")
DEFAULT_SOURCES = ("openalex", "arxiv")


def describe_source_error(exc: BaseException) -> str:
    """Turn a raw search exception into a short, user-facing reason."""
    if isinstance(exc, httpx.HTTPStatusError):
        code = exc.response.status_code
        if code == 429:
            return "rate limited (HTTP 429)"
        return f"HTTP {code}"
    if isinstance(exc, httpx.TimeoutException):
        return "timed out"
    if isinstance(exc, httpx.TransportError):
        return "network error"
    return exc.__class__.__name__


async def search_all(
    query: str,
    limit_per_source: int = 8,
    *,
    sources: tuple[str, ...] = DEFAULT_SOURCES,
    mailto: str | None = None,
    s2_api_key: str | None = None,
    failures: dict[str, str] | None = None,
) -> list[NormalizedPaper]:
    """Query the selected sources concurrently and merge the results.

    A failure in any single source is logged and skipped so the search degrades
    gracefully. When a ``failures`` dict is supplied, each failed source is
    recorded there (source name -> short reason) so callers can surface the
    problem to the user instead of silently dropping the source.
    """
    settings = None
    if mailto is None or s2_api_key is None:
        try:
            settings = get_settings()
        except Exception:  # noqa: BLE001 - settings optional for search
            settings = None
    if settings is not None:
        mailto = mailto or settings.CONTACT_EMAIL
        s2_api_key = s2_api_key or settings.SEMANTIC_SCHOLAR_API_KEY

    coros = []
    used_sources: list[str] = []
    if "openalex" in sources:
        coros.append(openalex.search(query, limit_per_source, mailto=mailto))
        used_sources.append("openalex")
    if "arxiv" in sources:
        coros.append(arxiv.search(query, limit_per_source))
        used_sources.append("arxiv")
    if "semantic_scholar" in sources:
        coros.append(semantic_scholar.search(query, limit_per_source, api_key=s2_api_key))
        used_sources.append("semantic_scholar")

    results = await asyncio.gather(*coros, return_exceptions=True)

    papers: list[NormalizedPaper] = []
    for name, result in zip(used_sources, results, strict=True):
        if isinstance(result, BaseException):
            log.warning("search_source_failed", source=name, error=str(result))
            if failures is not None:
                failures[name] = describe_source_error(result)
            continue
        papers.extend(result)

    merged = dedupe(papers)
    log.info("search_all", query=query, found=len(merged), sources=used_sources)
    return merged
