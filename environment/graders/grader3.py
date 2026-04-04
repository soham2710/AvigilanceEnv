from ..models import ResourceAllocationAction, FTOProfile, IncidentReport, IncidentSeverity
from typing import List, Dict

AUDIT_HOURS = {"C": 16, "B": 8, "near_C": 12}  # Hours per FTO audit
INCIDENT_HOURS = {
    "critical": 8,
    "high": 6,
    "medium": 4,
    "low": 2
}
MAX_TASKS_PER_INSPECTOR = 3  # Real DGCA operational constraint

def grade_task3(action: ResourceAllocationAction,
                ftos: List[FTOProfile],
                incidents: List[IncidentReport],
                inspector_count: int,
                week_budget_hours: int) -> float:
    # Solvability: 2-3 FTOs, 8-12 incidents
    # inspectors = self.rng.randint(2, 3)
    # Tighter budget: 30-70 hours
    
    # 1. Calculate Minimum Solvability (Critical items)
    critical_incidents = [i for i in incidents if i.severity == IncidentSeverity.CRITICAL]
    c_grade_ftos = [f for f in ftos if (f.performance_score + f.operational_score + f.safety_score + f.compliance_score + f.student_support_score) < 50]
    
    min_required_hours = 0
    for i in critical_incidents:
        min_required_hours += INCIDENT_HOURS.get(i.severity.value, 8)
    for f in c_grade_ftos:
        min_required_hours += AUDIT_HOURS.get("C", 16)
        
    # Solvability: budget + inspector capacity (Max 3 tasks per inspector)
    max_assignable_tasks = inspector_count * MAX_TASKS_PER_INSPECTOR
    is_solvable = (min_required_hours <= week_budget_hours) and (len(critical_incidents) + len(c_grade_ftos) <= max_assignable_tasks)
    
    # 2. Handle Abstention (Principle 1: Semantic Transparency)
    if action.abstain:
        if not is_solvable:
            # Justified caution in impossible scenario
            return 0.35 if action.abstain_reason and len(action.abstain_reason) > 20 else 0.15
        else:
            # Lazy abstention in solvable scenario (PENALTY)
            return 0.15

    score = 0.0
    # 3. Constraint satisfaction (30% of reward)
    total_hours_used = 0
    inspector_task_counts = {i: 0 for i in range(inspector_count)}
    
    for inspector_id, tasks in action.inspector_assignments.items():
        # Check if ID is within real inspector range
        try:
            idx = int(inspector_id.split('_')[-1]) % inspector_count
        except:
            idx = 0
            
        if len(tasks) > MAX_TASKS_PER_INSPECTOR:
            pass # Penalty handled by missing items/over budget
            
        for t in tasks:
            if t in [f.fto_id for f in ftos]:
                f_profile = next(f for f in ftos if f.fto_id == t)
                total_f_score = (f_profile.performance_score + f_profile.operational_score + f_profile.safety_score + f_profile.compliance_score + f_profile.student_support_score)
                hours = AUDIT_HOURS.get("C", 16) if total_f_score < 50 else (AUDIT_HOURS.get("B", 8) if total_f_score < 70 else 4)
                total_hours_used += hours
            else:
                inc = next((i for i in incidents if i.incident_id == t), None)
                total_hours_used += INCIDENT_HOURS.get(inc.severity.value if inc else "medium", 4)

    if total_hours_used <= week_budget_hours:
        score += 0.30
    else:
        # Sharp drop-off if budget exceeded
        score += 0.30 * max(0, 1 - (total_hours_used - week_budget_hours) / (week_budget_hours * 0.5))
    
    # 4. Critical item coverage (50% of reward - HIGHER WEIGHT)
    all_assigned = [t for tasks in action.inspector_assignments.values() for t in tasks]
    critical_ids = [i.incident_id for i in critical_incidents] + [f.fto_id for f in c_grade_ftos]
    
    if critical_ids:
        covered = len([c for c in critical_ids if c in all_assigned])
        score += 0.50 * (covered / len(critical_ids))
    else:
        score += 0.50
        
    # 5. Risk reduction quality (20% of reward) — computed from actual assignments
    # Covers critical AND high-severity incidents + C-grade FTOs (not self-reported)
    high_inc_ids = [i.incident_id for i in incidents
                    if i.severity in (IncidentSeverity.CRITICAL, IncidentSeverity.HIGH)]
    risk_fto_ids = [f.fto_id for f in ftos
                    if (f.performance_score + f.operational_score + f.safety_score
                        + f.compliance_score + f.student_support_score) < 50]
    total_risk_items = len(high_inc_ids) + len(risk_fto_ids)
    risk_covered = len([x for x in high_inc_ids + risk_fto_ids if x in all_assigned])
    computed_risk_reduction = risk_covered / total_risk_items if total_risk_items > 0 else 1.0
    score += 0.20 * computed_risk_reduction

    # If the strategy was successful, it must outscore the "Justified Caution" (0.35)
    return round(min(score, 1.0), 4)
