"""Plain-language summary ("what did we discover?") and honest limitations."""
from app.schemas import Breach, Finding, SiteResult


def _plural(n: int, word: str) -> str:
    return f"{n} {word}{'' if n == 1 else 's'}"


def build_summary(findings: list[Finding], sites_found: list[SiteResult], breaches: list[Breach],
                  inputs: dict[str, bool]) -> list[str]:
    lines = []
    if inputs["text"]:
        pii = [f for f in findings if f.category == "pii"]
        content = [f for f in findings if f.category == "content"]
        for severity in ("high", "medium", "low"):
            n = sum(1 for f in pii if f.severity == severity)
            if n:
                lines.append(f"{_plural(n, 'personal info finding')} of {severity} severity")
        if content:
            lines.append(f"{_plural(len(content), 'potentially risky post')}")
        if not pii and not content:
            lines.append("No personal information or risky posts detected in the text")
    if inputs["username"]:
        if sites_found:
            kinds = len({s.category for s in sites_found})
            lines.append(f"Username found on {_plural(len(sites_found), 'site')} across {_plural(kinds, 'kind')} of platform")
        else:
            lines.append("Username was not found on the sites checked")
    if inputs["email"]:
        if breaches:
            with_pw = sum(1 for b in breaches if "Passwords" in b.data_exposed)
            line = f"Email appears in {_plural(len(breaches), 'breach record')}"
            lines.append(line + (f"; passwords were leaked in {with_pw}" if with_pw else ""))
        else:
            lines.append("Email was not found in the known breaches that could be checked")
    return lines


def build_limitations(inputs: dict[str, bool], sites_checked: int, sites_unknown: int,
                      username_status: str, breach_status: str) -> list[str]:
    notes = []
    if inputs["text"]:
        notes.append("Text analysis is automatic and can make mistakes; each finding shows a confidence level.")
        notes.append("The risky-post model was trained on a small dataset (about 240 posts). It can confuse posts "
                     "that talk about security or travel safety with posts that actually leak something.")
    if inputs["username"]:
        notes.append("A username match only means an account with that name exists; it may belong to someone else.")
        if username_status == "unavailable":
            notes.append("No site could be checked, so the account spread is unknown, not zero.")
        elif sites_unknown:
            notes.append(f"{sites_unknown} of {sites_checked + sites_unknown} sites could not be checked "
                         "(blocked or timed out), so more accounts may exist.")
        notes.append("Only a small set of sites is scanned; large platforms such as Instagram and X block "
                     "automated checks.")
    if inputs["email"]:
        if breach_status == "unavailable":
            notes.append("The breach database could not be reached, so breaches are unknown, not zero.")
        else:
            notes.append("Breach results come from a public database and may be incomplete.")
    return notes
