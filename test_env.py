import sys
import unittest
import json
import os
from pathlib import Path

# Fix path to allow importing from environment
sys.path.append(os.getcwd())

from environment.avigilance_env import AvigilanceEnv
from environment.models import AvigilanceAction

class TestAvigilanceEnv(unittest.TestCase):
    def test_imports(self):
        """Test that the environment and models can be imported."""
        from environment.avigilance_env import AvigilanceEnv
        from environment.models import AvigilanceObservation
        print("Imports: OK")

    def test_task1_reset(self):
        """Test resetting Task 1."""
        env = AvigilanceEnv(task_id="task1", seed=42)
        obs = env.reset()
        self.assertEqual(obs.task_id, "task1")
        self.assertIsNotNone(obs.fto_profile)
        print("Task 1 Reset: OK")

    def test_task2_reset(self):
        """Test resetting Task 2."""
        env = AvigilanceEnv(task_id="task2", seed=42)
        obs = env.reset()
        self.assertEqual(obs.task_id, "task2")
        self.assertIsNotNone(obs.incident_batch)
        self.assertGreaterEqual(len(obs.incident_batch), 8)
        print("Task 2 Reset: OK")

    def test_task3_reset(self):
        """Test resetting Task 3."""
        env = AvigilanceEnv(task_id="task3", seed=42)
        obs = env.reset()
        self.assertEqual(obs.task_id, "task3")
        self.assertIsNotNone(obs.fto_audit_queue)
        print("Task 3 Reset: OK")

    def test_task1_step(self):
        """Test taking a step in Task 1."""
        env = AvigilanceEnv(task_id="task1", seed=42)
        obs = env.reset()
        
        # Build a dummy action
        action_dict = {
            "task_id": "task1",
            "fto_grade_action": {
                "grade": "B",
                "total_score": 60.5,
                "risk_flags": ["insufficient_solo_hours"],
                "recommended_action": "self_assessment_required",
                "justification": "FTO shows borderline safety metrics and high grievance count."
            }
        }
        action = AvigilanceAction.model_validate(action_dict)
        obs, reward, done, info = env.step(action)
        
        self.assertTrue(done)
        self.assertGreaterEqual(reward.score, 0.0)
        self.assertLessEqual(reward.score, 1.0)
        print(f"Task 1 Step: OK (Reward: {reward.score})")

if __name__ == "__main__":
    unittest.main()
