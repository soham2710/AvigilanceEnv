# generate_data.py — Scaled Avigilance 2.0: Real Data & Bizarre Conditions
import json
import random
from pathlib import Path

random.seed(2026)
Path("data").mkdir(exist_ok=True)

# Expanded Indian Airports (Real IATA codes and Hub contexts)
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

# Real/Realistic Indian FTOs
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
    name = FTO_NAMES[idx % len(FTO_NAMES)]
    if target_grade == "A+":
        perf, ops, safety, compliance, student = random.uniform(18, 20), random.uniform(36, 40), random.uniform(18, 20), random.uniform(9, 10), random.uniform(9, 10)
        incidents, solo_hours, pass_rate, grievances = 0, random.uniform(50, 70), random.uniform(0.85, 0.98), random.randint(0, 1)
    elif target_grade == "A":
        perf, ops, safety, compliance, student = random.uniform(15, 18), random.uniform(30, 36), random.uniform(15, 18), random.uniform(7.5, 9), random.uniform(7.5, 9)
        incidents, solo_hours, pass_rate, grievances = random.randint(0, 1), random.uniform(40, 50), random.uniform(0.75, 0.85), random.randint(1, 3)
    elif target_grade == "B":
        perf, ops, safety, compliance, student = random.uniform(10, 15), random.uniform(20, 30), random.uniform(10, 15), random.uniform(5, 7.5), random.uniform(5, 7.5)
        incidents, solo_hours, pass_rate, grievances = random.randint(1, 3), random.uniform(25, 40), random.uniform(0.60, 0.75), random.randint(3, 7)
    else:
        perf, ops, safety, compliance, student = random.uniform(2, 10), random.uniform(5, 20), random.uniform(2, 10), random.uniform(1, 5), random.uniform(1, 5)
        incidents, solo_hours, pass_rate, grievances = random.randint(3, 10), random.uniform(5, 25), random.uniform(0.30, 0.60), random.randint(7, 20)

    total = perf + ops + safety + compliance + student
    return {
        "fto_id": f"FTO_{idx:04d}", "name": f"{name} #{idx}", "location": "India",
        "performance_score": round(perf, 2), "operational_score": round(ops, 2),
        "safety_score": round(safety, 2), "compliance_score": round(compliance, 2),
        "student_support_score": round(student, 2), "total_students": random.randint(20, 200),
        "aircraft_count": random.randint(2, 20), "instructor_count": random.randint(2, 15),
        "recent_incidents": incidents, "solo_hours_per_student": round(solo_hours, 1),
        "pass_rate": round(pass_rate, 3), "grievances_last_6_months": grievances,
        "_ground_truth": {
            "expected_grade": target_grade, "true_score": round(total, 2),
            "expected_flags": _get_flags(incidents, solo_hours, pass_rate, grievances),
            "expected_action": _get_action(target_grade), "acceptable_actions": _get_acceptable_actions(target_grade)
        }
    }

# Generate Data
ftos = []
for i in range(1000):
    grade = random.choices(["A+", "A", "B", "C"], [10, 20, 30, 40])[0]
    ftos.append(make_fto(i, grade))
with open("data/fto_profiles.json", "w") as f: json.dump(ftos, f, indent=2)

incidents = []
for idx in range(5000):
    airport = random.choice(INDIAN_AIRPORTS)
    inc_type = random.choice(INCIDENT_TYPES)
    airline = random.choice(AIRLINES)
    incidents.append({
        "incident_id": f"INC_{idx:05d}", "date": f"2025-{random.randint(1,12):02d}-{random.randint(1,28):02d}",
        "airport_code": airport["code"], "airline": airline, "incident_type": inc_type,
        "severity": random.choices(["low", "medium", "high", "critical"], [15, 35, 35, 15])[0],
        "description": f"Stress report: {inc_type} at {airport['name']}.",
        "recurrence_count": random.randint(0, 10), "aircraft_type": random.choice(["A320", "B737"]),
        "flights_per_day_at_airport": airport["flights_per_day"], "days_since_last_inspection": random.randint(1, 1000),
        "is_resolved": random.random() > 0.5,
    })
with open("data/incident_reports.json", "w") as f: json.dump(incidents, f, indent=2)

scenarios = []
for idx in range(100):
    scenarios.append({"scenario_id": f"SCEN_{idx:03d}", "fto_ids": [f["fto_id"] for f in random.sample(ftos, 10)], "incident_ids": [i["incident_id"] for i in random.sample(incidents, 30)], "inspector_capacity": random.randint(1, 10), "week_budget_hours": random.randint(40, 200)})
with open("data/resource_scenarios.json", "w") as f: json.dump(scenarios, f, indent=2)

print("Avigilance 2.0 Data Generation Complete (Real Airports, FTOs, and Incidents).")
