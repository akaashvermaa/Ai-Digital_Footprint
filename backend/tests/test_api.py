"""API behaviour: failures, bad input, rate limiting and safe headers."""
import pytest
from fastapi.testclient import TestClient

from app import main
from app.schemas import SiteResult
from app.security import limiter

SAMPLE = "Call me at 9876543210. Going to Goa for 2 weeks, house is empty!"


@pytest.fixture(scope="module")
def client():
    with TestClient(main.app, raise_server_exceptions=False) as c:
        yield c


@pytest.fixture(autouse=True)
def _fresh_limiter(monkeypatch):
    monkeypatch.setenv("RATE_LIMIT_PER_MIN", "1000")
    limiter.reset()


async def _boom(*_):
    raise RuntimeError("network exploded")


def test_one_failing_checker_does_not_break_the_others(client, monkeypatch):
    monkeypatch.setattr(main, "scan_username", _boom)
    r = client.post("/api/analyze", json={"username": "someone", "text": SAMPLE})
    body = r.json()
    assert r.status_code == 200
    assert body["username_check_status"] == "unavailable"
    by_key = {c["key"]: c for c in body["categories"]}
    assert by_key["accounts"]["status"] == "unavailable" and not by_key["accounts"]["checked"]
    assert by_key["pii"]["checked"] and body["findings"]          # the text analysis still worked
    assert any("unknown, not zero" in n for n in body["limitations"])


def test_unavailable_breach_service_is_reported_not_hidden(client, monkeypatch):
    async def down(_):
        return [], "unavailable"
    monkeypatch.setattr(main, "check_breaches", down)
    body = client.post("/api/analyze", json={"email": "a@b.com", "text": SAMPLE}).json()
    assert body["breach_check_status"] == "unavailable"
    assert {c["key"]: c["status"] for c in body["categories"]}["breach"] == "unavailable"
    assert any("unknown, not zero" in n for n in body["limitations"])


def test_partial_username_scan_is_flagged(client, monkeypatch):
    async def partial(_):
        return [SiteResult(site="GitHub", url="https://github.com/x", category="Developer")], 20, 4
    monkeypatch.setattr(main, "scan_username", partial)
    body = client.post("/api/analyze", json={"username": "someone"}).json()
    assert body["username_check_status"] == "partial" and body["sites_unknown"] == 4
    assert any("4 of 24 sites could not be checked" in n for n in body["limitations"])


def test_all_checks_failing_gives_a_clear_503(client, monkeypatch):
    monkeypatch.setattr(main, "scan_username", _boom)
    r = client.post("/api/analyze", json={"username": "someone"})
    assert r.status_code == 503 and "try again" in r.json()["detail"]


@pytest.mark.parametrize("payload, fragment", [
    ({}, "at least"),
    ({"username": "bad name!"}, "Username can only"),
    ({"email": "not-an-email"}, "valid email"),
])
def test_bad_input_gets_a_readable_400(client, payload, fragment):
    r = client.post("/api/analyze", json=payload)
    assert r.status_code == 400 and fragment in r.json()["detail"]


def test_too_long_text_is_rejected_without_echoing_it(client):
    secret = "S3CRET-" * 2000
    r = client.post("/api/analyze", json={"text": secret})
    assert r.status_code == 422
    assert "too long" in r.json()["detail"] and "S3CRET" not in r.text


def test_control_and_bidi_characters_are_stripped(client):
    text = "call\x00 me ‮at‬ 9876543210 \x07"
    body = client.post("/api/analyze", json={"text": text}).json()
    assert any(f["type"] == "Phone number" for f in body["findings"])


def test_unexpected_error_returns_generic_message(client, monkeypatch):
    def explode(*_, **__):
        raise ValueError("secret detail 9876543210")
    monkeypatch.setattr(main, "build_summary", explode)
    r = client.post("/api/analyze", json={"text": SAMPLE})
    assert r.status_code == 500
    assert r.json()["detail"].startswith("Something went wrong") and "9876543210" not in r.text


def test_rate_limit_returns_429_with_retry_after(client, monkeypatch):
    monkeypatch.setenv("RATE_LIMIT_PER_MIN", "2")
    codes = [client.post("/api/analyze", json={"text": "hello there friend"}).status_code for _ in range(3)]
    assert codes == [200, 200, 429]
    r = client.post("/api/analyze", json={"text": "hello there friend"})
    assert r.status_code == 429 and int(r.headers["retry-after"]) >= 1 and "Too many" in r.json()["detail"]


def test_security_headers_are_present(client):
    r = client.get("/api/health")
    assert r.headers["cache-control"] == "no-store"
    assert r.headers["x-content-type-options"] == "nosniff"
    assert r.headers["referrer-policy"] == "no-referrer"
    assert r.headers["x-frame-options"] == "DENY"


def test_cors_only_allows_the_configured_frontend(client):
    ok = client.get("/api/health", headers={"Origin": "http://localhost:5173"})
    bad = client.get("/api/health", headers={"Origin": "http://evil.example"})
    assert ok.headers.get("access-control-allow-origin") == "http://localhost:5173"
    assert "access-control-allow-origin" not in bad.headers


def test_report_returns_a_pdf(client):
    result = client.post("/api/analyze", json={"text": SAMPLE}).json()
    r = client.post("/api/report", json=result)
    assert r.status_code == 200 and r.content.startswith(b"%PDF") and r.headers["cache-control"] == "no-store"


def test_report_payload_is_size_limited(client):
    result = client.post("/api/analyze", json={"text": SAMPLE}).json()
    result["findings"] = result["findings"][:1] * 301
    assert client.post("/api/report", json=result).status_code == 422


def test_report_escapes_markup_in_text(client):
    result = client.post("/api/analyze", json={"text": SAMPLE}).json()
    result["summary"] = ["<b>bold</b> & <script>x</script>"]
    r = client.post("/api/report", json=result)
    assert r.status_code == 200 and r.content.startswith(b"%PDF")
