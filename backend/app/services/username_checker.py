"""Checks on which websites a username exists (like the OSINT tool Sherlock).

For every site in data/sites.json we request the profile URL (or a public API,
the "probe" URL) and decide from the HTTP response:
  status       -> HTTP 200 means the profile exists, 404 means it doesn't
  absent_text  -> exists unless the page contains a "not found" marker
  present_text -> exists only if the page contains a marker
All sites are checked at the same time with asyncio, so a scan takes seconds (a site silent for 5s counts as "could not check").
"""
import asyncio
import json
import re
from pathlib import Path

import httpx

from app.schemas import SiteResult

SITES = json.loads((Path(__file__).resolve().parent.parent / "data" / "sites.json").read_text())
USERNAME_RE = re.compile(r"^[A-Za-z0-9._-]{2,40}$")
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/130.0 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9",
}


def is_valid_username(username: str) -> bool:
    return bool(USERNAME_RE.match(username))


async def check_site(client: httpx.AsyncClient, site: dict, username: str) -> bool | None:
    """True = found, False = not found, None = couldn't tell (blocked / error)."""
    url = site.get("probe", site["url"]).format(username)
    try:
        r = await client.get(url)
    except httpx.HTTPError:
        return None

    if r.status_code in (403, 429) or r.status_code >= 500:
        return None   # blocked or rate-limited: unknown, don't count it
    if site["check"] == "status":
        return r.status_code == 200
    if r.status_code != 200:
        return False
    if site["check"] == "absent_text":
        return site["absent_text"] not in r.text
    if site["check"] == "present_text":
        return site["present_text"] in r.text
    return None


async def scan_username(username: str) -> tuple[list[SiteResult], int, int]:
    """Returns (sites where the username was found, sites checked, sites that could not be checked)."""
    async with httpx.AsyncClient(headers=HEADERS, timeout=5, follow_redirects=True) as client:
        results = await asyncio.gather(*(check_site(client, s, username) for s in SITES))

    found = [
        SiteResult(site=s["name"], url=s["url"].format(username), category=s["category"])
        for s, ok in zip(SITES, results) if ok
    ]
    unknown = sum(1 for ok in results if ok is None)
    return found, len(results) - unknown, unknown
