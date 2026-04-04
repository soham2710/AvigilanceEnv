import os
import sys
import json
import subprocess
from pathlib import Path

def validate():
    print("AvigilanceEnv Pre-submission Validator")
    print("-" * 40)
    
    required_files = [
        "environment/avigilance_env.py",
        "environment/models.py",
        "environment/tasks/task1_fto_scorer.py",
        "environment/tasks/task2_incident_ranker.py",
        "environment/tasks/task3_resource_alloc.py",
        "environment/graders/grader1.py",
        "environment/graders/grader2.py",
        "environment/graders/grader3.py",
        "data/fto_profiles.json",
        "data/incident_reports.json",
        "app.py",
        "inference.py",
        "openenv.yaml",
        "Dockerfile",
        "requirements.txt",
        "README.md"
    ]
    
    errors = []
    for f in required_files:
        if not Path(f).exists():
            errors.append(f"Missing file: {f}")
        else:
            print(f"File found: {f}")
            
    if errors:
        print("\nValidation Failed!")
        for e in errors: print(f" - {e}")
        return False
        
    print("\nFile structure: OK")
    
    # Check if environment imports cleanly
    try:
        from environment.avigilance_env import AvigilanceEnv
        print("Environment imports: OK")
    except Exception as e:
        print(f"Environment import failed: {e}")
        return False
        
    # Check if openenv.yaml is valid (basic YAML check)
    try:
        import yaml
        with open("openenv.yaml", "r") as f:
            yaml.safe_load(f)
        print("openenv.yaml: OK")
    except Exception as e:
        print(f"openenv.yaml validation failed: {e}")
        return False
        
    print("\nValidation Successful! Repository is ready for submission.")
    return True

if __name__ == "__main__":
    if validate():
        sys.exit(0)
    else:
        sys.exit(1)
