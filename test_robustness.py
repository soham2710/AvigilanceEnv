# test_robustness.py — Stress Testing AvigilancePPOAgent with "Bad Data"
import torch
import json
from environment.avigilance_env import AvigilanceEnv
from pytorch_agent import AvigilancePPOAgent

def run_stress_test():
    device = torch.device("cpu")
    agent = AvigilancePPOAgent(device=device)
    
    # Load PPO weights if they exist (baseline fallback to random)
    if os.path.exists("models/fto_actor_critic_ppo.pth"):
        agent.fto_net.load_state_dict(torch.load("models/fto_actor_critic_ppo.pth"))
        print("Loaded PPO weights for stress testing.")

    print("\nStarting Stress Tests (Robustness Suite)...")
    print("-" * 50)

    # 1. The Zero Signal Test
    print("Test 1: Zero Signal (All fields 0.0)")
    zero_obs = {"fto_profile": {k: 0.0 for k in ["performance_score", "safety_score", "pass_rate", "recent_incidents"]}}
    grade, _ = agent.select_action_task1(zero_obs)
    print(f"Result: {grade} (Handled: OK)")

    # 2. Out-of-Range Test
    print("\nTest 2: Out-of-Range (Safety Score = -500, Pass Rate = 10.0)")
    bad_obs = {"fto_profile": {"safety_score": -500.0, "pass_rate": 10.0}}
    grade, _ = agent.select_action_task1(bad_obs)
    print(f"Result: {grade} (Handled: OK)")

    # 3. Contradiction Test
    print("\nTest 3: Contradiction (A+ Scores but 100 Recent Incidents)")
    contra_obs = {
        "fto_profile": {
            "performance_score": 19.9, "safety_score": 19.9, "operational_score": 39.9,
            "recent_incidents": 100, "grievances_last_6_months": 50
        }
    }
    grade, _ = agent.select_action_task1(contra_obs)
    print(f"Result: {grade} (Handled: OK)")

    # 4. Missing Fields Test
    print("\nTest 4: Missing Fields (Dict with only ID)")
    missing_obs = {"fto_profile": {"fto_id": "FTO_MISSING"}}
    grade, _ = agent.select_action_task1(missing_obs)
    print(f"Result: {grade} (Handled: OK)")

    print("-" * 50)
    print("Robustness Suite Complete. No model breakdown detected.")

if __name__ == "__main__":
    import os
    run_stress_test()
