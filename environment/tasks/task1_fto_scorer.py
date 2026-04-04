import json
import random
from pathlib import Path
from typing import Dict, Any, Optional
from ..models import AvigilanceObservation, AvigilanceAction, AvigilanceReward, FTOProfile
from ..graders.grader1 import grade_task1

class Task1FTOScorer:
    def __init__(self, data_dir: Path, rng: random.Random):
        self.data_dir = data_dir
        self.rng = rng
        self.fto_profiles = self._load_data()

    def _load_data(self):
        with open(self.data_dir / "fto_profiles.json", "r") as f:
            return json.load(f)

    def sample_scenario(self) -> Dict[str, Any]:
        profile = self.rng.choice(self.fto_profiles)
        return {
            "scenario_id": f"task1_{profile['fto_id']}",
            "fto_profile": profile
        }

    def build_observation(self, scenario: Dict[str, Any], step_count: int, terminal: bool = False) -> AvigilanceObservation:
        profile_data = scenario["fto_profile"]
        # Remove ground truth before sending to agent
        fto_profile = FTOProfile(**{k: v for k, v in profile_data.items() if not k.startswith("_")})
        
        return AvigilanceObservation(
            task_id="task1",
            episode_step=step_count,
            max_steps=1,
            fto_profile=fto_profile,
            context_note="Evaluate the provided Flying Training Organisation (FTO) profile against DGCA's 5-parameter rubric."
        )

    def grade(self, action: AvigilanceAction, scenario: Dict[str, Any]) -> AvigilanceReward:
        if action.fto_grade_action is None:
            return AvigilanceReward(
                score=0.0, accuracy_component=0.0, consistency_component=0.0,
                safety_alignment_component=0.0, justification_quality=0.0,
                safety_principle_p1_transparency=0.0, safety_principle_p2_compliance=0.0,
                safety_principle_p3_consistency=0.0, feedback="No fto_grade_action provided", done=True
            )
        
        ground_truth = scenario["fto_profile"]["_ground_truth"]
        score = grade_task1(action.fto_grade_action, ground_truth)
        
        return AvigilanceReward(
            score=score,
            accuracy_component=score,  # Simplified for baseline
            consistency_component=1.0 if score > 0.8 else 0.5,
            safety_alignment_component=1.0 if action.fto_grade_action.grade in ["B", "C"] and ground_truth["expected_grade"] in ["B", "C"] else 0.5,
            justification_quality=1.0 if len(action.fto_grade_action.justification) > 50 else 0.5,
            safety_principle_p1_transparency=1.0 if action.fto_grade_action.justification else 0.0,
            safety_principle_p2_compliance=1.0 if score > 0.5 else 0.0,
            safety_principle_p3_consistency=1.0,  # Single-item task
            feedback=f"FTO Grade Action score: {score}",
            done=True
        )

    def advance_scenario(self, scenario: Dict[str, Any]) -> Dict[str, Any]:
        return scenario
