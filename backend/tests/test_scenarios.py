import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.security import limiter
from evaluation.scenarios import SCENARIOS, run_scenario


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture(autouse=True)
def _no_rate_limit(monkeypatch):
    monkeypatch.setenv("RATE_LIMIT_PER_MIN", "1000")
    limiter.reset()


@pytest.mark.parametrize("scenario", SCENARIOS, ids=[s["name"] for s in SCENARIOS])
def test_scenario_lands_in_expected_level(client, scenario):
    result = run_scenario(client, scenario)
    assert result["level"] == scenario["level"], f"score {result['score']}"


def test_every_point_is_traceable_to_a_contribution(client):
    result = run_scenario(client, SCENARIOS[-1])
    for category in result["categories"]:
        if category["checked"]:
            total = sum(c["points"] for c in category["contributions"])
            assert category["score"] == min(100, total), category["label"]


def test_clean_text_scores_zero(client):
    result = run_scenario(client, SCENARIOS[0])
    assert result["score"] == 0 and result["findings"] == []
