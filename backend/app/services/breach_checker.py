"""Checks if an email appeared in known data breaches.

Uses the free XposedOrNot API (https://xposedornot.com), no API key needed.
Returns status "unavailable" instead of failing if the service is down.
"""
import re

import httpx

from app.schemas import Breach

API_URL = "https://api.xposedornot.com/v1/breach-analytics"
MAX_BREACHES = 1000
EMAIL_RE = re.compile(r"^[\w.+-]+@[\w-]+\.[\w.-]+$")


def is_valid_email(email: str) -> bool:
    return bool(EMAIL_RE.match(email))


async def check_breaches(email: str) -> tuple[list[Breach], str]:
    """Returns (breaches, status) where status is "ok" or "unavailable"."""
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            r = await client.get(API_URL, params={"email": email})
            if r.status_code == 404:      # the service answers 404 when an email is in no breach
                return [], "ok"
            r.raise_for_status()
            data = r.json()
    except (httpx.HTTPError, ValueError):
        return [], "unavailable"

    details = (data.get("ExposedBreaches") or {}).get("breaches_details") or []
    breaches = [
        Breach(
            name=b.get("breach", "Unknown"),
            year=str(b.get("xposed_date") or "") or None,
            data_exposed=[d.strip() for d in (b.get("xposed_data") or "").split(";") if d.strip()],
        )
        for b in details
    ]
    # Most recent first; keep the list within the response-size limit
    breaches.sort(key=lambda b: b.year or "", reverse=True)
    return breaches[:MAX_BREACHES], "ok"
