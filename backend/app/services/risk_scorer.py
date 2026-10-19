"""Combines all checks into one 0-100 risk score, and keeps the working.

Every category score is the SUM of a list of contributions, and every contribution
comes from an actual finding, so any point can be traced back to something found.

Category weights (re-normalised over the checks that were actually run):
    personal info 40%, data breaches 30%, risky content 15%, account spread 15%

Personal info:  per finding TYPE, the first finding earns full points
                (high 25 / medium 12 / low 5), every further one of the same type earns
                30% of that, and a type can never earn more than 2x its base. Eight cities
                therefore cannot swamp a single phone number.
Breaches:       1 breach 40, 2 -> 55, 3 -> 65, then +2 each up to 85;
                +15 if passwords leaked, +10 if phone/address/DOB/cards/IDs leaked.
Risky content:  confidence of the riskiest post x 100, +5 for each further risky post.
Accounts:       8 points per site where the username exists.
Levels:         0-30 Low, 31-60 Medium, 61-100 High.
"""
from collections import defaultdict

from app.schemas import Breach, CategoryScore, Contribution, Finding

WEIGHTS = {"pii": 0.40, "breach": 0.30, "content": 0.15, "accounts": 0.15}
LABELS = {
    "pii": "Personal info exposure",
    "breach": "Data breaches",
    "content": "Risky content",
    "accounts": "Account spread",
}
SEVERITY_POINTS = {"high": 25, "medium": 12, "low": 5}
SEVERITY_RANK = {"high": 3, "medium": 2, "low": 1}
REPEAT_FACTOR = 0.3      # each extra finding of the same type earns 30% of the base
TYPE_CAP_MULTIPLE = 2    # a type can earn at most 2x its base points
POINTS_PER_SITE = 8
SENSITIVE_BREACH_DATA = ("Phone numbers", "Physical addresses", "Dates of birth",
                         "Credit cards", "Bank account numbers", "Government issued IDs")

Breakdown = tuple[int, list[Contribution]]


def _finish(contributions: list[Contribution]) -> Breakdown:
    return min(100, sum(c.points for c in contributions)), contributions


def pii_breakdown(findings: list[Finding]) -> Breakdown:
    groups: dict[str, list[Finding]] = defaultdict(list)
    for f in findings:
        groups[f.type].append(f)

    contributions = []
    for kind, items in groups.items():
        top = max(items, key=lambda f: SEVERITY_RANK[f.severity]).severity
        base = SEVERITY_POINTS[top]
        points = min(base * TYPE_CAP_MULTIPLE, base + base * REPEAT_FACTOR * (len(items) - 1))
        label = f"{kind} ({top})" + (f" x{len(items)}" if len(items) > 1 else "")
        contributions.append(Contribution(label=label, points=round(points)))
    contributions.sort(key=lambda c: -c.points)
    return _finish(contributions)


def breach_breakdown(breaches: list[Breach]) -> Breakdown:
    n = len(breaches)
    if n == 0:
        return 0, []
    base = {1: 40, 2: 55, 3: 65}.get(n, min(85, 65 + 2 * (n - 3)))
    contributions = [Contribution(label=f"Email found in {n} breach{'es' if n > 1 else ''}", points=base)]
    exposed = {d for b in breaches for d in b.data_exposed}
    if "Passwords" in exposed:
        contributions.append(Contribution(label="Passwords were leaked", points=15))
    if any(d in exposed for d in SENSITIVE_BREACH_DATA):
        contributions.append(Contribution(label="Phone / address / DOB / ID data leaked", points=10))
    return _finish(contributions)


def content_breakdown(findings: list[Finding]) -> Breakdown:
    if not findings:
        return 0, []
    top = max(f.confidence for f in findings)
    contributions = [Contribution(label=f"Riskiest post ({top:.0%} confident)", points=round(top * 100))]
    if len(findings) > 1:
        contributions.append(Contribution(label=f"{len(findings) - 1} more risky post(s)",
                                          points=5 * (len(findings) - 1)))
    return _finish(contributions)


def accounts_breakdown(sites_found: int) -> Breakdown:
    if sites_found == 0:
        return 0, []
    return _finish([Contribution(label=f"{sites_found} accounts found x {POINTS_PER_SITE}",
                                 points=min(100, sites_found * POINTS_PER_SITE))])


# Plain score helpers (used by tests and by anything that doesn't need the working)
def pii_score(findings: list[Finding]) -> int:
    return pii_breakdown(findings)[0]


def breach_score(breaches: list[Breach]) -> int:
    return breach_breakdown(breaches)[0]


def accounts_score(sites_found: int) -> int:
    return accounts_breakdown(sites_found)[0]


def level_for(score: int) -> str:
    if score <= 30:
        return "Low"
    if score <= 60:
        return "Medium"
    return "High"


def combine(raw: dict[str, int | None],
            contributions: dict[str, list[Contribution]] | None = None,
            unavailable: set[str] | frozenset[str] = frozenset()) -> tuple[int, str, list[CategoryScore]]:
    """raw: category -> score, or None when that check was not run or failed.

    `unavailable` lists categories we tried to check but could not; they are left
    out of the total (the weights re-balance) and shown as "couldn't check".
    """
    contributions = contributions or {}
    active = {k: v for k, v in raw.items() if v is not None}
    total_weight = sum(WEIGHTS[k] for k in active) or 1

    categories = []
    for k in WEIGHTS:
        checked = raw.get(k) is not None
        categories.append(CategoryScore(
            key=k, label=LABELS[k], score=raw.get(k) or 0, checked=checked,
            weight=round(WEIGHTS[k] / total_weight, 3) if checked else 0,
            status="ok" if checked else ("unavailable" if k in unavailable else "not_checked"),
            contributions=contributions.get(k, []),
        ))
    total = round(sum(v * WEIGHTS[k] / total_weight for k, v in active.items()))
    return total, level_for(total), categories
