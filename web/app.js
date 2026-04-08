const healthStatus = document.getElementById("healthStatus");
const metadataStatus = document.getElementById("metadataStatus");
const sessionStatus = document.getElementById("sessionStatus");
const observationView = document.getElementById("observationView");
const resultView = document.getElementById("resultView");
const actionInput = document.getElementById("actionInput");
const taskSelect = document.getElementById("taskSelect");
const seedInput = document.getElementById("seedInput");

function pretty(value) {
  return JSON.stringify(value, null, 2);
}

function defaultAction(taskId, observation) {
  if (!observation) {
    return { task_id: taskId };
  }

  if (taskId === "task1" && observation.fto_profile) {
    const fto = observation.fto_profile;
    const total = Number((
      fto.performance_score +
      fto.operational_score +
      fto.safety_score +
      fto.compliance_score +
      fto.student_support_score
    ).toFixed(2));

    return {
      task_id: "task1",
      fto_grade_action: {
        grade: total >= 75 ? "A" : total >= 50 ? "B" : "C",
        total_score: total,
        risk_flags: [],
        recommended_action: total >= 75 ? "clear" : "self_assessment_required",
        justification: "Frontend example action generated from the visible FTO profile."
      }
    };
  }

  if (taskId === "task2" && observation.incident_batch) {
    const ids = observation.incident_batch.map((item) => item.incident_id);
    return {
      task_id: "task2",
      incident_priority_action: {
        priority_ranking: ids,
        top_3_rationale: "Example ranking generated in the Space frontend.",
        defer_list: ids.slice(3),
        escalate_immediately: ids.slice(0, 2),
        pattern_detected: false,
        pattern_description: null
      }
    };
  }

  if (taskId === "task3") {
    const incidentIds = (observation.incident_queue || []).map((item) => item.incident_id);
    const ftoIds = (observation.fto_audit_queue || []).map((item) => item.fto_id);
    const allItems = incidentIds.concat(ftoIds);
    return {
      task_id: "task3",
      resource_allocation_action: {
        inspector_assignments: {
          inspector_1: allItems.slice(0, 2),
          inspector_2: allItems.slice(2, 4)
        },
        deferred_items: allItems.slice(4),
        priority_rationale: "Example allocation generated in the Space frontend.",
        predicted_risk_reduction: 0.55,
        abstain: false,
        abstain_reason: null
      }
    };
  }

  return { task_id: taskId };
}

async function fetchJson(url, options = {}) {
  const response = await fetch(url, options);
  const data = await response.json();
  if (!response.ok) {
    throw new Error(pretty(data));
  }
  return data;
}

async function refreshStatus() {
  try {
    const [health, metadata] = await Promise.all([
      fetchJson("/health"),
      fetchJson("/metadata")
    ]);
    healthStatus.textContent = health.status;
    metadataStatus.textContent = `${metadata.name} v${metadata.version}`;
  } catch (error) {
    healthStatus.textContent = "Unavailable";
    metadataStatus.textContent = String(error.message || error);
  }
}

async function resetEpisode() {
  const taskId = taskSelect.value;
  const seed = Number(seedInput.value || 42);
  const observation = await fetchJson(`/reset?task_id=${taskId}&seed=${seed}`, { method: "POST" });
  observationView.textContent = pretty(observation);
  actionInput.value = pretty(defaultAction(taskId, observation));
  sessionStatus.textContent = `${taskId} seeded with ${seed}`;
  resultView.textContent = "Episode reset successfully.";
}

async function submitAction() {
  let payload;
  try {
    payload = JSON.parse(actionInput.value);
  } catch (error) {
    resultView.textContent = `Action JSON parse error:\n${error.message}`;
    return;
  }

  try {
    const result = await fetchJson("/step", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
    observationView.textContent = pretty(result.observation);
    resultView.textContent = pretty(result);
    sessionStatus.textContent = result.done ? "Episode completed" : "Episode active";
  } catch (error) {
    resultView.textContent = `Step failed:\n${error.message}`;
  }
}

async function fetchState() {
  const taskId = taskSelect.value;
  try {
    const state = await fetchJson(`/state?task_id=${taskId}`);
    resultView.textContent = pretty(state);
  } catch (error) {
    resultView.textContent = `State fetch failed:\n${error.message}`;
  }
}

document.getElementById("refreshStatus").addEventListener("click", refreshStatus);
document.getElementById("resetEpisode").addEventListener("click", resetEpisode);
document.getElementById("submitAction").addEventListener("click", submitAction);
document.getElementById("fetchState").addEventListener("click", fetchState);
document.getElementById("loadExample").addEventListener("click", () => {
  let observation = null;
  try {
    observation = JSON.parse(observationView.textContent);
  } catch (error) {
    observation = null;
  }
  actionInput.value = pretty(defaultAction(taskSelect.value, observation));
});

taskSelect.addEventListener("change", () => {
  actionInput.value = pretty(defaultAction(taskSelect.value, null));
});

refreshStatus();
actionInput.value = pretty(defaultAction(taskSelect.value, null));