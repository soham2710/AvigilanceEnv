import json
import random
from pathlib import Path
from typing import Dict, Any, List
from ..models import AvigilanceObservation, AvigilanceAction, AvigilanceReward, IncidentReport
from ..graders.grader2 import grade_task2
from ..scoring import normalize_open_score

class Task2IncidentRanker:
    def __init__(self, data_dir: Path, rng: random.Random):
        self.data_dir = data_dir
        self.rng = rng
        self._incidents = self._load_data()

    def _load_data(self) -> List[Dict[str, Any]]:
        with open(self.data_dir / "incident_reports.json", "r") as f:
            return json.load(f)

    def sample_scenario(self) -> Dict[str, Any]:
        count = self.rng.randint(8, 10)
        batch = self.rng.sample(self._incidents, count)
        return {
            "scenario_id": f"task2_{self.rng.randint(1000, 9999)}",
            "incident_batch": batch,
            "available_inspectors": self.rng.randint(2, 5)
        }

    def build_observation(self, scenario: Dict[str, Any], step_count: int, terminal: bool = False) -> AvigilanceObservation:
        batch = [IncidentReport(**i) for i in scenario["incident_batch"]]
        return AvigilanceObservation(
            task_id="task2",
            episode_step=step_count,
            max_steps=1,
            incident_batch=batch,
            available_inspectors=scenario["available_inspectors"],
            context_note="Triage the provided batch of incidents."
        )

    def grade(self, action: AvigilanceAction, scenario: Dict[str, Any]) -> AvigilanceReward:
        if action.incident_priority_action is None:
            return AvigilanceReward(
                score=normalize_open_score(0.0),
                accuracy_component=normalize_open_score(0.0),
                consistency_component=normalize_open_score(0.0),
                safety_alignment_component=normalize_open_score(0.0),
                justification_quality=normalize_open_score(0.0),
                safety_principle_p1_transparency=normalize_open_score(0.0),
                safety_principle_p2_compliance=normalize_open_score(0.0),
                safety_principle_p3_consistency=normalize_open_score(0.0),
                feedback="No incident_priority_action provided",
                done=True,
            )
        
        score = grade_task2(action.incident_priority_action, [IncidentReport(**i) for i in scenario["incident_batch"]])
        
        return AvigilanceReward(
            score=score,
            accuracy_component=normalize_open_score(0.4 if score > 0.4 else score),
            consistency_component=normalize_open_score(0.2 if score > 0.6 else 0.1),
            safety_alignment_component=normalize_open_score(0.2 if score > 0.8 else 0.1),
            justification_quality=normalize_open_score(1.0 if action.incident_priority_action.top_3_rationale else 0.0),
            safety_principle_p1_transparency=normalize_open_score(1.0 if action.incident_priority_action.top_3_rationale else 0.0),
            safety_principle_p2_compliance=normalize_open_score(1.0 if score > 0.5 else 0.0),
            safety_principle_p3_consistency=normalize_open_score(1.0 if action.incident_priority_action.pattern_detected else 0.0),
            feedback=f"Incident Priority Action score: {score}",
            done=True
        )

    def advance_scenario(self, scenario: Dict[str, Any]) -> Dict[str, Any]:
        return scenario
