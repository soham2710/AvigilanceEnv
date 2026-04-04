# train.py — Advanced Training Pipeline with DataLoader and Validation
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import Dataset, DataLoader, random_split
import json
from pathlib import Path
from environment.avigilance_env import AvigilanceEnv
from environment.graders.grader2 import compute_priority_score
from pytorch_agent import AvigilanceRLAgent
import os

class FTODataset(Dataset):
    def __init__(self, data_path: str):
        with open(data_path, "r") as f:
            self.data = json.load(f)
        self.grades = ["A+", "A", "B", "C"]
        
    def __len__(self):
        return len(self.data)
        
    def __getitem__(self, idx):
        fto = self.data[idx]
        features = [
            fto["performance_score"] / 20.0, fto["operational_score"] / 40.0,
            fto["safety_score"] / 20.0, fto["compliance_score"] / 10.0,
            fto["student_support_score"] / 10.0, fto["pass_rate"],
            min(fto["recent_incidents"] / 10.0, 1.0),
            min(fto["solo_hours_per_student"] / 100.0, 1.0)
        ]
        features += [0.0] * (15 - len(features))
        target_grade = fto["_ground_truth"]["expected_grade"]
        target_idx = self.grades.index(target_grade)
        return torch.FloatTensor(features), torch.tensor(target_idx)

class IncidentDataset(Dataset):
    def __init__(self, data_path: str):
        with open(data_path, "r") as f:
            self.data = json.load(f)
            
    def __len__(self):
        # We'll treat each batch of 10-15 incidents as one training sequence
        return len(self.data) // 15
        
    def __getitem__(self, idx):
        start = idx * 10
        batch = self.data[start:start+10]
        
        batch_features = []
        true_priorities = []
        for i in batch:
            feats = [
                0.0, i["recurrence_count"] / 5.0, i["flights_per_day_at_airport"] / 1200.0,
                i["days_since_last_inspection"] / 365.0,
                1.0 if i["severity"] == "critical" else 0.5, 1.0 if i["is_resolved"] else 0.0,
                0.0, 0.0, 0.0, 0.0
            ]
            batch_features.append(feats)
            # Use compute_priority_score or a simple severity-based priority for ground truth
            p = 1.0 if i["severity"] == "critical" else 0.8 if i["severity"] == "high" else 0.5
            true_priorities.append(p)
            
        return torch.FloatTensor(batch_features), torch.FloatTensor(true_priorities)

def train_agent(epochs: int = 100, batch_size: int = 64):
    os.makedirs("models", exist_ok=True)
    agent = AvigilanceRLAgent()
    
    # --- Task 1 Training ---
    fto_data = FTODataset("data/fto_profiles.json")
    train_size = int(0.8 * len(fto_data))
    val_size = len(fto_data) - train_size
    fto_train, fto_val = random_split(fto_data, [train_size, val_size])
    
    train_loader = DataLoader(fto_train, batch_size=batch_size, shuffle=True)
    val_loader = DataLoader(fto_val, batch_size=batch_size)
    
    optimizer = optim.AdamW(agent.fto_model.parameters(), lr=1e-3, weight_decay=1e-5)
    criterion = nn.CrossEntropyLoss()
    scheduler = optim.lr_scheduler.ReduceLROnPlateau(optimizer, "min", patience=5)
    
    print(f"Training Task 1: {len(fto_train)} train, {len(fto_val)} val")
    best_val_loss = float("inf")
    
    for epoch in range(epochs):
        agent.fto_model.train()
        train_loss = 0.0
        for x, y in train_loader:
            optimizer.zero_grad()
            logits, _ = agent.fto_model(x)
            loss = criterion(logits, y)
            loss.backward()
            optimizer.step()
            train_loss += loss.item()
            
        agent.fto_model.eval()
        val_loss = 0.0
        with torch.no_grad():
            for x, y in val_loader:
                logits, _ = agent.fto_model(x)
                val_loss += criterion(logits, y).item()
        
        avg_train = train_loss / len(train_loader)
        avg_val = val_loss / len(val_loader)
        scheduler.step(avg_val)
        
        if avg_val < best_val_loss:
            best_val_loss = avg_val
            torch.save(agent.fto_model.state_dict(), "models/fto_grader_final.pth")
            
        if (epoch + 1) % 10 == 0:
            print(f"Epoch {epoch+1:03d} | Train Loss: {avg_train:.4f} | Val Loss: {avg_val:.4f}")

    # --- Task 2 Training ---
    inc_data = IncidentDataset("data/incident_reports.json")
    inc_train_size = int(0.8 * len(inc_data))
    inc_val_size = len(inc_data) - inc_train_size
    inc_train, inc_val = random_split(inc_data, [inc_train_size, inc_val_size])
    
    inc_train_loader = DataLoader(inc_train, batch_size=batch_size // 2, shuffle=True)
    inc_val_loader = DataLoader(inc_val, batch_size=batch_size // 2)
    
    optimizer_inc = optim.AdamW(agent.incident_model.parameters(), lr=5e-4)
    criterion_inc = nn.MSELoss()
    
    print(f"\nTraining Task 2: {len(inc_train)} train, {len(inc_val)} val")
    best_inc_val = float("inf")
    
    for epoch in range(epochs):
        agent.incident_model.train()
        train_loss = 0.0
        for x, y in inc_train_loader:
            optimizer_inc.zero_grad()
            preds = agent.incident_model(x)
            loss = criterion_inc(preds, y)
            loss.backward()
            optimizer_inc.step()
            train_loss += loss.item()
            
        agent.incident_model.eval()
        val_loss = 0.0
        with torch.no_grad():
            for x, y in inc_val_loader:
                preds = agent.incident_model(x)
                val_loss += criterion_inc(preds, y).item()
        
        avg_train = train_loss / len(inc_train_loader)
        avg_val = val_loss / len(inc_val_loader)
        
        if avg_val < best_inc_val:
            best_inc_val = avg_val
            torch.save(agent.incident_model.state_dict(), "models/incident_ranker_final.pth")
            
        if (epoch + 1) % 10 == 0:
            print(f"Epoch {epoch+1:03d} | Train Loss: {avg_train:.4f} | Val Loss: {avg_val:.4f}")

if __name__ == "__main__":
    train_agent(epochs=100) # Deeper model requires fewer epochs on larger data
