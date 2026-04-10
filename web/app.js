const healthStatus = document.getElementById("healthStatus");
const healthDetail = document.getElementById("healthDetail");
const metadataStatus = document.getElementById("metadataStatus");
const sessionStatus = document.getElementById("sessionStatus");
const sessionDetail = document.getElementById("sessionDetail");
const observationView = document.getElementById("observationView");
const resultView = document.getElementById("resultView");
const actionInput = document.getElementById("actionInput");
const taskSelect = document.getElementById("taskSelect");
const seedInput = document.getElementById("seedInput");
const taskTitle = document.getElementById("taskTitle");
const taskDescription = document.getElementById("taskDescription");
const rewardSummary = document.getElementById("rewardSummary");
const doneSummary = document.getElementById("doneSummary");
const observationSummary = document.getElementById("observationSummary");
const resultBadge = document.getElementById("resultBadge");
const timeline = document.getElementById("timeline");
const taskCards = Array.from(document.querySelectorAll(".task-card"));

const TASK_META = {
  task1: {
    title: "task1 · FTO Quality Scorer",
    description: "Grade a Flying Training Organisation against the DGCA rubric and recommend action."
  },
  task2: {
    title: "task2 · Incident Prioritiser",
    description: "Rank active incidents by operational urgency and identify escalation candidates."
  },
  task3: {
    title: "task3 · Resource Allocator",
    description: "Allocate inspection bandwidth across incidents and FTO audits under time constraints."
  }
};

function pretty(value) {
  return JSON.stringify(value, null, 2);
}

function setBadge(label, tone = "") {
  resultBadge.textContent = label;
  resultBadge.className = `status-pill${tone ? ` ${tone}` : ""}`;
}

function pushTimeline(tag, message) {
  const item = document.createElement("li");
  item.innerHTML = `<span class="timeline-tag">${tag}</span><p>${message}</p>`;
  timeline.prepend(item);

  while (timeline.children.length > 6) {
    timeline.removeChild(timeline.lastElementChild);
  }
}

function setTask(taskId) {
  const meta = TASK_META[taskId];
  taskSelect.value = taskId;
  taskTitle.textContent = meta.title;
  taskDescription.textContent = meta.description;

  taskCards.forEach((card) => {
    card.classList.toggle("is-active", card.dataset.task === taskId);
  });
}

function summarizeObservation(taskId, observation) {
  if (!observation) {
    return "No observation loaded";
  }

  if (taskId === "task1" && observation.fto_profile) {
    const fto = observation.fto_profile;
    return `${fto.fto_name} · pass rate ${fto.pass_rate} · incidents ${fto.recent_incidents}`;
  }

  if (taskId === "task2" && observation.incident_batch) {
    return `${observation.incident_batch.length} incidents in the current triage batch`;
  }

  if (taskId === "task3") {
    const incidents = (observation.incident_queue || []).length;
    const ftos = (observation.fto_audit_queue || []).length;
    return `${incidents} incidents and ${ftos} FTO audits competing for inspectors`;
  }

  return "Observation loaded";
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
    healthDetail.textContent = "Environment is reachable and ready for task resets.";
    metadataStatus.textContent = `${metadata.name} v${metadata.version}`;
    setBadge("Service reachable", "ok");
    pushTimeline("status", `Health check passed for ${metadata.name} ${metadata.version}.`);
  } catch (error) {
    healthStatus.textContent = "Unavailable";
    metadataStatus.textContent = String(error.message || error);
    healthDetail.textContent = "Health or metadata endpoint failed.";
    setBadge("Service issue", "error");
    pushTimeline("error", `Status refresh failed: ${String(error.message || error)}`);
  }
}

async function resetEpisode() {
  const taskId = taskSelect.value;
  const seed = Number(seedInput.value || 42);
  try {
    const observation = await fetchJson(`/reset?task_id=${taskId}&seed=${seed}`, { method: "POST" });
    observationView.textContent = pretty(observation);
    actionInput.value = pretty(defaultAction(taskId, observation));
    observationSummary.textContent = summarizeObservation(taskId, observation);
    rewardSummary.textContent = "Awaiting first step";
    doneSummary.textContent = "Episode active";
    sessionStatus.textContent = `${taskId} seeded with ${seed}`;
    sessionDetail.textContent = "Example action payload loaded and ready for editing.";
    resultView.textContent = pretty({ event: "reset", task_id: taskId, seed, status: "ready" });
    setBadge("Episode ready", "ok");
    pushTimeline("reset", `Started ${taskId} with deterministic seed ${seed}.`);
  } catch (error) {
    resultView.textContent = `Reset failed:\n${error.message}`;
    setBadge("Reset failed", "error");
    pushTimeline("error", `Reset failed for ${taskId}: ${String(error.message || error)}`);
  }
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
    sessionDetail.textContent = result.done ? "The environment reported a completed episode." : "A further step may still be available for this task.";
    observationSummary.textContent = summarizeObservation(payload.task_id, result.observation);
    rewardSummary.textContent = `${result.reward.score}`;
    doneSummary.textContent = result.done ? "Done" : "In progress";
    setBadge(result.done ? "Step complete" : "Step accepted", result.done ? "ok" : "warn");
    pushTimeline("step", `Submitted ${payload.task_id}; reward score ${result.reward.score}; done=${result.done}.`);
  } catch (error) {
    resultView.textContent = `Step failed:\n${error.message}`;
    setBadge("Step failed", "error");
    pushTimeline("error", `Step request failed: ${String(error.message || error)}`);
  }
}

async function fetchState() {
  const taskId = taskSelect.value;
  try {
    const state = await fetchJson(`/state?task_id=${taskId}`);
    resultView.textContent = pretty(state);
    doneSummary.textContent = state.done ? "Done" : "State fetched";
    sessionDetail.textContent = `Fetched state for ${taskId}.`;
    setBadge("State fetched", "warn");
    pushTimeline("state", `Fetched live state for ${taskId}.`);
  } catch (error) {
    resultView.textContent = `State fetch failed:\n${error.message}`;
    setBadge("State failed", "error");
    pushTimeline("error", `State fetch failed for ${taskId}: ${String(error.message || error)}`);
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
  setBadge("Example action loaded", "warn");
  pushTimeline("draft", `Loaded example payload for ${taskSelect.value}.`);
});

taskSelect.addEventListener("change", () => {
  setTask(taskSelect.value);
  actionInput.value = pretty(defaultAction(taskSelect.value, null));
  observationSummary.textContent = "Task changed; reset to load live observation";
  rewardSummary.textContent = "None yet";
  doneSummary.textContent = "Idle";
  sessionDetail.textContent = `Ready to reset ${taskSelect.value}.`;
});

taskCards.forEach((card) => {
  card.addEventListener("click", () => {
    setTask(card.dataset.task);
    actionInput.value = pretty(defaultAction(card.dataset.task, null));
    observationSummary.textContent = "Task changed; reset to load live observation";
    rewardSummary.textContent = "None yet";
    doneSummary.textContent = "Idle";
    sessionDetail.textContent = `Ready to reset ${card.dataset.task}.`;
  });
});

setTask(taskSelect.value);
refreshStatus();
actionInput.value = pretty(defaultAction(taskSelect.value, null));