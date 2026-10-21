"""Re-verify every site in app/data/sites.json.   Run:  python check_sites.py

Websites change: they start blocking bots, change URLs or answer "found" for everything.
For each site this tests:
  - a list of usernames that are very likely to exist  -> at least one must be FOUND
  - two made-up usernames                               -> both must be NOT found
A site that fails either test would give wrong results, so remove it from sites.json.
Run this before a demo or presentation.
"""
import asyncio

import httpx

from app.services.username_checker import HEADERS, SITES, check_site

LIKELY_REAL = ["torvalds", "john", "google", "admin", "sindresorhus", "guido"]
FAKES = ["zq8xk2vnotreal77", "qwkjzxv9plmn"]


async def test_site(client: httpx.AsyncClient, site: dict) -> dict:
    real = [await check_site(client, site, u) for u in LIKELY_REAL]
    fake = [await check_site(client, site, u) for u in FAKES]
    if all(r is None for r in real + fake):
        verdict = "BLOCKED"          # the site refuses automated requests
    elif any(f for f in fake):
        verdict = "FALSE-POSITIVE"   # says a made-up name exists
    elif not any(r for r in real):
        verdict = "NEVER-FOUND"      # cannot find anything: URL or check is wrong
    else:
        verdict = "OK"
    return {"name": site["name"], "verdict": verdict}


async def main():
    async with httpx.AsyncClient(headers=HEADERS, timeout=10, follow_redirects=True) as client:
        results = await asyncio.gather(*(test_site(client, s) for s in SITES))

    bad = [r for r in results if r["verdict"] != "OK"]
    print(f"{len(results) - len(bad)} of {len(results)} sites OK")
    for r in bad:
        print(f"  PROBLEM  {r['name']}: {r['verdict']}")
    if bad:
        print("\nRe-run once to rule out a temporary glitch; if it repeats, remove the site from app/data/sites.json.")


if __name__ == "__main__":
    asyncio.run(main())
