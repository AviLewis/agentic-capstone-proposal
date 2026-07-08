"""OpenAI chat-model factory and structured-output helper.

Agents call :func:`ainvoke_structured` to get a validated Pydantic object plus a
:class:`Usage` record (tokens + estimated USD cost). The helper is easy to stub
in tests: agent functions accept an ``invoke`` callable that defaults to it.
"""

from __future__ import annotations

from typing import TypeVar

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from pydantic import BaseModel

from app.config import get_settings
from app.logging import get_logger

log = get_logger(__name__)

T = TypeVar("T", bound=BaseModel)

# (input, output) USD per 1M tokens. Fallback used for unknown models.
_PRICING: dict[str, tuple[float, float]] = {
    "gpt-4o": (2.50, 10.00),
    "gpt-4o-mini": (0.15, 0.60),
    "gpt-4.1": (2.00, 8.00),
    "gpt-4.1-mini": (0.40, 1.60),
}
_DEFAULT_PRICE = (2.50, 10.00)


class Usage(BaseModel):
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    cost_usd: float = 0.0

    def __add__(self, other: Usage) -> Usage:
        return Usage(
            input_tokens=self.input_tokens + other.input_tokens,
            output_tokens=self.output_tokens + other.output_tokens,
            total_tokens=self.total_tokens + other.total_tokens,
            cost_usd=self.cost_usd + other.cost_usd,
        )


def estimate_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    price_in, price_out = _PRICING.get(model, _DEFAULT_PRICE)
    return (input_tokens * price_in + output_tokens * price_out) / 1_000_000


def get_chat_model(temperature: float = 0.7, model: str | None = None) -> ChatOpenAI:
    settings = get_settings()
    return ChatOpenAI(
        model=model or settings.OPENAI_MODEL,
        temperature=temperature,
        api_key=settings.OPENAI_API_KEY,
        timeout=60,
        max_retries=2,
    )


def _usage_from_raw(raw, model: str) -> Usage:
    meta = getattr(raw, "usage_metadata", None) or {}
    input_tokens = int(meta.get("input_tokens", 0))
    output_tokens = int(meta.get("output_tokens", 0))
    total = int(meta.get("total_tokens", input_tokens + output_tokens))
    return Usage(
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        total_tokens=total,
        cost_usd=estimate_cost(model, input_tokens, output_tokens),
    )


async def ainvoke_structured(
    schema: type[T],
    system: str,
    human: str,
    *,
    temperature: float = 0.7,
    model: str | None = None,
) -> tuple[T, Usage]:
    """Invoke the chat model and parse the response into ``schema``.

    Returns the parsed object and a :class:`Usage` record. Raises ``ValueError``
    if the model output could not be parsed into the schema.
    """
    settings = get_settings()
    model_name = model or settings.OPENAI_MODEL
    llm = get_chat_model(temperature=temperature, model=model_name)
    structured = llm.with_structured_output(schema, include_raw=True)

    result = await structured.ainvoke(
        [SystemMessage(content=system), HumanMessage(content=human)]
    )
    parsed = result.get("parsed")
    if parsed is None:
        raise ValueError(
            f"Failed to parse structured output for {schema.__name__}: "
            f"{result.get('parsing_error')}"
        )
    return parsed, _usage_from_raw(result.get("raw"), model_name)
