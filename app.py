import json
from typing import Any

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse

from environment.avigilance_env import AvigilanceEnv
from environment.models import AvigilanceAction


FRONTEND_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AvigilanceEnv Space Console</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Sora:wght@400;500;600;700;800&family=IBM+Plex+Mono:wght@400;500&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg: #f3ecdf;
            --panel: rgba(255, 250, 244, 0.76);
            --panel-strong: linear-gradient(145deg, #0f2e36 0%, #1f4e57 44%, #d26831 100%);
            --text: #12232c;
            --muted: #5c6b72;
            --accent: #d26831;
            --line: rgba(18, 35, 44, 0.12);
            --line-strong: rgba(255, 255, 255, 0.18);
            --shadow: 0 28px 70px rgba(20, 35, 41, 0.14);
            --shadow-soft: 0 16px 32px rgba(20, 35, 41, 0.08);
            --surface-dark: #0f2128;
            --surface-dark-2: #132a33;
            --success: #19816f;
            --warn: #b96e17;
        }

        * { box-sizing: border-box; }
        html { scroll-behavior: smooth; }

        body {
            margin: 0;
            font-family: "Sora", "Segoe UI Variable", sans-serif;
            color: var(--text);
            background:
                radial-gradient(circle at 10% 10%, rgba(210, 104, 49, 0.16), transparent 18%),
                radial-gradient(circle at 88% 12%, rgba(15, 140, 127, 0.14), transparent 20%),
                linear-gradient(180deg, #f8f2e8 0%, var(--bg) 100%);
        }

        code, pre, textarea, input, select {
            font-family: "IBM Plex Mono", monospace;
        }

        .page-shell {
            position: relative;
            width: min(1360px, calc(100vw - 32px));
            margin: 0 auto;
            padding: 24px 0 64px;
        }

        .page-noise {
            position: fixed;
            inset: 0;
            background-image:
                linear-gradient(rgba(255,255,255,0.03) 1px, transparent 1px),
                linear-gradient(90deg, rgba(255,255,255,0.03) 1px, transparent 1px);
            background-size: 24px 24px;
            pointer-events: none;
            opacity: 0.45;
        }

        .topbar,
        .hero,
        .ops-grid,
        .walkthrough-grid,
        .console-grid,
        .hero-signal-grid,
        .task-card-grid,
        .summary-strip {
            display: grid;
            gap: 20px;
        }

        .topbar {
            grid-template-columns: 1.2fr auto;
            align-items: end;
            gap: 16px;
            margin-bottom: 20px;
        }

        .topbar h1 {
            margin: 8px 0 0;
            font-size: clamp(2.4rem, 5vw, 4.7rem);
            line-height: 0.95;
            letter-spacing: -0.06em;
        }

        .topbar-chips {
            display: flex;
            flex-wrap: wrap;
            justify-content: flex-end;
            gap: 10px;
        }

        .chip {
            padding: 10px 14px;
            border-radius: 999px;
            border: 1px solid rgba(18, 35, 44, 0.1);
            background: rgba(255, 251, 247, 0.86);
            box-shadow: var(--shadow-soft);
            font-size: 0.82rem;
        }

        .hero {
            grid-template-columns: 1.5fr 0.95fr;
            align-items: stretch;
            margin-bottom: 22px;
        }

        .panel {
            border: 1px solid var(--line);
            border-radius: 28px;
            box-shadow: var(--shadow);
            background: var(--panel);
            padding: 24px;
        }

        .panel-dark {
            background: var(--panel-strong);
            color: #f7f4ee;
            position: relative;
            overflow: hidden;
        }

        .panel-dark::after {
            content: "";
            position: absolute;
            inset: auto -40px -50px auto;
            width: 280px;
            height: 280px;
            border-radius: 50%;
            background: radial-gradient(circle, rgba(255,255,255,0.18), transparent 72%);
            pointer-events: none;
        }

        .hero-stage { padding: 28px; }
        .hero-copy { position: relative; z-index: 1; }

        .hero-copy h2 {
            margin: 10px 0 14px;
            max-width: 13ch;
            font-size: clamp(2.1rem, 4vw, 3.6rem);
            line-height: 0.98;
            letter-spacing: -0.05em;
        }

        .hero-copy .lead {
            max-width: 64ch;
            color: rgba(247, 244, 238, 0.82);
            font-size: 1rem;
            line-height: 1.72;
        }

        .eyebrow,
        .label {
            text-transform: uppercase;
            letter-spacing: 0.18em;
            font-size: 0.72rem;
            font-weight: 600;
        }

        .hero-actions,
        .button-group,
        .control-row {
            display: flex;
            flex-wrap: wrap;
            gap: 12px;
        }

        .hero-actions { margin-top: 22px; }

        .hero-signal-grid {
            margin-top: 28px;
            grid-template-columns: repeat(4, minmax(0, 1fr));
            position: relative;
            z-index: 1;
        }

        .signal-card {
            min-height: 128px;
            padding: 18px;
            border-radius: 22px;
            border: 1px solid var(--line-strong);
            background: rgba(255, 255, 255, 0.08);
        }

        .signal-card.highlight { background: rgba(255, 255, 255, 0.14); }

        .signal-card strong {
            display: block;
            margin: 10px 0 6px;
            font-size: 1.2rem;
        }

        .signal-card p {
            margin: 0;
            color: rgba(247, 244, 238, 0.72);
            line-height: 1.55;
        }

        .hero-rail h3 {
            margin: 10px 0 8px;
            font-size: 1.5rem;
            line-height: 1.1;
        }

        .hero-rail p,
        .console-heading p,
        .walkthrough article p {
            margin: 0;
            color: var(--muted);
            line-height: 1.6;
        }

        .task-card-grid { margin: 22px 0; }

        .task-card {
            padding: 16px 18px;
            border-radius: 20px;
            border: 1px solid var(--line);
            background: rgba(255, 255, 255, 0.58);
            text-align: left;
            cursor: pointer;
            transition: transform 160ms ease, border-color 160ms ease, background 160ms ease;
        }

        .task-card:hover,
        .task-card.is-active {
            transform: translateY(-1px);
            border-color: rgba(210, 104, 49, 0.45);
            background: rgba(255, 245, 237, 0.96);
        }

        .task-card span,
        .rail-metrics span {
            display: block;
            margin-bottom: 6px;
            text-transform: uppercase;
            letter-spacing: 0.14em;
            font-size: 0.7rem;
            color: var(--muted);
        }

        .task-card strong,
        .rail-metrics strong {
            display: block;
            font-size: 0.98rem;
            line-height: 1.4;
        }

        .rail-metrics { display: grid; gap: 14px; margin-bottom: 18px; }
        .wide { width: 100%; }

        .button {
            appearance: none;
            border: 1px solid transparent;
            border-radius: 999px;
            padding: 12px 18px;
            cursor: pointer;
            text-decoration: none;
            transition: transform 160ms ease, background 160ms ease, border-color 160ms ease;
            font-weight: 700;
        }

        .button:hover { transform: translateY(-1px); }
        .button.primary { background: var(--accent); color: #fff7f0; }
        .button.secondary { background: var(--surface-dark); color: #f6efe5; }
        .button.ghost { background: transparent; color: var(--text); border-color: var(--line); }

        .ops-grid { grid-template-columns: 1.5fr 0.82fr; margin-bottom: 22px; }
        .side-stack { display: grid; gap: 20px; }
        .panel-accent { background: linear-gradient(180deg, rgba(255, 249, 242, 0.92), rgba(255, 244, 233, 0.82)); }
        .walkthrough-grid { grid-template-columns: repeat(3, 1fr); }
        .summary-strip { grid-template-columns: repeat(3, minmax(0, 1fr)); margin-bottom: 18px; }

        .panel-header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 16px;
            margin-bottom: 18px;
        }

        .panel-header.compact { margin-bottom: 14px; }
        .panel-header h2 { margin: 8px 0 0; font-size: 1.45rem; }

        .checklist { margin: 0; padding-left: 18px; line-height: 1.7; }
        .checklist.strong li + li { margin-top: 10px; }

        label { display: grid; gap: 8px; min-width: 180px; }

        input, select, textarea {
            width: 100%;
            border: 1px solid var(--line);
            border-radius: 16px;
            background: rgba(255, 255, 255, 0.78);
            color: var(--text);
            padding: 13px 15px;
        }

        select, input { min-height: 50px; }
        textarea { min-height: 320px; resize: vertical; }

        #actionInputHelp {
            margin: 10px 2px 0;
            color: var(--muted);
            font-size: 0.9rem;
            line-height: 1.4;
        }

        .stretch { align-items: flex-end; }
        .stretch .button { min-height: 50px; }

        .summary-card,
        .console-panel,
        .walkthrough article,
        .panel-log {
            border: 1px solid rgba(18, 35, 44, 0.08);
            border-radius: 22px;
            background: rgba(255, 255, 255, 0.48);
            box-shadow: var(--shadow-soft);
        }

        .summary-card { padding: 16px 18px; }
        .summary-card strong { display: block; margin-top: 8px; font-size: 1rem; line-height: 1.45; }
        .console-grid.triple { grid-template-columns: repeat(3, minmax(0, 1fr)); }
        .console-panel { padding: 18px; }
        .console-heading { margin-bottom: 14px; }
        .console-heading h3,
        .walkthrough article h3 { margin: 0 0 6px; font-size: 1.05rem; }

        pre {
            margin: 0;
            min-height: 320px;
            padding: 18px;
            border-radius: 18px;
            background: linear-gradient(180deg, var(--surface-dark) 0%, var(--surface-dark-2) 100%);
            color: #dce8e6;
            overflow: auto;
            white-space: pre-wrap;
            word-break: break-word;
            line-height: 1.5;
        }

        .status-pill {
            padding: 10px 14px;
            border-radius: 999px;
            background: rgba(15, 33, 40, 0.08);
            font-size: 0.82rem;
            font-weight: 700;
        }

        .status-pill.ok { background: rgba(25, 129, 111, 0.14); color: var(--success); }
        .status-pill.warn { background: rgba(185, 110, 23, 0.14); color: var(--warn); }
        .status-pill.error { background: rgba(160, 33, 33, 0.14); color: #8d1f1f; }

        .timeline {
            display: grid;
            gap: 12px;
            margin: 0;
            padding: 0;
            list-style: none;
        }

        .timeline li {
            padding: 14px 14px 14px 16px;
            border-left: 3px solid rgba(210, 104, 49, 0.45);
            border-radius: 0 18px 18px 0;
            background: rgba(255, 255, 255, 0.52);
        }

        .timeline-tag {
            display: inline-flex;
            margin-bottom: 8px;
            padding: 4px 9px;
            border-radius: 999px;
            background: rgba(18, 35, 44, 0.08);
            font-size: 0.72rem;
            text-transform: uppercase;
            letter-spacing: 0.14em;
        }

        .timeline p { margin: 0; line-height: 1.5; }
        .walkthrough article { padding: 18px; }

        @media (max-width: 960px) {
            .topbar,
            .hero,
            .ops-grid,
            .walkthrough-grid,
            .console-grid,
            .hero-signal-grid,
            .summary-strip {
                grid-template-columns: 1fr;
            }

            .topbar-chips { justify-content: flex-start; }

            .page-shell {
                width: min(100vw - 20px, 100%);
                padding-top: 18px;
            }

            .hero-stage,
            .hero-rail,
            .panel { padding: 20px; }
        }
    </style>
</head>
<body>
    <div class="page-shell">
        <div class="page-noise" aria-hidden="true"></div>
        <header class="topbar">
            <div>
                <p class="eyebrow">DGCA Monitoring Space</p>
                <h1>Avigilance Mission Console</h1>
            </div>
            <div class="topbar-chips">
                <span class="chip">Single-File UI</span>
                <span class="chip">OpenEnv Ready</span>
                <span class="chip">Manual + Validator Flows</span>
            </div>
        </header>
        <main>
            <section class="hero" id="console">
                <article class="hero-stage panel panel-dark">
                    <div class="hero-copy">
                        <p class="eyebrow">Live Operations Deck</p>
                        <h2>Run task resets, inspect payloads, and submit exact environment actions from one screen.</h2>
                        <p class="lead">This Space root is now entirely self-contained in app.py. No split frontend assets, no dependency on separate CSS or JavaScript files, and no Gradio-style root shell.</p>
                        <div class="hero-actions">
                            <a class="button primary" href="#controlDeck">Open Control Deck</a>
                            <a class="button ghost" href="#walkthrough">Verification Flow</a>
                        </div>
                    </div>
                    <div class="hero-signal-grid">
                        <div class="signal-card highlight">
                            <span class="label">API Health</span>
                            <strong id="healthStatus">Checking...</strong>
                            <p id="healthDetail">Polling live service metadata.</p>
                        </div>
                        <div class="signal-card">
                            <span class="label">Runtime</span>
                            <strong id="metadataStatus">Loading...</strong>
                            <p>FastAPI backend with a single-file browser console.</p>
                        </div>
                        <div class="signal-card">
                            <span class="label">Session</span>
                            <strong id="sessionStatus">No episode yet</strong>
                            <p id="sessionDetail">Reset any task to initialize an active episode.</p>
                        </div>
                        <div class="signal-card">
                            <span class="label">Reward Guardrail</span>
                            <strong>(0, 1)</strong>
                            <p>Scores remain strictly inside the open interval.</p>
                        </div>
                    </div>
                </article>
                <aside class="hero-rail panel">
                    <div class="rail-block">
                        <p class="eyebrow">Active Task</p>
                        <h3 id="taskTitle">task1 · FTO Quality Scorer</h3>
                        <p id="taskDescription">Grade a Flying Training Organisation against the DGCA rubric and recommend action.</p>
                    </div>
                    <div class="task-card-grid">
                        <button class="task-card is-active" data-task="task1" type="button">
                            <span>task1</span>
                            <strong>FTO Quality</strong>
                        </button>
                        <button class="task-card" data-task="task2" type="button">
                            <span>task2</span>
                            <strong>Incident Prioritiser</strong>
                        </button>
                        <button class="task-card" data-task="task3" type="button">
                            <span>task3</span>
                            <strong>Resource Allocator</strong>
                        </button>
                    </div>
                    <div class="rail-metrics">
                        <div>
                            <span class="label">Endpoints</span>
                            <strong>/reset · /step · /state</strong>
                        </div>
                        <div>
                            <span class="label">Use Case</span>
                            <strong>Reviewer and validator preflight</strong>
                        </div>
                    </div>
                    <button class="button secondary wide" id="refreshStatus" type="button">Refresh Live Status</button>
                </aside>
            </section>

            <section class="ops-grid">
                <article class="panel panel-accent">
                    <div class="panel-header">
                        <div>
                            <p class="eyebrow">Control Deck</p>
                            <h2 id="controlDeck">Interactive Task Runner</h2>
                        </div>
                        <div class="status-pill" id="resultBadge">Awaiting reset</div>
                    </div>
                    <div class="control-row">
                        <label>
                            <span class="label">Task</span>
                            <select id="taskSelect">
                                <option value="task1">task1: FTO Quality Scorer</option>
                                <option value="task2">task2: Incident Prioritiser</option>
                                <option value="task3">task3: Resource Allocator</option>
                            </select>
                        </label>
                        <label>
                            <span class="label">Seed</span>
                            <input id="seedInput" type="number" value="42">
                        </label>
                        <div class="button-group stretch">
                            <button class="button primary" id="resetEpisode" type="button">Reset Episode</button>
                            <button class="button ghost" id="loadExample" type="button">Load Example Action</button>
                            <button class="button ghost" id="fetchState" type="button">Fetch State</button>
                            <button class="button secondary" id="submitAction" type="button">Submit Step</button>
                        </div>
                    </div>
                    <div class="summary-strip">
                        <div class="summary-card">
                            <span class="label">Observation Snapshot</span>
                            <strong id="observationSummary">No observation loaded</strong>
                        </div>
                        <div class="summary-card">
                            <span class="label">Last Reward</span>
                            <strong id="rewardSummary">None yet</strong>
                        </div>
                        <div class="summary-card">
                            <span class="label">Episode State</span>
                            <strong id="doneSummary">Idle</strong>
                        </div>
                    </div>
                    <div class="console-grid triple">
                        <section class="console-panel">
                            <div class="console-heading">
                                <h3>Observation Payload</h3>
                                <p>Backend response after reset or step.</p>
                            </div>
                            <pre id="observationView">Press Reset Episode to start.</pre>
                        </section>
                        <section class="console-panel">
                            <div class="console-heading">
                                <h3>Action Editor</h3>
                                <p>Use typed JSON matching the task schema.</p>
                            </div>
                            <label for="actionInput" class="label">Action JSON</label>
                            <textarea id="actionInput" spellcheck="false" aria-describedby="actionInputHelp"></textarea>
                            <p id="actionInputHelp">The helper can prefill a valid payload, but you can edit every field before submit.</p>
                        </section>
                        <section class="console-panel">
                            <div class="console-heading">
                                <h3>Runtime Result</h3>
                                <p>State, reward, or error output from the active request.</p>
                            </div>
                            <pre id="resultView">Waiting for actions.</pre>
                        </section>
                    </div>
                </article>
                <aside class="side-stack">
                    <article class="panel">
                        <div class="panel-header compact">
                            <div>
                                <p class="eyebrow">Operational Notes</p>
                                <h2>Task Guidance</h2>
                            </div>
                        </div>
                        <ul class="checklist strong">
                            <li><strong>task1</strong> is a one-step FTO grading decision with a DGCA action recommendation.</li>
                            <li><strong>task2</strong> ranks incidents by urgency and can escalate the highest-risk cases immediately.</li>
                            <li><strong>task3</strong> allocates inspector time and may require multiple steps depending on the scenario.</li>
                        </ul>
                    </article>
                    <article class="panel panel-log">
                        <div class="panel-header compact">
                            <div>
                                <p class="eyebrow">Activity Feed</p>
                                <h2>Operator Timeline</h2>
                            </div>
                        </div>
                        <ol class="timeline" id="timeline">
                            <li>
                                <span class="timeline-tag">boot</span>
                                <p>Console loaded. Pulling service metadata.</p>
                            </li>
                        </ol>
                    </article>
                </aside>
            </section>

            <section class="walkthrough panel" id="walkthrough">
                <div class="panel-header">
                    <div>
                        <p class="eyebrow">Verification Path</p>
                        <h2>How This Space Should Be Reviewed</h2>
                    </div>
                </div>
                <div class="walkthrough-grid">
                    <article>
                        <h3>1. Reset a live task</h3>
                        <p>Choose one of the three environments, seed it deterministically, and inspect the exact observation payload emitted by the backend.</p>
                    </article>
                    <article>
                        <h3>2. Submit a typed action</h3>
                        <p>Load the generated example or replace it with your own JSON, then submit the request against the same /step endpoint validators hit.</p>
                    </article>
                    <article>
                        <h3>3. Verify contract behavior</h3>
                        <p>Use the result panel and activity feed to confirm reward bounds, episode status, and endpoint availability before running repository validation scripts.</p>
                    </article>
                </div>
            </section>
        </main>
    </div>
    <script>
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
            if (!observation) return "No observation loaded";
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
            if (!observation) return { task_id: taskId };

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
                        justification: "Single-file UI example action generated from the visible FTO profile."
                    }
                };
            }

            if (taskId === "task2" && observation.incident_batch) {
                const ids = observation.incident_batch.map((item) => item.incident_id);
                return {
                    task_id: "task2",
                    incident_priority_action: {
                        priority_ranking: ids,
                        top_3_rationale: "Example ranking generated in the single-file Space UI.",
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
                        priority_rationale: "Example allocation generated in the single-file Space UI.",
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
    </script>
</body>
</html>
"""

api_app = FastAPI(
    title="AvigilanceEnv",
    description="India Aviation Safety Monitoring OpenEnv — DGCA Early Warning System",
    version="1.1.0",
)

_envs: dict[str, AvigilanceEnv] = {}


def _to_jsonable(value: Any) -> Any:
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    return value


def _dump_json(value: Any) -> str:
    return json.dumps(_to_jsonable(value), indent=2, ensure_ascii=True)


def _reset_session(task_id: str = "task1", seed: int = 42) -> dict[str, Any]:
    env = AvigilanceEnv(task_id=task_id, seed=seed)
    _envs[task_id] = env
    obs = env.reset()
    return obs.model_dump(mode="json")


def _step_session(action: AvigilanceAction) -> dict[str, Any]:
    env = _envs.get(action.task_id)
    if env is None:
        raise HTTPException(status_code=400, detail=f"No active episode for {action.task_id}. Call /reset first.")

    obs, reward, done, info = env.step(action)
    return {
        "observation": obs.model_dump(mode="json"),
        "reward": reward.model_dump(mode="json"),
        "done": done,
        "info": info,
    }


def _get_state(task_id: str = "task1") -> dict[str, Any]:
    env = _envs.get(task_id)
    if env is None:
        return {"status": "no_active_episode"}
    return env.state()


@api_app.get("/api/info")
def api_info() -> dict[str, Any]:
    return {
        "name": "AvigilanceEnv",
        "description": "India Aviation Safety Monitoring — OpenEnv Early Warning System",
        "tasks": ["task1", "task2", "task3"],
        "status": "ready",
    }


@api_app.post("/reset")
def reset(task_id: str = "task1", seed: int = 42) -> JSONResponse:
    try:
        return JSONResponse(content=_reset_session(task_id=task_id, seed=seed))
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@api_app.post("/step")
def step(action: AvigilanceAction) -> JSONResponse:
    try:
        return JSONResponse(content=_step_session(action))
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@api_app.get("/state")
def state(task_id: str = "task1") -> JSONResponse:
    return JSONResponse(content=_get_state(task_id=task_id))


@api_app.get("/health")
def health() -> dict[str, Any]:
    return {"status": "healthy", "env": "AvigilanceEnv"}


@api_app.get("/metadata")
def metadata() -> dict[str, Any]:
    return {
        "name": "AvigilanceEnv",
        "description": "India Aviation Safety Monitoring OpenEnv — DGCA Early Warning System",
        "version": "1.1.0",
        "tasks": ["task1", "task2", "task3"],
        "walkthrough": "/#walkthrough",
    }


@api_app.get("/walkthrough")
def walkthrough() -> RedirectResponse:
    return RedirectResponse(url="/#walkthrough", status_code=307)


@api_app.get("/", response_class=HTMLResponse)
def frontend() -> HTMLResponse:
    return HTMLResponse(FRONTEND_HTML)


@api_app.get("/schema")
def schema() -> dict[str, Any]:
    from environment.models import AvigilanceAction as ActionModel
    from environment.models import AvigilanceObservation, AvigilanceReward

    return {
        "observation": AvigilanceObservation.model_json_schema(),
        "action": ActionModel.model_json_schema(),
        "state": AvigilanceReward.model_json_schema(),
    }


@api_app.post("/mcp")
def mcp(payload: dict | None = None) -> dict[str, Any]:
    body = payload or {}
    return {
        "jsonrpc": "2.0",
        "id": body.get("id"),
        "result": {
            "name": "AvigilanceEnv",
            "tools": ["reset", "step", "state"],
        },
    }


app = api_app


def main() -> None:
    uvicorn.run(app, host="0.0.0.0", port=7860)


if __name__ == "__main__":
    main()
