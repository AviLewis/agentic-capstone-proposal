"""Shared literal types used across the DB and graph layers.

Kept dependency-free to avoid import cycles between ``app.db`` and ``app.graph``.
"""

from __future__ import annotations

from typing import Literal

RunStatus = Literal[
    "pending",
    "ideating",
    "awaiting_question_selection",
    "reviewing_literature",
    "designing_methodology",
    "planning",
    "judging",
    "awaiting_plan_approval",
    "completed",
    "capped",
    "error",
]

PaperSource = Literal["openalex", "arxiv", "semantic_scholar"]
