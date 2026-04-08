from fastapi.testclient import TestClient

from app import app
from environment.models import AvigilanceReward


client = TestClient(app)


def test_root_serves_space_frontend() -> None:
    response = client.get("/")

    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "AvigilanceEnv" in response.text
    assert "Reset Episode" in response.text
    assert 'label for="actionInput"' in response.text


def test_frontend_assets_are_served() -> None:
    script = client.get("/assets/app.js")
    styles = client.get("/assets/styles.css")

    assert script.status_code == 200
    assert "javascript" in script.headers["content-type"]
    assert "resetEpisode" in script.text

    assert styles.status_code == 200
    assert "text/css" in styles.headers["content-type"]
    assert "--accent" in styles.text


def test_frontend_fallback_route_serves_space_app() -> None:
    response = client.get("/walkthrough")

    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "AvigilanceEnv" in response.text


def test_openenv_endpoints_round_trip() -> None:
    reset = client.post("/reset", params={"task_id": "task1", "seed": 42})
    assert reset.status_code == 200
    observation = reset.json()
    assert observation["task_id"] == "task1"

    action = {
        "task_id": "task1",
        "fto_grade_action": {
            "grade": "B",
            "total_score": 70,
            "risk_flags": [],
            "recommended_action": "self_assessment_required",
            "justification": "Contract test action from pytest.",
        },
    }
    step = client.post("/step", json=action)
    assert step.status_code == 200
    payload = step.json()
    assert 0 < payload["reward"]["score"] < 1
    assert payload["observation"]["task_id"] == "task1"

    state = client.get("/state", params={"task_id": "task1"})
    assert state.status_code == 200
    assert state.json()["task_id"] == "task1"


def test_reward_schema_is_exclusive() -> None:
    schema = AvigilanceReward.model_json_schema()
    assert schema["properties"]["score"]["exclusiveMinimum"] == 0
    assert schema["properties"]["score"]["exclusiveMaximum"] == 1


def test_metadata_points_to_frontend_walkthrough_anchor() -> None:
    response = client.get("/metadata")

    assert response.status_code == 200
    assert response.json()["walkthrough"] == "/#walkthrough"
