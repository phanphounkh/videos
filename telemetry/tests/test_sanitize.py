import math

import pytest

from app.sanitize import TooDeep, clean, clean_str, parse_json, scrub


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("Failed for jane.doe+test@example.co.uk now", "Failed for [email] now"),
        ("a@b.io and c@d.org", "[email] and [email]"),
        ("Authorization: Bearer abcdef1234567890xyz", "Authorization: [token]"),
        ("jwt eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjMifQ.sig_nature-1 leaked", "jwt [token] leaked"),
        ("nothing to hide: 12345 /projects/:id", "nothing to hide: 12345 /projects/:id"),
    ],
)
def test_scrub(raw, expected):
    assert scrub(raw) == expected


def test_scrub_happens_before_truncation():
    cleaned = clean_str("x" * 290 + " person@example.com", max_chars=300)
    assert cleaned == "x" * 290 + " [email]"


def test_clean_removes_nul_and_surrogates_everywhere():
    cleaned = clean({"a\x00": "b\x00c", "n": [{"s": "ok\ud800"}], "i": 3, "t": True, "z": None})
    assert cleaned["a"] == "bc"
    assert cleaned["n"][0]["s"].startswith("ok")
    cleaned["n"][0]["s"].encode("utf-8")  # must be encodable: Postgres refuses anything else
    assert cleaned["i"] == 3 and cleaned["t"] is True and cleaned["z"] is None


def test_clean_cleans_dict_keys_too():
    assert list(clean({"who@example.com": 1})) == ["[email]"]


def test_clean_refuses_hostile_nesting():
    nested: dict = {}
    cursor = nested
    for _ in range(20):
        cursor["x"] = {}
        cursor = cursor["x"]
    with pytest.raises(TooDeep):
        clean(nested, max_depth=8)


def test_parse_json_maps_nan_and_overflow_to_null():
    parsed = parse_json('{"a": NaN, "b": Infinity, "c": 1e999, "d": 2.5}')
    assert parsed == {"a": None, "b": None, "c": None, "d": 2.5}
    assert not any(isinstance(v, float) and math.isnan(v) for v in parsed.values())
