"""Robots.txt + host allowlist checks."""

from __future__ import annotations

from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser

_CACHE: dict[str, RobotFileParser] = {}

DEMO_ALLOW = {"books.toscrape.com"}


def host_allowed(url: str, allowed_hosts: list[str] | None) -> bool:
    host = urlparse(url).hostname or ""
    if allowed_hosts:
        return host in allowed_hosts
    return True


def robots_allowed(url: str, user_agent: str = "WaggleBot") -> bool:
    parsed = urlparse(url)
    host = parsed.hostname or ""
    if host in DEMO_ALLOW:
        return True
    origin = f"{parsed.scheme}://{host}"
    robots_url = f"{origin}/robots.txt"
    rp = _CACHE.get(origin)
    if rp is None:
        rp = RobotFileParser()
        rp.set_url(robots_url)
        try:
            rp.read()
        except Exception:
            return True
        _CACHE[origin] = rp
    try:
        return rp.can_fetch(user_agent, url)
    except Exception:
        return True
