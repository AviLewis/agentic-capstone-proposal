"""LLM-facing agents: ideator, literature review, methodology, plan, judge.

Each agent is a set of pure async functions that take domain inputs plus an
``invoke`` callable (defaulting to :func:`app.llm.ainvoke_structured`) and return
structured results + token/cost :class:`~app.llm.Usage`. Injecting ``invoke``
makes the agents trivially testable with a stubbed LLM.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any, TypeVar

from pydantic import BaseModel

from app.llm import Usage

T = TypeVar("T", bound=BaseModel)

# Signature of app.llm.ainvoke_structured.
StructuredInvoker = Callable[..., Awaitable[tuple[Any, Usage]]]

__all__ = ["StructuredInvoker", "Usage", "T"]
