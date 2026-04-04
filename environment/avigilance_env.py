import json
import random
from pathlib import Path
from typing import Tuple, Optional
from .models import (AvigilanceObservation, AvigilanceAction,
                     AvigilanceReward, FTOProfile, IncidentReport)
from .tasks.task1_fto_scorer import Task1FTOScorer
from .tasks.task2_incident_ranker import Task2IncidentRanker
from .tasks.task3_resource_alloc import Task3ResourceAllocator

class AvigilanceEnv:
    """
    AvigilanceEnv: India Aviation Safety Monitoring OpenEnv

    An OpenEnv environment where an AI agent acts as the intelligent
    early-warning layer for India's DGCA aviation safety oversight system.

    Governed by Three Safety Principles:
    - P1: Semantic State Transparency (agent state is always inspectable)
    - P2: Policy Compliance Enforcement (only DGCA-valid actions permitted)
    - P3: Temporal Consistency Tracking (patterns across time are detected)

    Tasks:
    - task1: FTO Quality Scorer (Easy) — score a Flying Training Organisation
    - task2: Incident Prioritizer (Medium) — rank DGCA safety incidents
    - task3: Resource Allocator (Hard) — optimal inspector dispatch under constraints
    """

    TASKS = ["task1", "task2", "task3"]
    MAX_STEPS = {"task1": 1, "task2": 1, "task3": 2}

    def __init__(self, task_id: str = "task1", seed: Optional[int] = None):
        assert task_id in self.TASKS, f"task_id must be one of {self.TASKS}"
        self.task_id = task_id
        self.seed = seed
        self._rng = random.Random(seed)
        self._data_dir = Path(__file__).parent.parent / "data"
        self._task_handlers = {
            "task1": Task1FTOScorer(self._data_dir, self._rng),
            "task2": Task2IncidentRanker(self._data_dir, self._rng),
            "task3": Task3ResourceAllocator(self._data_dir, self._rng),
        }
        self._current_scenario = None
        self._step_count = 0
        self._done = False
        self._episode_reward = 0.0

    def reset(self) -> AvigilanceObservation:
        """Reset environment and return initial observation."""
        self._step_count = 0
        self._done = False
        self._episode_reward = 0.0
        handler = self._task_handlers[self.task_id]
        self._current_scenario = handler.sample_scenario()
        return handler.build_observation(self._current_scenario, self._step_count)

    def step(self, action: AvigilanceAction) -> Tuple[
            AvigilanceObservation, AvigilanceReward, bool, dict]:
        """Take an action and return (observation, reward, done, info)."""
        assert not self._done, "Episode is done. Call reset() first."
        assert action.task_id == self.task_id, \
            f"Action task_id {action.task_id} != env task_id {self.task_id}"

        handler = self._task_handlers[self.task_id]
        reward = handler.grade(action, self._current_scenario)

        self._step_count += 1
        self._episode_reward += reward.score
        max_steps = self.MAX_STEPS[self.task_id]
        self._done = (self._step_count >= max_steps) or reward.done

        if self._done:
            obs = handler.build_observation(self._current_scenario,
                                             self._step_count, terminal=True)
        else:
            self._current_scenario = handler.advance_scenario(self._current_scenario)
            obs = handler.build_observation(self._current_scenario, self._step_count)

        info = {
            "step": self._step_count,
            "episode_reward": self._episode_reward,
            "task_id": self.task_id,
            "safety_principles": {
                "P1_transparency": reward.safety_principle_p1_transparency,
                "P2_compliance": reward.safety_principle_p2_compliance,
                "P3_consistency": reward.safety_principle_p3_consistency,
            }
        }
        return obs, reward, self._done, info

    def state(self) -> dict:
        """Return current internal state (OpenEnv requirement)."""
        return {
            "task_id": self.task_id,
            "step": self._step_count,
            "done": self._done,
            "episode_reward": self._episode_reward,
            "seed": self.seed,
            "scenario_id": self._current_scenario.get("scenario_id")
                           if self._current_scenario else None,
        }
