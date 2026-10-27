"""Measuring calls to AI providers (LLM, text-to-speech, image).

    async with track_ai("llm.script", provider="gemini", user_id=uid, project_id=pid) as call:
        result = await provider.generate_script(...)
        call.output_units = estimated_output_tokens

records latency, success or failure (with the provider's error code), units used,
and an estimated cost. Usage is exact when a provider reports it (via
`report_usage`) and estimated from text length otherwise; the event says which.

Cost: only computed when TELEMETRY_PRICES has a rate for "<service>.<provider>".
With no rate the cost is None - an unknown price is never presented as zero.
"""

import contextvars
import json
import time
import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from functools import lru_cache
from typing import Any

from app.core.config import get_settings
from app.core.exceptions import AppError
from app.services.telemetry import events
from app.services.telemetry.recorder import record

# Providers call report_usage() from inside their request; track_ai reads it back.
_usage: contextvars.ContextVar[dict[str, float] | None] = contextvars.ContextVar(
    "telemetry_usage", default=None
)


def report_usage(*, input_units: float | None = None, output_units: float | None = None) -> None:
    """Called by a provider with the exact usage its API reported."""
    bag = _usage.get()
    if bag is None:
        return
    if input_units is not None:
        bag["input"] = bag.get("input", 0) + float(input_units)
    if output_units is not None:
        bag["output"] = bag.get("output", 0) + float(output_units)


@lru_cache
def _prices_from(raw: str) -> dict[str, dict[str, float]]:
    if not raw.strip():
        return {}
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    if not isinstance(parsed, dict):
        return {}
    return {
        key: {k: float(v) for k, v in rates.items() if isinstance(v, int | float)}
        for key, rates in parsed.items()
        if isinstance(rates, dict)
    }


def estimate_cost(
    service: str,
    provider: str,
    *,
    input_units: float | None,
    output_units: float | None,
    prices: dict[str, dict[str, float]] | None = None,
) -> float | None:
    """USD for one call, or None when no price is configured for it."""
    table = prices if prices is not None else _prices_from(get_settings().telemetry_prices)
    rates = table.get(f"{service.split('.')[0]}.{provider}")
    if not rates:
        return None
    cost = rates.get("per_call", 0.0)
    cost += (input_units or 0) / 1_000_000 * rates.get("input_per_1m", 0.0)
    cost += (output_units or 0) / 1_000_000 * rates.get("output_per_1m", 0.0)
    # TTS is priced per character of input text.
    cost += (input_units or 0) / 1_000_000 * rates.get("per_1m_chars", 0.0)
    return round(cost, 6)


@dataclass(slots=True)
class AiCall:
    """What a tracked call knows; the caller fills in what only it can know."""

    name: str
    provider: str
    model: str | None = None
    user_id: uuid.UUID | None = None
    project_id: uuid.UUID | None = None
    unit: str = "tokens"
    # Fallback figures used when the provider reported nothing (character counts
    # converted to tokens for text models).
    input_units: float | None = None
    output_units: float | None = None
    props: dict[str, Any] = field(default_factory=dict)


CHARS_PER_TOKEN = 4


@asynccontextmanager
async def track_ai(
    name: str,
    *,
    provider: str,
    model: str | None = None,
    user_id: uuid.UUID | None = None,
    project_id: uuid.UUID | None = None,
    unit: str = "tokens",
    input_units: float | None = None,
    **props: Any,
) -> AsyncIterator[AiCall]:
    call = AiCall(
        name=name,
        provider=provider,
        model=model,
        user_id=user_id,
        project_id=project_id,
        unit=unit,
        input_units=input_units,
        props=dict(props),
    )
    bag: dict[str, float] = {}
    token = _usage.set(bag)
    started = time.perf_counter()
    error_code: str | None = None
    try:
        yield call
    except BaseException as exc:
        error_code = exc.code if isinstance(exc, AppError) else type(exc).__name__
        raise
    finally:
        _usage.reset(token)
        try:
            _emit(call, bag, (time.perf_counter() - started) * 1000, error_code)
            await _count(call, bag, error_code)
        except Exception:  # noqa: BLE001 - measuring must not break the call
            pass


async def _count(call: AiCall, bag: dict[str, float], error_code: str | None) -> None:
    """Adds a successful call to the person's monthly usage (what limits are checked against)."""
    if error_code or call.user_id is None:
        return
    from app.services import usage

    await usage.add(call.user_id, "ai_calls")
    if call.unit == "tokens":
        total = (bag.get("input", call.input_units) or 0) + (
            bag.get("output", call.output_units) or 0
        )
        await usage.add(call.user_id, "tokens", round(total))


def _emit(call: AiCall, bag: dict[str, float], duration_ms: float, error_code: str | None) -> None:
    reported = bool(bag)
    input_units = bag.get("input", call.input_units)
    output_units = bag.get("output", call.output_units)
    cost = (
        None
        if error_code
        else estimate_cost(
            call.name, call.provider, input_units=input_units, output_units=output_units
        )
    )
    props: dict[str, Any] = {
        "name": call.name,
        "unit": call.unit,
        # True when the numbers are a length-based estimate, not the provider's own.
        "estimated": not reported,
    }
    if call.project_id:
        props["project_id"] = str(call.project_id)
    if error_code:
        props["error_code"] = str(error_code)[:64]
    props.update(events.clean_props(call.props))
    # Tokens are only meaningful for text models; other units stay in properties.
    tokens = call.unit == "tokens"
    record(
        events.Event(
            name=call.name,
            event_type="llm_usage",
            level="error" if error_code else "info",
            outcome="error" if error_code else "ok",
            duration_ms=round(duration_ms),
            user_id=str(call.user_id) if call.user_id else None,
            provider=call.provider,
            model=call.model,
            prompt_tokens=round(input_units) if tokens and input_units is not None else None,
            completion_tokens=round(output_units) if tokens and output_units is not None else None,
            total_tokens=(
                round((input_units or 0) + (output_units or 0))
                if tokens and (input_units is not None or output_units is not None)
                else None
            ),
            cost_usd=cost,
            properties={
                **props,
                **({} if tokens else {"input_units": input_units, "output_units": output_units}),
            },
        )
    )
