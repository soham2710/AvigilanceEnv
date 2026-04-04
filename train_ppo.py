# train_ppo.py — Rigorous PPO Training for AvigilanceEnv
import torch
import torch.nn as nn
import torch.optim as optim
from torch.distributions import Categorical
import numpy as np
from environment.avigilance_env import AvigilanceEnv
from pytorch_agent import AvigilancePPOAgent
import os
from copy import deepcopy

# Hyper-parameters
LEARNING_RATE = 3e-4
GAMMA = 0.99
EPS_CLIP = 0.2
K_EPOCHS = 4
ENTROPY_BETA = 0.01
EARLY_STOP_REWARD = 0.85
MAX_EPISODES = 1000

class PPOBuffer:
    def __init__(self):
        self.states = []
        self.actions = []
        self.logprobs = []
        self.rewards = []
        self.is_terminals = []

    def clear(self):
        del self.states[:]
        del self.actions[:]
        del self.logprobs[:]
        del self.rewards[:]
        del self.is_terminals[:]

def train_ppo():
    device = torch.device("cpu")
    agent = AvigilancePPOAgent(device=device)
    optimizer = optim.Adam(agent.fto_net.parameters(), lr=LEARNING_RATE)
    # Cosine Annealing Scheduler as requested
    scheduler = optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=MAX_EPISODES)
    
    buffer = PPOBuffer()
    env = AvigilanceEnv(task_id="task1", seed=42)
    
    print("Starting Rigorous PPO Training for Task 1...")
    print(f"Early Stopping Target: {EARLY_STOP_REWARD}")
    
    best_reward = -float("inf")
    
    for episode in range(1, MAX_EPISODES + 1):
        state_obs = env.reset()
        state_fto = state_obs.fto_profile.model_dump()
        
        # Preprocess features (same as agent select_action)
        def safe_norm(val, scale):
            v = float(val) if val is not None else 0.0
            return v / scale

        features = [
            safe_norm(state_fto.get("performance_score"), 20.0),
            safe_norm(state_fto.get("operational_score"), 40.0),
            safe_norm(state_fto.get("safety_score"), 20.0),
            safe_norm(state_fto.get("compliance_score"), 10.0),
            safe_norm(state_fto.get("student_support_score"), 10.0),
            safe_norm(state_fto.get("pass_rate"), 1.0),
            min(safe_norm(state_fto.get("recent_incidents"), 10.0), 1.0),
            min(safe_norm(state_fto.get("solo_hours_per_student"), 100.0), 1.0),
            1.0 if state_fto.get("total_students", 0) > 100 else 0.5,
            1.0 if state_fto.get("instructor_count", 0) > 10 else 0.5
        ]
        features += [0.0] * (15 - len(features))
        state_tensor = torch.FloatTensor(features).to(device).unsqueeze(0)
        
        # Policy acting
        logits, state_val = agent.fto_net(state_tensor)
        probs = torch.softmax(logits, dim=-1)
        dist = Categorical(probs)
        action = dist.sample()
        action_logprob = dist.log_prob(action)
        
        # Step environment
        from environment.models import AvigilanceAction, FTOGradeAction
        grade = ["A+", "A", "B", "C"][action.item()]
        env_action = AvigilanceAction(
            task_id="task1",
            fto_grade_action=FTOGradeAction(
                grade=grade,
                total_score=sum([v for k,v in state_fto.items() if "score" in k and isinstance(v, (int, float))]),
                risk_flags=["high_incident_rate"] if state_fto.get("recent_incidents", 0) > 3 else [],
                recommended_action="clear" if grade in ["A", "A+"] else "dgca_notice_issued",
                justification="PPO Training Loop."
            )
        )
        _, reward_obj, done, _ = env.step(env_action)
        reward = reward_obj.score
        
        # Push to buffer
        buffer.states.append(state_tensor)
        buffer.actions.append(action)
        buffer.logprobs.append(action_logprob)
        buffer.rewards.append(reward)
        buffer.is_terminals.append(done)
        
        # Update PPO
        if episode % 10 == 0:
            # Monte Carlo Returns
            rewards = []
            discounted_reward = 0
            for r, is_term in zip(reversed(buffer.rewards), reversed(buffer.is_terminals)):
                if is_term: discounted_reward = 0
                discounted_reward = r + (GAMMA * discounted_reward)
                rewards.insert(0, discounted_reward)
            
            rewards = torch.tensor(rewards, dtype=torch.float32).to(device)
            # Normalize rewards
            rewards = (rewards - rewards.mean()) / (rewards.std() + 1e-7)
            
            old_states = torch.cat(buffer.states).detach()
            old_actions = torch.cat(buffer.actions).detach()
            old_logprobs = torch.cat(buffer.logprobs).detach()
            
            for _ in range(K_EPOCHS):
                logits, state_values = agent.fto_net(old_states)
                probs = torch.softmax(logits, dim=-1)
                dist = Categorical(probs)
                logprobs = dist.log_prob(old_actions)
                dist_entropy = dist.entropy()
                state_values = torch.squeeze(state_values)
                
                # Ratios for clipping
                ratios = torch.exp(logprobs - old_logprobs)
                
                # Advantages
                advantages = rewards - state_values.detach()
                surr1 = ratios * advantages
                surr2 = torch.clamp(ratios, 1-EPS_CLIP, 1+EPS_CLIP) * advantages
                
                # Loss
                loss = -torch.min(surr1, surr2) + 0.5 * nn.MSELoss()(state_values, rewards) - ENTROPY_BETA * dist_entropy
                
                optimizer.zero_grad()
                loss.mean().backward()
                # Gradient Clipping for robustness
                nn.utils.clip_grad_norm_(agent.fto_net.parameters(), 1.0)
                optimizer.step()
                
            buffer.clear()
            scheduler.step()

        # Logging & Early Stopping
        if episode % 100 == 0:
            avg_reward = np.mean(buffer.rewards[-100:] if buffer.rewards else [reward])
            print(f"Episode {episode:04d} | Avg Reward: {avg_reward:.4f} | LR: {scheduler.get_last_lr()[0]:.6f}")
            
            if avg_reward > EARLY_STOP_REWARD:
                print(f"Target reward reached! Early stopping at {episode}.")
                break
                
            if avg_reward > best_reward:
                best_reward = avg_reward
                os.makedirs("models", exist_ok=True)
                torch.save(agent.fto_net.state_dict(), "models/fto_actor_critic_ppo.pth")

    print(f"Training Complete. Best Mean Reward: {best_reward:.4f}")

if __name__ == "__main__":
    train_ppo()
