"""Makes JSON from outside storable, and keeps personal data out of it.

Free text reaches this service that nothing upstream filtered: exception messages,
log fields, browser error text. Postgres refuses three things such text can hold: NUL,
a lone UTF-16 surrogate, and NaN/Infinity. Any one fails a whole INSERT, so they are
mapped to something storable here.

Separately, `scrub` removes what telemetry must never hold: email addresses and
credentials. Code sometimes puts a user's email or a token into an error message; this
is the authoritative place that stops it, whatever the sender did.
"""

import json
import math
import re


class TooDeep(ValueError):
    """clean() met nesting deeper than its max_depth."""


_EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)*\.[A-Za-z]{2,}")
_SECRET = re.compile(
    r"(?:eyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]*|Bearer\s+[A-Za-z0-9._~+/=-]{8,})"
)


def scrub(text: str) -> str:
    """Emails become [email]; JWTs and `Bearer ...` credentials become [token]."""
    return _SECRET.sub("[token]", _EMAIL.sub("[email]", text))


def _finite_or_none(literal: str) -> float | None:
    value = float(literal)
    return value if math.isfinite(value) else None


def parse_json(raw: str | bytes):
    """json.loads with NaN/Infinity (and overflowing literals like 1e999) as null."""
    return json.loads(raw, parse_constant=lambda _: None, parse_float=_finite_or_none)


def clean_str(value: str, max_chars: int | None = None) -> str:
    # Scrub BEFORE truncating, so a cut can never split an address in half.
    value = scrub(value)
    if max_chars is not None and len(value) > max_chars:
        value = value[:max_chars]
    if "\x00" in value:
        value = value.replace("\x00", "")
    try:
        value.encode("utf-8")
    except UnicodeEncodeError:
        value = value.encode("utf-8", "replace").decode("utf-8")
    return value


def clean(value, max_chars: int | None = None, max_depth: int | None = None, _depth: int = 0):
    """`value` with every string (dict keys included) cleaned. Raises TooDeep past max_depth."""
    if max_depth is not None and _depth > max_depth:
        raise TooDeep
    if isinstance(value, str):
        return clean_str(value, max_chars)
    if isinstance(value, dict):
        return {
            clean_str(str(k), max_chars): clean(v, max_chars, max_depth, _depth + 1)
            for k, v in value.items()
        }
    if isinstance(value, list):
        return [clean(v, max_chars, max_depth, _depth + 1) for v in value]
    return value
