# generate_data.py — Avigilance 2.0: Noisy, Imbalanced, Real-World Messy Data
# Design philosophy: the agent must learn from the worst real-world conditions —
# conflicting signals, near-boundary edge cases, deceptive patterns, severe
# class imbalance, and high noise. Easy clean data is not how DGCA works.
import json
import random
from pathlib import Path

random.seed(2026)
Path("data").mkdir(exist_ok=True)

INDIAN_AIRPORTS = [
    {"code": "DEL", "name": "Indira Gandhi Int.", "city": "Delhi", "flights_per_day": 1200},
    {"code": "BOM", "name": "Chhatrapati Shivaji Maharaj Int.", "city": "Mumbai", "flights_per_day": 980},
    {"code": "BLR", "name": "Kempegowda Int.", "city": "Bengaluru", "flights_per_day": 760},
    {"code": "HYD", "name": "Rajiv Gandhi Int.", "city": "Hyderabad", "flights_per_day": 480},
    {"code": "MAA", "name": "Chennai Int.", "city": "Chennai", "flights_per_day": 520},
    {"code": "CCU", "name": "Netaji Subhas Chandra Bose Int.", "city": "Kolkata", "flights_per_day": 380},
    {"code": "AMD", "name": "Sardar Vallabhbhai Patel Int.", "city": "Ahmedabad", "flights_per_day": 280},
    {"code": "COK", "name": "Cochin Int.", "city": "Kochi", "flights_per_day": 220},
    {"code": "PNQ", "name": "Pune Int.", "city": "Pune", "flights_per_day": 180},
    {"code": "GOI", "name": "Dabolim Airport", "city": "Goa", "flights_per_day": 120},
    {"code": "GOX", "name": "Manohar Int. (Mopa)", "city": "Goa", "flights_per_day": 110},
    {"code": "VNS", "name": "Lal Bahadur Shastri Int.", "city": "Varanasi", "flights_per_day": 85},
    {"code": "IDR", "name": "Devi Ahilyabai Holkar", "city": "Indore", "flights_per_day": 90},
    {"code": "BBI", "name": "Biju Patnaik Int.", "city": "Bhubaneswar", "flights_per_day": 75},
    {"code": "TRV", "name": "Trivandrum Int.", "city": "Thiruvananthapuram", "flights_per_day": 65},
    {"code": "CCJ", "name": "Calicut Int.", "city": "Kozhikode", "flights_per_day": 55},
    {"code": "JAI", "name": "Jaipur Int.", "city": "Jaipur", "flights_per_day": 140},
    {"code": "GAU", "name": "Lokpriya Gopinath Bordoloi Int.", "city": "Guwahati", "flights_per_day": 110},
    {"code": "PAT", "name": "Jay Prakash Narayan Int.", "city": "Patna", "flights_per_day": 95},
    {"code": "SXR", "name": "Srinagar Int.", "city": "Srinagar", "flights_per_day": 80},
]

AIRLINES = ["IndiGo", "Air India", "SpiceJet", "Akasa Air", "Air India Express", "Alliance Air", "Blue Dart"]

INCIDENT_TYPES = [
    "runway_incursion", "technical_snag", "atc_deviation", "fdtl_violation",
    "maintenance_lapse", "bird_strike", "fuel_irregularity", "unauthorized_access"
]

FTO_NAMES = [
    "IGRU — Indira Gandhi Rashtriya Uran Akademi (Rae Bareli)",
    "NFTI — National Flying Training Institute (Gondia)",
    "CAA — Chimes Aviation Academy (Sagar)",
    "Skynex Aero Training (Hyderabad)",
    "Ahmedabad Aviation Academy",
    "Bombay Flying Club (Mumbai)",
    "Delhi Flying Club",
    "Government Flying Training School (Jakkur)",
    "Madhya Pradesh Flying Club (Indore)",
    "Rajasthan State Flying School (Jaipur)",
    "Orient Flight Academy (Mysuru)",
    "Asia Pacific Flight Training (Hyderabad)",
    "Wings India Flying School",
    "Alchemist Aviation (Jamshedpur)",
    "Garg Aviations (Chandigarh)",
    "Ambitions Flying Club (Aligarh)",
    "Falcon Flying Academy (Faizabad)",
    "Flytech Aviation Academy",
    "Indira Gandhi Uran Akademi",
    "International Pioneer Flying Academy",
    "Jet Serve Aviation",
    "Karnal Aviation Club",
    "Ludhiana Aviation Club",
    "Patiala Aviation Club",
    "Pioneer Flying Academy",
    "Rajiv Gandhi Academy for Aviation Technology",
    "Seagull Aviation Academy",
    "Sha-Shib Flying Academy",
    "Silchar Flying Club",
    "Taneja Aerospace and Aviation",
]

