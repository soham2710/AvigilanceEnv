import json
import random
from pathlib import Path
from typing import Dict, Any, List
from ..models import AvigilanceObservation, AvigilanceAction, AvigilanceReward, FTOProfile, IncidentReport
from ..graders.grader3 import grade_task3

class Task3ResourceAllocator:
    def __init__(self, data_dir: Path, rng: random.Random):
        self.data_dir = data_dir
        self.rng = rng
        self._ftos = self._load_ftos()
        self._incidents = self._load_incidents()

    def _load_ftos(self) -> List[Dict[str, Any]]:
        with open(self.data_dir / "fto_profiles.json", "r") as f:
            return json.load(f)

    def _load_incidents(self) -> List[Dict[str, Any]]:
        with open(self.data_dir / "incident_reports.json", "r") as f:
            return json.load(f)

    def sample_scenario(self) -> Dict[str, Any]:
        # Adjusted for solvability: 2-3 FTOs, 8-12 incidents
        fto_count = self.rng.randint(2, 3)
        incident_count = self.rng.randint(8, 12)
        inspectors = self.rng.randint(2, 3)
        # Tighter budget: 30-70 hours
        budget = self.rng.randint(30, 70)
        
        return {
            "scenario_id": f"task3_{self.rng.randint(1000, 9999)}",
            "fto_audit_queue": self.rng.sample(self._ftos, fto_count),
            "incident_queue": self.rng.sample(self._incidents, incident_count),
            "inspector_capacity": inspectors,
            "week_budget_hours": budget
        }

    def build_observation(self, scenario: Dict[str, Any], step_count: int, terminal: bool = False) -> AvigilanceObservation:
        ftos = [FTOProfile(**{k: v for k, v in f.items() if not k.startswith("_")}) for f in scenario["fto_audit_queue"]]
        incidents = [IncidentReport(**i) for i in scenario["incident_queue"]]
        
        return AvigilanceObservation(
            task_id="task3",
            episode_step=step_count,
            max_steps=2,
            fto_audit_queue=ftos,
            incident_queue=incidents,
            inspector_capacity=scenario["inspector_capacity"],
            week_budget_hours=scenario["week_budget_hours"],
            context_note=f"Allocate {scenario['inspector_capacity']} inspectors to the provided audit and incident queues."
        )

    def grade(self, action: AvigilanceAction, scenario: Dict[str, Any]) -> AvigilanceReward:
        if action.resource_allocation_action is None:
            return AvigilanceReward(
                score=0.0, accuracy_component=0.0, consistency_component=0.0,
                safety_alignment_component=0.0, justification_quality=0.0,
                safety_principle_p1_transparency=0.0, safety_principle_p2_compliance=0.0,
                safety_principle_p3_consistency=0.0, feedback="No resource_allocation_action provided", done=True
            )
            
        score = grade_task3(
            action.resource_allocation_action,
            [FTOProfile(**{k: v for k, v in f.items() if not k.startswith("_")}) for f in scenario["fto_audit_queue"]],
            [IncidentReport(**i) for i in scenario["incident_queue"]],
            scenario["inspector_capacity"],
            scenario["week_budget_hours"]
        )
        
        # Determine if done
        done = False
        if score > 0.85:
            done = True
            
        return AvigilanceReward(
            score=score,
            accuracy_component=0.4 if score > 0.4 else score,
            consistency_component=0.2 if score > 0.6 else 0.1,
            safety_alignment_component=0.2 if score > 0.8 else 0.1,
            justification_quality=0.2 if action.resource_allocation_action.priority_rationale else 0.0,
            safety_principle_p1_transparency=1.0 if not action.resource_allocation_action.abstain else 0.5,
            safety_principle_p2_compliance=1.0 if score > 0.3 else 0.0,
            safety_principle_p3_consistency=1.0 if score > 0.7 else 0.5,
            feedback=f"Resource Allocation Action score: {score}",
            done=done
        )

    def advance_scenario(self, scenario: Dict[str, Any]) -> Dict[str, Any]:
        # Simple advance: sample new items for step 2
        return self.sample_scenario()
