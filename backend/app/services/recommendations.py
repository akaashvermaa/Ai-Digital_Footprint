"""Rule-based advice. Every finding maps to a concrete fix, sorted by urgency."""
from app.schemas import Breach, Finding, Recommendation, SiteResult
from app.services.explanations import describe

RANK = {"urgent": 0, "important": 1, "good practice": 2}
SEVERITY_PRIORITY = {"high": "urgent", "medium": "important", "low": "good practice"}


def build_recommendations(findings: list[Finding], breaches: list[Breach],
                          sites_found: list[SiteResult], level: str) -> list[Recommendation]:
    chosen: dict[str, str] = {}   # advice text -> most urgent priority it was given

    def add(priority: str, text: str):
        if text and (text not in chosen or RANK[priority] < RANK[chosen[text]]):
            chosen[text] = priority

    for f in findings:
        add(SEVERITY_PRIORITY[f.severity], f.fix or describe(f.type)[1])

    if breaches:
        exposed = {d for b in breaches for d in b.data_exposed}
        names = ", ".join(b.name for b in breaches[:3]) + (" and others" if len(breaches) > 3 else "")
        if "Passwords" in exposed:
            add("urgent", "Passwords were leaked in a breach: change the password of every account that uses "
                          "this email, never reuse passwords, and use a password manager.")
        add("important", f"Your email was found in {len(breaches)} data breach(es) ({names}). "
                         "Change the passwords of accounts that use this email.")
        add("important", "Turn on two-factor authentication (2FA) for email, banking and social media.")
        add("important", "Be careful with calls, SMS or emails asking for OTPs or details; "
                         "breached data is used for phishing.")

    if len(sites_found) >= 5:
        add("important", f"Your username appears on {len(sites_found)} sites. Delete accounts you no longer "
                         "use and make the others private.")
    if sites_found:
        add("good practice", "Use different usernames for personal and professional accounts so they "
                             "can't be linked easily.")

    if level == "Low":
        add("good practice", "Your footprint looks good. Keep reviewing your privacy settings every few months.")
    add("good practice", "Search your own name and username on Google regularly to see what others can find.")

    return [Recommendation(priority=p, text=t)
            for t, p in sorted(chosen.items(), key=lambda kv: RANK[kv[1]])]
