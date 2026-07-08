"""Literature search tools (OpenAlex, arXiv, Semantic Scholar) + aggregator."""

from app.tools import arxiv, openalex, semantic_scholar
from app.tools.normalize import clean_doi, dedupe, normalize_title
from app.tools.schemas import NormalizedPaper
from app.tools.search import search_all

__all__ = [
    "arxiv",
    "openalex",
    "semantic_scholar",
    "search_all",
    "dedupe",
    "normalize_title",
    "clean_doi",
    "NormalizedPaper",
]