# Noisy descriptions that don't always match the incident type — real-world ambiguity
NOISY_DESCRIPTIONS = [
    "ATC logged anomaly — details pending investigation.",
    "Crew report submitted; maintenance sign-off missing.",
    "Ground handler flagged; no DGCA form filed yet.",
    "Verbally reported by PIC — written report delayed 48h.",
    "Near-miss recorded on ACARS; severity disputed by airline.",
    "Routine check revealed historic lapse — date unclear.",
    "Alert triggered by automated system; human verification pending.",
    "Inspector noted deviation during ramp check.",
    "Third-party tip received; airline denies incident occurred.",
    "Flight data recorder anomaly; crew debriefed, no consensus.",
    "Reported by trainee — senior crew disputes account.",
    "Simultaneous incidents at adjacent stands; root cause unclear.",
    "Weather cited as mitigating factor; DGCA disagrees.",
    "Repeat occurrence — previous report closed prematurely.",
    "High-profile flight; political sensitivity flagged.",
]

def _get_flags(incidents, solo_hours, pass_rate, grievances):
    flags = []
    if incidents >= 3: flags.append("high_incident_rate")
    if solo_hours < 20: flags.append("insufficient_solo_hours")
    if pass_rate < 0.55: flags.append("low_pass_rate")
    if grievances >= 8: flags.append("excessive_student_grievances")
    if incidents >= 5: flags.append("safety_critical")
    return flags

def _get_action(grade):
    return {"A+": "clear", "A": "clear", "B": "self_assessment_required", "C": "dgca_notice_issued"}[grade]

def _get_acceptable_actions(grade):
    return {"A+": ["clear"], "A": ["clear", "self_assessment_required"],
            "B": ["self_assessment_required", "dgca_notice_issued"],
            "C": ["dgca_notice_issued", "immediate_audit"]}[grade]


