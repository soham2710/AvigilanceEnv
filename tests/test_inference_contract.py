import os
import re
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
START_RE = re.compile(r"^\[START\] task=(task1|task2|task3) env=avigilance-env model=.+$")
STEP_RE = re.compile(r"^\[STEP\] step=\d+ action=.+ reward=\d+\.\d{2} done=(true|false) error=.*$")
END_RE = re.compile(r"^\[END\] success=(true|false) steps=\d+ score=\d+(?:\.\d+)? rewards=.*$")


def _extract_number(line: str, field: str) -> float:
    match = re.search(rf"{field}=(\d+(?:\.\d+)?)", line)
    assert match, f"{field} not found in line: {line}"
    return float(match.group(1))


def test_inference_emits_only_required_log_lines() -> None:
    env = os.environ.copy()
    env.setdefault("API_BASE_URL", "https://router.huggingface.co/v1")
    env.setdefault("MODEL_NAME", "Qwen/Qwen2.5-72B-Instruct")
    env.pop("HF_TOKEN", None)
    env.pop("OPENAI_API_KEY", None)
    env.pop("OPEN_ROUTER_API", None)

    result = subprocess.run(
        [sys.executable, "inference.py"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        env=env,
        check=True,
    )

    lines = [line for line in result.stdout.splitlines() if line.strip()]
    assert lines, "inference.py produced no stdout"

    start_count = 0
    end_count = 0
    for line in lines:
        if line.startswith("[START]"):
            assert START_RE.match(line), line
            start_count += 1
        elif line.startswith("[STEP]"):
            assert STEP_RE.match(line), line
            reward = _extract_number(line, "reward")
            assert 0 < reward < 1, line
        elif line.startswith("[END]"):
            assert END_RE.match(line), line
            score = _extract_number(line, "score")
            assert 0 < score < 1, line
            rewards = line.split("rewards=", 1)[1].split(",") if "rewards=" in line else []
            for reward_text in rewards:
                reward = float(reward_text)
                assert 0 < reward < 1, line
            end_count += 1
        else:
            raise AssertionError(f"Unexpected stdout line: {line}")

    assert start_count == 3
    assert end_count == 3