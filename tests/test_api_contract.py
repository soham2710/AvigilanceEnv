import pytest
from fastapi.testclient import TestClient

from app import app
from environment.models import AvigilanceReward, REWARD_FLOAT_FIELDS


client = TestClient(app)


def _assert_reward_fields_within_open_interval(reward: dict) -> None:
    for field_name in REWARD_FLOAT_FIELDS:
        value = reward[field_name]
        assert 0 < value < 1, f"{field_name} escaped the open interval: {value}"


def _build_action(task_id: str, observation: dict) -> dict:
    if task_id == "task1":
        return {
            "task_id": "task1",
            "fto_grade_action": {
                "grade": "B",
                "total_score": 70,
                "risk_flags": [],
                "recommended_action": "self_assessment_required",
                "justification": "Contract test action from pytest.",
            },
        }

    if task_id == "task2":
        incident_ids = [item["incident_id"] for item in observation["incident_batch"]]
        return {
            "task_id": "task2",
            "incident_priority_action": {
                "priority_ranking": incident_ids,
                "top_3_rationale": "Contract test rationale from pytest.",
                "defer_list": incident_ids[3:],
                "escalate_immediately": incident_ids[:2],
                "pattern_detected": False,
                "pattern_description": None,
            },
        }

    incident_ids = [item["incident_id"] for item in observation["incident_queue"]]
    fto_ids = [item["fto_id"] for item in observation["fto_audit_queue"]]
    assignments = {
        "inspector_1": (incident_ids + fto_ids)[:2],
        "inspector_2": (incident_ids + fto_ids)[2:4],
    }
    return {
        "task_id": "task3",
        "resource_allocation_action": {
            "inspector_assignments": assignments,
            "deferred_items": (incident_ids + fto_ids)[4:],
            "priority_rationale": "Contract test allocation rationale from pytest.",
            "predicted_risk_reduction": 0.55,
            "abstain": False,
            "abstain_reason": None,
        },
    }


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
    _assert_reward_fields_within_open_interval(payload["reward"])
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


@pytest.mark.parametrize("task_id", ["task1", "task2", "task3"])
def test_all_task_step_rewards_stay_inside_open_interval(task_id: str) -> None:
    reset = client.post("/reset", params={"task_id": task_id, "seed": 42})

    assert reset.status_code == 200
    action = _build_action(task_id, reset.json())

    step = client.post("/step", json=action)

    assert step.status_code == 200
    _assert_reward_fields_within_open_interval(step.json()["reward"])


@pytest.mark.parametrize(
    ("task_id", "invalid_payload"),
    [
        ("task1", {"task_id": "task1"}),
        ("task2", {"task_id": "task2"}),
        ("task3", {"task_id": "task3"}),
    ],
)
def test_missing_task_actions_return_open_interval_reward_fields(task_id: str, invalid_payload: dict) -> None:
    reset = client.post("/reset", params={"task_id": task_id, "seed": 42})

    assert reset.status_code == 200
    step = client.post("/step", json=invalid_payload)

    assert step.status_code == 200
    _assert_reward_fields_within_open_interval(step.json()["reward"])