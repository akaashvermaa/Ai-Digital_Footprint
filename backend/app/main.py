"""FastAPI backend for the AI Digital Footprint Risk Analyzer.

Run:  uvicorn app.main:app --reload     (API docs at http://localhost:8000/docs)

Each check (text analysis, username scan, breach lookup) is isolated: if one fails
it is reported as "unavailable" and left out of the score, and the others still run.
"""
import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.responses import Response

from app.schemas import AnalyzeRequest, AnalyzeResponse
from app.security import clean_text, install_security
from app.services.breach_checker import check_breaches, is_valid_email
from app.services.pii_detector import detect_pii_with_spans, get_nlp
from app.services.recommendations import build_recommendations
from app.services.report_pdf import build_pdf
from app.services.risk_scorer import (accounts_breakdown, breach_breakdown, combine,
                                      content_breakdown, pii_breakdown)
from app.services.summary import build_limitations, build_summary
from app.services.text_risk_model import analyze_content, get_model
from app.services.username_checker import is_valid_username, scan_username

logger = logging.getLogger("footprint")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Load the NLP and ML models once at startup so the first request is fast
    get_nlp()
    get_model()
    yield


app = FastAPI(title="AI Digital Footprint Risk Analyzer", lifespan=lifespan)
install_security(app)


@app.get("/api/health")
def health():
    return {"status": "ok"}


# --- isolated checks: they never raise, a failure becomes an "unavailable" status -------------

async def run_username(username: str):
    try:
        found, checked, unknown = await scan_username(username)
    except Exception as exc:
        logger.error("Username scan failed: %s", type(exc).__name__)
        return [], 0, 0, "unavailable"
    status = "unavailable" if checked == 0 else "partial" if unknown else "ok"
    return found, checked, unknown, status


async def run_breach(email: str):
    try:
        return await check_breaches(email)
    except Exception as exc:
        logger.error("Breach check failed: %s", type(exc).__name__)
        return [], "unavailable"


def analyse_text(text: str):
    """Returns (pii findings, content findings) or None if the analysis failed."""
    try:
        pii_findings, spans = detect_pii_with_spans(text)
        return pii_findings, analyze_content(text, spans)[1]
    except Exception as exc:
        logger.error("Text analysis failed: %s", type(exc).__name__)
        return None


async def _skip():
    return None


@app.post("/api/analyze", response_model=AnalyzeResponse)
async def analyze(req: AnalyzeRequest):
    username = (req.username or "").strip().lstrip("@")
    email = (req.email or "").strip().lower()
    text = clean_text(req.text)

    if not (username or email or text):
        raise HTTPException(400, "Enter at least a username, an email or some text.")
    if username and not is_valid_username(username):
        raise HTTPException(400, "Username can only contain letters, numbers, '.', '_' and '-' (2-40 characters).")
    if email and not is_valid_email(email):
        raise HTTPException(400, "Please enter a valid email address.")

    username_res, breach_res, text_res = await asyncio.gather(
        run_username(username) if username else _skip(),
        run_breach(email) if email else _skip(),
        asyncio.to_thread(analyse_text, text) if text else _skip(),
    )

    unavailable: set[str] = set()
    raw: dict[str, int | None] = {"pii": None, "breach": None, "content": None, "accounts": None}
    contributions: dict[str, list] = {}
    findings = []

    if text:
        if text_res is None:
            unavailable |= {"pii", "content"}
        else:
            pii_findings, content_findings = text_res
            findings = pii_findings + content_findings
            raw["pii"], contributions["pii"] = pii_breakdown(pii_findings)
            raw["content"], contributions["content"] = content_breakdown(content_findings)

    sites_found, sites_checked, sites_unknown, username_status = [], 0, 0, "not_checked"
    if username:
        sites_found, sites_checked, sites_unknown, username_status = username_res
        if username_status == "unavailable":
            unavailable.add("accounts")
        else:
            raw["accounts"], contributions["accounts"] = accounts_breakdown(len(sites_found))

    breaches, breach_status = [], "not_checked"
    if email:
        breaches, breach_status = breach_res
        if breach_status == "unavailable":
            unavailable.add("breach")
        else:
            raw["breach"], contributions["breach"] = breach_breakdown(breaches)

    if all(v is None for v in raw.values()):
        raise HTTPException(503, "None of the checks could run right now. Please try again in a moment.")

    score, level, categories = combine(raw, contributions, unavailable)
    inputs = {"username": bool(username), "email": bool(email), "text": bool(text)}

    return AnalyzeResponse(
        score=score, level=level, categories=categories, findings=findings,
        sites_found=sites_found, sites_checked=sites_checked, sites_unknown=sites_unknown,
        username_check_status=username_status,
        breaches=breaches, breach_check_status=breach_status,
        summary=build_summary(findings, sites_found, breaches, inputs),
        recommendations=build_recommendations(findings, breaches, sites_found, level),
        limitations=build_limitations(inputs, sites_checked, sites_unknown, username_status, breach_status),
        inputs=inputs,
    )


@app.post("/api/report")
def report(result: AnalyzeResponse):
    return Response(
        content=build_pdf(result),
        media_type="application/pdf",
        headers={"Content-Disposition": 'attachment; filename="footprint-risk-report.pdf"'},
    )
