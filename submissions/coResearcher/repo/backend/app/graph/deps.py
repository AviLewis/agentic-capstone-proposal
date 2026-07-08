"""Injectable dependencies for graph nodes.

Nodes call ``deps.invoke`` (LLM structured output) and ``deps.search`` (paper
search) through this module so tests can monkeypatch them without touching the
graph wiring or passing non-serializable callables through LangGraph config.
"""

from __future__ import annotations

from app.llm import ainvoke_structured
from app.tools.search import search_all

# Overridable at runtime (e.g. in tests via monkeypatch).
invoke = ainvoke_structured
search = search_all
