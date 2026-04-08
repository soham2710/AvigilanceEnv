from environment.avigilance_env import AvigilanceEnv
from environment.models import AvigilanceAction, AvigilanceReward


REWARD_FLOAT_FIELDS = (
    "score",
    "accuracy_component",
    "consistency_component",
    "safety_alignment_component",
    "justification_quality",
    "safety_principle_p1_transparency",
    "safety_principle_p2_compliance",
    "safety_principle_p3_consistency",
)


def test_reward_model_clamps_boundary_values_into_open_interval():
    reward = AvigilanceReward(
        score=0,
        accuracy_component=0,
        consistency_component=1,
        safety_alignment_component=1,
        justification_quality=0,
        safety_principle_p1_transparency=0,
        safety_principle_p2_compliance=1,
        safety_principle_p3_consistency=1,
        feedback="boundary test",
        done=True,
    )

    for field_name in REWARD_FLOAT_FIELDS:
        value = getattr(reward, field_name)
        assert 0 < value < 1, f"{field_name} escaped the open interval: {value}"


def test_task_reward_payload_never_returns_exact_zero_or_one():
    env = AvigilanceEnv(task_id="task1", seed=42)
    env.reset()

    _, reward, _, _ = env.step(AvigilanceAction(task_id="task1"))

    payload = reward.model_dump()
    for field_name in REWARD_FLOAT_FIELDS:
        value = payload[field_name]
        assert 0 < value < 1, f"{field_name} serialized as a boundary value: {value}"