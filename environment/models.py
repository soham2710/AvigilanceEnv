from pydantic import BaseModel, Field, field_validator
from typing import List, Dict, Optional, Literal
from enum import Enum
from .scoring import normalize_open_score

class IncidentSeverity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class FTOGrade(str, Enum):
    A_PLUS = "A+"
    A = "A"
    B = "B"
    C = "C"

class FTOProfile(BaseModel):
    fto_id: str
    name: str
    location: str
    # DGCA 5-parameter rubric (flexible for stress testing)
    performance_score: float  # Expected 0-20
    operational_score: float  # Expected 0-40
    safety_score: float       # Expected 0-20
    compliance_score: float    # Expected 0-10
    student_support_score: float # Expected 0-10
    total_students: int
    aircraft_count: int
    instructor_count: int
    recent_incidents: int
    solo_hours_per_student: float
    pass_rate: float          # Expected 0-1
    grievances_last_6_months: int

class IncidentReport(BaseModel):
    incident_id: str
    date: str
    airport_code: str  # DEL, BOM, BLR, MAA, HYD, CCU, COK, PNQ, AMD, JAI
    airline: str       # IndiGo, Air India, SpiceJet, Akasa, Air India Express
    incident_type: str # runway_incursion, technical_snag, atc_deviation,
                       # fdtl_violation, maintenance_lapse, bird_strike,
                       # fuel_irregularity, unauthorized_access
    severity: IncidentSeverity
    description: str
    recurrence_count: int  # How many times this pattern has occurred
    aircraft_type: str
    flights_per_day_at_airport: int
    days_since_last_inspection: int
    is_resolved: bool

class AvigilanceObservation(BaseModel):
    task_id: str  # "task1", "task2", "task3"
    episode_step: int
    max_steps: int
    # Task 1 specific
    fto_profile: Optional[FTOProfile] = None
    # Task 2 specific
    incident_batch: Optional[List[IncidentReport]] = None
    available_inspectors: Optional[int] = None
    # Task 3 specific
    fto_audit_queue: Optional[List[FTOProfile]] = None
    incident_queue: Optional[List[IncidentReport]] = None
    inspector_capacity: Optional[int] = None
    week_budget_hours: Optional[int] = None
    # Context always present
    dgca_current_vacancy_pct: float = 0.503  # Real: 843/1630 posts filled
    india_aviation_risk_level: str = "HIGH"
    context_note: str = ""

class FTOGradeAction(BaseModel):
    """Task 1 action: grade a single FTO"""
    grade: FTOGrade
    total_score: float = Field(ge=0.0, le=100.0)
    risk_flags: List[str]  # Specific issues identified
    recommended_action: Literal[
        "clear", "self_assessment_required", "dgca_notice_issued",
        "immediate_audit", "suspension_recommended"
    ]
    justification: str

    @field_validator('total_score')
    @classmethod
    def clamp_score(cls, v):
        return round(max(0.0, min(100.0, v)), 2)

class IncidentPriorityAction(BaseModel):
    """Task 2 action: rank incidents by urgency"""
    priority_ranking: List[str]  # List of incident_ids in priority order
    top_3_rationale: str  # Why top 3 are most urgent
    defer_list: List[str]  # incident_ids to defer
    escalate_immediately: List[str]  # incident_ids needing same-day response
    pattern_detected: bool
    pattern_description: Optional[str] = None

class ResourceAllocationAction(BaseModel):
    """Task 3 action: allocate inspectors to FTOs and incidents"""
    inspector_assignments: Dict[str, List[str]]
    # key: inspector_id, value: list of task_ids (fto_id or incident_id)
    deferred_items: List[str]  # Items not assigned this week
    priority_rationale: str
    predicted_risk_reduction: float = Field(ge=0.0, le=1.0)
    abstain: bool = False  # MGURM A1: Agent can abstain if insufficient data
    abstain_reason: Optional[str] = None

class AvigilanceAction(BaseModel):
    task_id: str
    fto_grade_action: Optional[FTOGradeAction] = None
    incident_priority_action: Optional[IncidentPriorityAction] = None
    resource_allocation_action: Optional[ResourceAllocationAction] = None

class AvigilanceReward(BaseModel):
    score: float = Field(ge=0.0, le=1.0)  # Final normalized score
    # Breakdown for interpretability
    accuracy_component: float = Field(ge=0.0, le=1.0)
    consistency_component: float = Field(ge=0.0, le=1.0)
    safety_alignment_component: float = Field(ge=0.0, le=1.0)
    justification_quality: float = Field(ge=0.0, le=1.0)
    # Safety principle compliance scores
    safety_principle_p1_transparency: float = Field(ge=0.0, le=1.0)
    safety_principle_p2_compliance: float = Field(ge=0.0, le=1.0)
    safety_principle_p3_consistency: float = Field(ge=0.0, le=1.0)
    feedback: str
    done: bool

    @field_validator('score')
    @classmethod
    def enforce_open_interval(cls, value: float) -> float:
        return normalize_open_score(value)
