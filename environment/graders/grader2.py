from ..models import IncidentPriorityAction, IncidentReport
from typing import List, Dict
from ..scoring import normalize_open_score

SEVERITY_BASE = {
    "runway_incursion": 0.95,
    "atc_deviation": 0.80,
    "fdtl_violation": 0.70,
    "technical_snag": 0.60,
    "maintenance_lapse": 0.65,
    "bird_strike": 0.50,
    "fuel_irregularity": 0.55,
    "unauthorized_access": 0.45,
}

def compute_priority_score(incident: IncidentReport) -> float:
    base = SEVERITY_BASE.get(incident.incident_type, 0.5)
    # Recurrence multiplier (Principle 3: pattern detection)
    recurrence_boost = min(incident.recurrence_count * 0.08, 0.25)
    # High-traffic airport multiplier
    traffic_boost = min(incident.flights_per_day_at_airport / 500 * 0.10, 0.10)
    # Days since inspection penalty
    inspection_penalty = min(incident.days_since_last_inspection / 180 * 0.10, 0.10)
    # Severity level multiplier
    severity_map = {"low": 1.0, "medium": 1.15, "high": 1.30, "critical": 1.50}
    multiplier = severity_map[incident.severity]
    raw = (base + recurrence_boost + traffic_boost + inspection_penalty) * multiplier
    return round(min(raw, 1.0), 4)

def grade_task2(action: IncidentPriorityAction, incidents: List[IncidentReport]) -> float:
    score = 0.0
    true_scores = {i.incident_id: compute_priority_score(i) for i in incidents}
    true_ranking = sorted(true_scores, key=true_scores.get, reverse=True)

    # TOP-3 ACCURACY — 50% of reward (order-agnostic set overlap)
    top3_agent = set(action.priority_ranking[:3])
    top3_true = set(true_ranking[:3])
    score += 0.50 * (len(top3_agent & top3_true) / 3)

    # TOP-5 OVERLAP — 15% of reward (replaces full Kendall tau; more forgiving)
    top5_agent = set(action.priority_ranking[:5])
    top5_true = set(true_ranking[:5])
    score += 0.15 * (len(top5_agent & top5_true) / 5)

    # ESCALATION F1 — 20% of reward (precision + recall of escalate_immediately)
    true_escalate = [i.incident_id for i in incidents if true_scores[i.incident_id] >= 0.85]
    if true_escalate:
        esc_set = set(action.escalate_immediately)
        true_esc_set = set(true_escalate)
        precision = len(esc_set & true_esc_set) / max(len(esc_set), 1)
        recall = len(esc_set & true_esc_set) / len(true_esc_set)
        f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) > 0 else 0.0
        score += 0.20 * f1
    else:
        score += 0.20 if not action.escalate_immediately else 0.0

    # PATTERN DETECTION — 15% of reward (systemic risk identification)
    type_airline_groups: Dict[str, int] = {}
    for i in incidents:
        key = f"{i.incident_type}_{i.airline}"
        type_airline_groups[key] = type_airline_groups.get(key, 0) + 1
    real_pattern_exists = any(v >= 2 for v in type_airline_groups.values())
    if action.pattern_detected == real_pattern_exists:
        score += 0.15
    elif action.pattern_detected and not real_pattern_exists:
        score += 0.05  # Partial credit: false alarm better than missing one

    return normalize_open_score(score)
