from user_agents import parse as _parse

# Parsing cost grows with length and runs on the event loop: a padded header must not
# buy a client a long stall.
_MAX_UA = 512


def classify_client(user_agent: str | None) -> dict:
    """(platform, os, browser) from a raw User-Agent. The raw string is never stored."""
    if not user_agent:
        return {"platform": None, "os": None, "browser": None}
    ua = _parse(user_agent[:_MAX_UA])
    if ua.is_bot:
        platform = "bot"
    elif ua.is_tablet:
        platform = "tablet"
    elif ua.is_mobile:
        platform = "mobile"
    elif ua.is_pc:
        platform = "desktop"
    else:
        platform = "other"
    os_name = " ".join(p for p in (ua.os.family, ua.os.version_string) if p) or None
    browser = " ".join(p for p in (ua.browser.family, ua.browser.version_string) if p) or None
    return {"platform": platform, "os": os_name, "browser": browser}
