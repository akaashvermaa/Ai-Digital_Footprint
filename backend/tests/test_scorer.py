from app.schemas import Breach, Finding
from app.services.risk_scorer import (accounts_score, breach_breakdown, breach_score, combine,
                                      content_breakdown, level_for, pii_breakdown, pii_score)


def finding(severity, kind="x", confidence=0.9):
    return Finding(category="pii", type=kind, value="x", severity=severity, source="test", confidence=confidence)


def test_levels():
    assert level_for(0) == "Low"
    assert level_for(30) == "Low"
    assert level_for(45) == "Medium"
    assert level_for(61) == "High"


def test_same_type_is_capped_at_twice_the_base():
    # ten high-severity findings of ONE type must not reach 100
    assert pii_score([finding("high", "Phone number")] * 10) == 50
    # eight cities: 12 base, capped at 24
    assert pii_score([finding("medium", "Location")] * 8) == 24


def test_different_types_add_up():
    findings = [finding("high", "Phone number"), finding("high", "Date of birth"),
                finding("medium", "Location"), finding("low", "Person name")]
    assert pii_score(findings) == 25 + 25 + 12 + 5


def test_second_finding_of_a_type_earns_less():
    one = pii_score([finding("high", "Phone number")])
    two = pii_score([finding("high", "Phone number")] * 2)
    assert one < two < 2 * one


def test_score_is_the_sum_of_its_contributions():
    score, parts = pii_breakdown([finding("high", "Phone number"), finding("medium", "Location")] * 2)
    assert score == sum(p.points for p in parts)
    assert {p.label.split(" (")[0] for p in parts} == {"Phone number", "Location"}


def test_breach_score_increases_with_passwords():
    plain = [Breach(name="A", data_exposed=["Email addresses"])]
    with_pw = [Breach(name="A", data_exposed=["Email addresses", "Passwords"])]
    assert breach_score([]) == 0
    assert breach_score(with_pw) > breach_score(plain) > 0


def test_breach_breakdown_explains_itself():
    score, parts = breach_breakdown([Breach(name="A", data_exposed=["Passwords", "Phone numbers"])])
    assert score == 40 + 15 + 10
    assert [p.points for p in parts] == [40, 15, 10]


def test_content_score_only_counts_flagged_posts():
    assert content_breakdown([])[0] == 0
    score, parts = content_breakdown([finding("high", confidence=0.8), finding("medium", confidence=0.7)])
    assert score == 85 and len(parts) == 2


def test_accounts_score():
    assert accounts_score(0) == 0
    assert accounts_score(5) == 40
    assert accounts_score(20) == 100


def test_unchecked_categories_are_ignored():
    # Only text was checked, so the score equals the text-based categories only
    score, level, categories = combine({"pii": 100, "breach": None, "content": 100, "accounts": None})
    assert score == 100 and level == "High"
    assert sum(c.weight for c in categories) == 1.0


def test_unavailable_category_is_excluded_and_labelled():
    score, _, categories = combine({"pii": 50, "breach": None, "content": None, "accounts": None},
                                   unavailable={"breach"})
    by_key = {c.key: c for c in categories}
    assert score == 50                       # the failed breach check does not drag the score to 0
    assert by_key["breach"].status == "unavailable" and not by_key["breach"].checked
    assert by_key["content"].status == "not_checked"


def test_all_zero_is_low():
    score, level, _ = combine({"pii": 0, "breach": 0, "content": 0, "accounts": 0})
    assert (score, level) == (0, "Low")
