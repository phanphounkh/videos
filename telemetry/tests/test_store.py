from datetime import UTC, datetime

from app.schemas.event import EventIn
from app.store import MAX_AGE_S, MAX_FUTURE_S, event_time, to_row

DESKTOP = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)
PHONE = (
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_4 like Mac OS X) AppleWebKit/605.1.15 "
    "(KHTML, like Gecko) Version/17.4 Mobile/15E148 Safari/604.1"
)


def test_a_sane_timestamp_is_kept():
    assert event_time(1_000.0, now=1_100.0) == datetime.fromtimestamp(1_000.0, UTC)


def test_missing_future_and_ancient_timestamps_become_now():
    now = 10_000_000.0
    assert event_time(None, now) == datetime.fromtimestamp(now, UTC)
    assert event_time(now + MAX_FUTURE_S + 1, now) == datetime.fromtimestamp(now, UTC)
    assert event_time(now - MAX_AGE_S - 1, now) == datetime.fromtimestamp(now, UTC)


def test_user_agent_is_classified_and_not_stored():
    row = to_row(EventIn(event_type="product", name="x", user_agent=DESKTOP))
    assert (row.platform, row.browser.split()[0]) == ("desktop", "Chrome")
    phone = to_row(EventIn(event_type="product", name="x", user_agent=PHONE))
    assert phone.platform == "mobile" and "iOS" in phone.os
    assert not hasattr(row, "user_agent")


def test_properties_default_to_an_empty_object():
    assert to_row(EventIn(event_type="log", name="x")).properties == {}
