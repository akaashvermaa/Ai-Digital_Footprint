"""Realistic user scenarios used to check that the risk score behaves sensibly.

Each scenario states the level we EXPECT from the design of the formula (before looking at
the number), so the table doubles as documentation and as a regression test.
Network calls are replaced by fixed data so results are reproducible and offline.
"""
from unittest.mock import patch

from app.schemas import Breach, SiteResult

OVERSHARE = (
    "Hi I'm Rahul Sharma, call me at 9876543210, studying at IIT Kanpur. Born 12/05/2004. "
    "Going to Goa with family for 2 weeks, house will be empty! "
    "I leave the spare key under the doormat in case I forget mine."
)


def breaches(n, passwords=False):
    data = ["Email addresses", "Names"] + (["Passwords"] if passwords else [])
    return [Breach(name=f"Breach{i}", year="2022", data_exposed=data) for i in range(n)]


# name, text, number of sites the username is found on (None = no username), breaches (None = no email), expected level
SCENARIOS = [
    dict(name="Clean user: harmless post only", text="Loved the new movie. Learning React this week.",
         sites=None, breaches=None, level="Low"),
    dict(name="Careful user: 2 public accounts", text=None, sites=2, breaches=None, level="Low"),
    dict(name="Travel-only post (house empty)", text="Going to Goa for two weeks, the house will be empty!",
         sites=None, breaches=None, level="Medium"),
    dict(name="Email in a single, mild breach", text=None, sites=None, breaches=breaches(1), level="Medium"),
    dict(name="Username on 4 sites only", text=None, sites=4, breaches=None, level="Medium"),
    dict(name="Heavy breach with passwords leaked", text=None, sites=None, breaches=breaches(12, True), level="High"),
    dict(name="Over-sharing student: everything", text=OVERSHARE, sites=15, breaches=breaches(5, True), level="High"),
]


def run_scenario(client, sc: dict) -> dict:
    async def fake_scan(username):
        sites = [SiteResult(site=f"Site{i}", url=f"https://example.com/{i}", category="Social")
                 for i in range(sc["sites"])]
        return sites, 24, 0

    async def fake_breach(email):
        return sc["breaches"], "ok"

    payload = {}
    if sc["text"]:
        payload["text"] = sc["text"]
    if sc["sites"] is not None:
        payload["username"] = "demo_user"
    if sc["breaches"] is not None:
        payload["email"] = "demo@example.com"
    with patch("app.main.scan_username", fake_scan), patch("app.main.check_breaches", fake_breach):
        return client.post("/api/analyze", json=payload).json()