def make_fto(idx: int, target_grade: str) -> dict:
    """Generate FTO profile with intentional noise and conflicting signals."""
    name = FTO_NAMES[idx % len(FTO_NAMES)]
    noise = random.random()  # used to inject adversarial/conflicting cases

    if target_grade == "A+":
        # Mostly clean but occasional near-boundary case
        if noise < 0.15:  # 15% near-boundary: just above 90 threshold
            perf = random.uniform(17.5, 18.5)
            ops = random.uniform(36, 37)
            safety = random.uniform(17.5, 18.5)
            compliance = random.uniform(8.5, 9)
            student = random.uniform(8.5, 9)
        else:
            perf = random.uniform(18, 20)
            ops = random.uniform(36, 40)
            safety = random.uniform(18, 20)
            compliance = random.uniform(9, 10)
            student = random.uniform(9, 10)
        incidents = 0
        solo_hours = random.uniform(50, 70)
        pass_rate = random.uniform(0.85, 0.98)
        grievances = random.randint(0, 1)

    elif target_grade == "A":
        perf = random.uniform(14, 18)
        ops = random.uniform(28, 36)
        safety = random.uniform(14, 18)
        compliance = random.uniform(7, 9)
        student = random.uniform(7, 9)
        incidents = random.randint(0, 1)
        solo_hours = random.uniform(38, 52)
        pass_rate = random.uniform(0.72, 0.87)
        grievances = random.randint(1, 4)
        # Conflicting signal: good scores but borderline incidents
        if noise < 0.20:
            incidents = 2  # pushes toward B but scores say A
            pass_rate = random.uniform(0.76, 0.85)

    elif target_grade == "B":
        perf = random.uniform(8, 15)
        ops = random.uniform(16, 30)
        safety = random.uniform(8, 15)
        compliance = random.uniform(4, 7.5)
        student = random.uniform(4, 7.5)
        incidents = random.randint(1, 4)
        solo_hours = random.uniform(18, 42)
        pass_rate = random.uniform(0.55, 0.76)
        grievances = random.randint(2, 8)
        # Near-boundary: score hovers at 50 ± 3
        if noise < 0.30:
            delta = random.uniform(-3, 3)
            adj = delta / 5
            perf += adj; ops += adj * 2; safety += adj; compliance += adj * 0.5; student += adj * 0.5

    else:  # C — dominant class (real DGCA reality: zero A/A+ FTOs as of 2025)
        profile_type = random.choices(
            ["failing", "near_boundary", "conflicting", "ghost_fto"],
            [50, 25, 15, 10]
        )[0]

        if profile_type == "failing":
            perf = random.uniform(1, 8)
            ops = random.uniform(3, 16)
            safety = random.uniform(1, 8)
            compliance = random.uniform(0.5, 4)
            student = random.uniform(0.5, 4)
            incidents = random.randint(4, 15)
            solo_hours = random.uniform(3, 18)
            pass_rate = random.uniform(0.15, 0.55)
            grievances = random.randint(8, 25)

        elif profile_type == "near_boundary":
            # Just below C/B threshold (total ~47-52, scores say B but incidents say C)
            perf = random.uniform(9, 11)
            ops = random.uniform(18, 22)
            safety = random.uniform(9, 11)
            compliance = random.uniform(4.5, 5.5)
            student = random.uniform(4.5, 5.5)
            incidents = random.randint(3, 5)  # >= 3 forces C grade
            solo_hours = random.uniform(22, 30)
            pass_rate = random.uniform(0.58, 0.68)
            grievances = random.randint(6, 10)

        elif profile_type == "conflicting":
            # Deceptive: great pass_rate / compliance but dangerous safety record
            perf = random.uniform(5, 12)
            ops = random.uniform(8, 20)
            safety = random.uniform(1, 6)  # safety disaster
            compliance = random.uniform(7, 9)  # compliance looks good
            student = random.uniform(7, 9)   # student support looks good
            incidents = random.randint(5, 12)
            solo_hours = random.uniform(30, 55)  # solo hours fine
            pass_rate = random.uniform(0.75, 0.90)  # pass rate fine — misleading!
            grievances = random.randint(0, 3)

        else:  # ghost_fto: zero students, zero aircraft, still registered
            perf = random.uniform(0, 3)
            ops = random.uniform(0, 5)
            safety = random.uniform(0, 3)
            compliance = random.uniform(0, 2)
            student = random.uniform(0, 2)
            incidents = random.randint(0, 2)  # no incidents because no flights!
            solo_hours = 0.0
            pass_rate = 0.0  # no students to pass
            grievances = random.randint(0, 2)

    total = perf + ops + safety + compliance + student
    return {
        "fto_id": f"FTO_{idx:04d}",
        "name": f"{name} #{idx}",
        "location": "India",
        "performance_score": round(perf, 2),
        "operational_score": round(ops, 2),
        "safety_score": round(safety, 2),
        "compliance_score": round(compliance, 2),
        "student_support_score": round(student, 2),
        "total_students": random.randint(0, 200),
        "aircraft_count": random.randint(0, 20),
        "instructor_count": random.randint(0, 15),
        "recent_incidents": incidents,
        "solo_hours_per_student": round(solo_hours, 1),
        "pass_rate": round(pass_rate, 3),
        "grievances_last_6_months": grievances,
        "_ground_truth": {
            "expected_grade": target_grade,
            "true_score": round(total, 2),
            "expected_flags": _get_flags(incidents, solo_hours, pass_rate, grievances),
            "expected_action": _get_action(target_grade),
            "acceptable_actions": _get_acceptable_actions(target_grade),
        }
    }


