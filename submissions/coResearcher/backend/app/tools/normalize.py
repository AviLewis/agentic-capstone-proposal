"""Normalization + dedupe helpers for literature results."""

from __future__ import annotations

import re

from app.tools.schemas import NormalizedPaper

_NON_ALNUM = re.compile(r"[^a-z0-9]+")


def normalize_title(title: str | None) -> str:
    return _NON_ALNUM.sub(" ", (title or "").lower()).strip()


def clean_doi(doi: str | None) -> str | None:
    if not doi:
        return None
    d = doi.strip().lower()
    for prefix in ("https://doi.org/", "http://doi.org/", "doi:"):
        if d.startswith(prefix):
            d = d[len(prefix) :]
    return d or None


def _dedupe_key(paper: NormalizedPaper) -> str:
    doi = clean_doi(paper.doi)
    if doi:
        return f"doi:{doi}"
    return f"title:{normalize_title(paper.title)}"


def dedupe(papers: list[NormalizedPaper]) -> list[NormalizedPaper]:
    """Drop duplicate papers, keyed by DOI then normalized title.

    When two entries collide, prefer the one carrying an abstract so we retain
    the richest record.
    """
    best: dict[str, NormalizedPaper] = {}
    order: list[str] = []
    for paper in papers:
        key = _dedupe_key(paper)
        if not key or key in ("doi:", "title:"):
            continue
        existing = best.get(key)
        if existing is None:
            best[key] = paper
            order.append(key)
        elif not existing.abstract and paper.abstract:
            best[key] = paper  # upgrade to the record with an abstract
    return [best[k] for k in order]
