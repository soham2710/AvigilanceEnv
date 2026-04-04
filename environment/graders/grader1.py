from ..models import FTOGradeAction
from typing import Dict, Any

def grade_task1(action: FTOGradeAction, ground_truth: Dict[str, Any]) -> float:
    score = 0.0
    # Grade accuracy (40% of reward)
    grades = ["C", "B", "A", "A+"]
    if action.grade == ground_truth["expected_grade"]:
        score += 0.40
    elif abs(grades.index(action.grade) -
             grades.index(ground_truth["expected_grade"])) == 1:
        score += 0.20  # Partial credit for adjacent grade
    
    # Score accuracy (20% of reward)
    score_error = abs(action.total_score - ground_truth["true_score"])
    score += 0.20 * max(0, 1 - score_error / 20)
    
    # Risk flags correctness (20% of reward)
    flags_hit = len(set(action.risk_flags) & set(ground_truth["expected_flags"]))
    score += 0.20 * (flags_hit / max(len(ground_truth["expected_flags"]), 1))
    
    # Recommended action (20% of reward)
    if action.recommended_action == ground_truth["expected_action"]:
        score += 0.20
    elif action.recommended_action in ground_truth.get("acceptable_actions", []):
        score += 0.10
        
    return round(min(score, 1.0), 4)