def make_incident(idx: int) -> dict:
    """Generate incident with noise, edge cases, and adversarial patterns."""
    airport = random.choice(INDIAN_AIRPORTS)
    inc_type = random.choice(INCIDENT_TYPES)
    airline = random.choice(AIRLINES)

    # Heavily imbalanced severity — most incidents are low/medium (realistic)
    # Critical events are rare; the agent must not miss them
    severity = random.choices(
        ["low", "medium", "high", "critical"],
        [40, 35, 18, 7]
    )[0]

    # Extreme recurrence values — some never recur (0), some are chronic (15+)
    recurrence_profile = random.choices(
        ["zero", "low", "moderate", "chronic", "extreme"],
        [25, 30, 25, 15, 5]
    )[0]
    recurrence_map = {
        "zero": 0,
        "low": random.randint(1, 2),
        "moderate": random.randint(3, 6),
        "chronic": random.randint(7, 12),
        "extreme": random.randint(13, 25),
    }
    recurrence = recurrence_map[recurrence_profile]

    # Inspection staleness — many Indian airports have very stale inspections
    days_since = random.choices(
        [random.randint(1, 30), random.randint(31, 180),
         random.randint(181, 500), random.randint(501, 1500)],
        [20, 35, 30, 15]
    )[0]

    # Resolved but high severity — deceptive: agent must still flag
    is_resolved = random.random() < (0.70 if severity in ("low", "medium") else 0.15)

    # Noisy description that may contradict the incident type
    description = random.choice(NOISY_DESCRIPTIONS)

    return {
        "incident_id": f"INC_{idx:05d}",
        "date": f"2025-{random.randint(1, 12):02d}-{random.randint(1, 28):02d}",
        "airport_code": airport["code"],
        "airline": airline,
        "incident_type": inc_type,
        "severity": severity,
        "description": description,
        "recurrence_count": recurrence,
        "aircraft_type": random.choice(["A320", "B737", "ATR72", "Q400", "A321", "B777"]),
        "flights_per_day_at_airport": airport["flights_per_day"],
        "days_since_last_inspection": days_since,
        "is_resolved": is_resolved,
    }


# ── FTO Profiles ─────────────────────────────────────────────────────────────
# Real DGCA distribution: ~65% C, 22% B, 10% A, 3% A+
# (As of Sep 2025: 0 A/A+ rated FTOs in India — we include a tiny fraction
#  for evaluation completeness, but the dataset is C-heavy as reality demands)
ftos = []
for i in range(1000):
    grade = random.choices(["A+", "A", "B", "C"], [3, 10, 22, 65])[0]
    ftos.append(make_fto(i, grade))
with open("data/fto_profiles.json", "w") as f:
    json.dump(ftos, f, indent=2)

# ── Incident Reports ──────────────────────────────────────────────────────────
# 8000 incidents: rare critical events buried in noise,
# chronic recurrence patterns, stale inspections, deceptive descriptions
incidents = [make_incident(idx) for idx in range(8000)]
with open("data/incident_reports.json", "w") as f:
    json.dump(incidents, f, indent=2)

# ── Resource Scenarios ────────────────────────────────────────────────────────
# Deliberately underfunded: inspector capacity always too low to cover everything.
# Agent must prioritise, not just assign everything.
scenarios = []
for idx in range(150):
    # Always pick more work items than can reasonably be handled
    n_ftos = random.randint(8, 20)
    n_incs = random.randint(10, 25)
    inspectors = random.randint(1, 4)   # intentionally few
    # Budget is tight: enough for ~40-60% of all items
    total_items = n_ftos + n_incs
    tight_budget = random.randint(
        int(total_items * 3),    # can cover ~30% (very tight)
        int(total_items * 6)     # can cover ~60% (moderate)
    )
    scenarios.append({
        "scenario_id": f"SCEN_{idx:03d}",
        "fto_ids": [f["fto_id"] for f in random.sample(ftos, n_ftos)],
        "incident_ids": [i["incident_id"] for i in random.sample(incidents, n_incs)],
        "inspector_capacity": inspectors,
        "week_budget_hours": tight_budget,
    })
with open("data/resource_scenarios.json", "w") as f:
    json.dump(scenarios, f, indent=2)

# ── Stats ─────────────────────────────────────────────────────────────────────
from collections import Counter
grade_dist = Counter(f["_ground_truth"]["expected_grade"] for f in ftos)
sev_dist = Counter(i["severity"] for i in incidents)
recur_zero = sum(1 for i in incidents if i["recurrence_count"] == 0)
recur_extreme = sum(1 for i in incidents if i["recurrence_count"] >= 13)
critical_resolved = sum(1 for i in incidents if i["severity"] == "critical" and i["is_resolved"])
print("Avigilance 2.0 Noisy Data Generation Complete.")
print(f"  FTO grades:      {dict(sorted(grade_dist.items()))}")
print(f"  Incident sev:    {dict(sorted(sev_dist.items()))}")
print(f"  Recurrence=0:    {recur_zero} | Extreme(>=13): {recur_extreme}")
print(f"  Critical+resolved (deceptive): {critical_resolved}")
print(f"  Scenarios:       {len(scenarios)} (underfunded, forced prioritisation)")
