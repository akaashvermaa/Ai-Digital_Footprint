"""Request / response models shared by the API and the PDF report.

Lists and strings have maximum sizes, so a /api/report payload can't be used to
send huge documents to the PDF generator.
"""
from typing import Literal, Optional

from pydantic import BaseModel, Field

Severity = Literal["low", "medium", "high"]
CheckStatus = Literal["ok", "not_checked", "unavailable", "partial"]


class AnalyzeRequest(BaseModel):
    username: Optional[str] = Field(None, max_length=50)
    email: Optional[str] = Field(None, max_length=120)
    text: Optional[str] = Field(None, max_length=10000)


class Finding(BaseModel):
    category: Literal["pii", "content", "breach", "accounts"]
    type: str = Field(max_length=80)            # e.g. "Phone number", "Location"
    value: str = Field(max_length=300)          # masked when sensitive
    severity: Severity
    source: str = Field(max_length=40)           # "regex", "spaCy NER", "ML model", ...
    confidence: float = Field(0.9, ge=0, le=1)  # how sure the detector is (regex ids > NER guesses)
    occurrences: int = Field(1, ge=1, le=10000) # same value found several times, reported once
    explanation: str = Field("", max_length=400)  # why this could be risky
    fix: str = Field("", max_length=400)          # what the user should do


class SiteResult(BaseModel):
    site: str = Field(max_length=60)
    url: str = Field(max_length=300)
    category: str = Field(max_length=40)


class Breach(BaseModel):
    name: str = Field(max_length=100)
    year: Optional[str] = Field(None, max_length=10)
    data_exposed: list[str] = Field([], max_length=60)


class Contribution(BaseModel):
    """One line of 'where did these points come from?'."""
    label: str = Field(max_length=120)
    points: int = Field(ge=0, le=100)


class CategoryScore(BaseModel):
    key: str = Field(max_length=20)
    label: str = Field(max_length=40)
    score: int = Field(ge=0, le=100)             # 0-100
    weight: float = Field(ge=0, le=1)            # share of the total, after re-normalising
    checked: bool
    status: CheckStatus = "ok"                   # unavailable = we tried but the check failed
    contributions: list[Contribution] = Field([], max_length=30)


class Recommendation(BaseModel):
    priority: Literal["urgent", "important", "good practice"]
    text: str = Field(max_length=500)


class AnalyzeResponse(BaseModel):
    score: int = Field(ge=0, le=100)
    level: Literal["Low", "Medium", "High"]
    categories: list[CategoryScore] = Field(max_length=10)
    findings: list[Finding] = Field(max_length=300)
    sites_found: list[SiteResult] = Field(max_length=100)
    sites_checked: int = Field(ge=0, le=1000)
    sites_unknown: int = Field(0, ge=0, le=1000)  # blocked / timed out: result unknown
    username_check_status: CheckStatus = "not_checked"
    breaches: list[Breach] = Field(max_length=1000)
    breach_check_status: CheckStatus
    summary: list[str] = Field([], max_length=20)       # what the system discovered, in plain words
    recommendations: list[Recommendation] = Field(max_length=60)
    limitations: list[str] = Field([], max_length=20)   # what this result can NOT tell you
    inputs: dict[str, bool]                              # which inputs were provided
