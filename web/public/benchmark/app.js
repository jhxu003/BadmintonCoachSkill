const $ = (selector, root = document) => root.querySelector(selector);
const escapeHtml = (value) => String(value ?? "—").replace(/[&<>'"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[c]));
const pct = value => value == null ? "—" : `${(value * 100).toFixed(1)}%`;
const number = (value, digits = 1) => value == null ? "—" : Number(value).toFixed(digits);
let payload = { metrics: { models: {} }, cases: [] };
let activeModel = "qwen3-vl-2b";

function metricCards() {
  const models = Object.values(payload.metrics.models || {});
  const complete = models.filter(m => m.samples > 0);
  const avg = key => complete.length ? complete.reduce((sum, m) => sum + (m[key] || 0), 0) / complete.length : null;
  const separation = complete.length ? Math.max(...complete.map(m => m.low_vs_high_issue_separation ?? 0)) : null;
  const cards = [
    ["BADS_CLL", "Dataset"], [payload.metrics.manifest_samples || payload.cases.length || "—", "Selected clips"],
    [Object.keys(payload.metrics.models || {}).length || 2, "Open models"], [pct(avg("pipeline_success_rate")), "Pipeline success"],
    [pct(avg("stroke_recognition_accuracy")), "Stroke accuracy"], [number(separation, 2), "Low − high issues"]
  ];
  $("#scoreboard").innerHTML = cards.map(([value,label]) => `<div class="score"><strong>${escapeHtml(value)}</strong><span>${label}</span></div>`).join("");
}

function modelTable() {
  $("#model-table").innerHTML = Object.entries(payload.metrics.models || {}).map(([name,m]) => {
    const tiers = m.quality_tiers || {};
    return `<tr><td><strong>${escapeHtml(name)}</strong></td><td>${pct(m.schema_success_rate)}</td><td>${pct(m.pipeline_success_rate)}</td><td>${pct(m.stroke_recognition_accuracy)}</td><td>${number(tiers.low?.average_issues)} / ${number(tiers.medium?.average_issues)} / ${number(tiers.high?.average_issues)}</td><td>${m.average_runtime_seconds == null ? "—" : `${number(m.average_runtime_seconds)}s`}</td></tr>`;
  }).join("") || `<tr><td colspan="6">No inference results yet. The page will populate after the smoke test.</td></tr>`;
}

function populateControls() {
  const strokes = [...new Set(payload.cases.map(item => item.dataset.stroke_type))].sort();
  const stroke = $('#filters [name="stroke"]');
  stroke.innerHTML += strokes.map(value => `<option value="${escapeHtml(value)}">${escapeHtml(value)}</option>`).join("");
  const model = $('#filters [name="model"]');
  const names = Object.keys(payload.cases[0]?.models || payload.metrics.models || {"qwen3-vl-2b":{},"qwen25-vl-3b":{}});
  model.innerHTML = names.map(value => `<option value="${escapeHtml(value)}">${escapeHtml(value)}</option>`).join("");
  activeModel = names[0] || activeModel;
}

function field(label, value) { return `<div class="datum"><span>${label}</span><strong>${escapeHtml(value)}</strong></div>`; }
function issueMarkup(issue) {
  const evidence = Array.isArray(issue.evidence) ? issue.evidence.join(" · ") : issue.evidence;
  return `<div class="issue"><div class="issue-head"><span>${escapeHtml(issue.issue)}</span><span class="confidence">${escapeHtml(issue.confidence)}</span></div><p>${escapeHtml(evidence || "No supporting evidence returned")}</p></div>`;
}
function analysisMarkup(model) {
  const observation = model?.observation;
  const coach = model?.coach || {status:"not_run",issues:[]};
  if (!observation) return `<p class="model-status"><span class="status-dot"></span>Observation not available</p><div class="problems"><h4>Run pending</h4><p>This case will populate after local inference and schema validation.</p></div>`;
  const footwork = observation.footwork_observations || {};
  const issues = coach.issues || [];
  const drill = coach.drill ? `${coach.drill.drill_name || coach.drill.drill_id}${coach.drill.dosage ? ` · ${coach.drill.dosage}` : ""}` : null;
  return `<p class="model-status"><span class="status-dot ${model.schema_valid ? 'ok' : ''}"></span>${model.schema_valid ? 'Schema valid' : 'Schema invalid'}${model.runtime_seconds ? ` · ${number(model.runtime_seconds)}s` : ''}</p>
    <div class="observation-grid">${field("Predicted action",observation.action)}${field("Camera view",observation.camera_view)}${field("Contact",observation.contact_point)}${field("Elbow",observation.elbow_height_before_hit)}${field("Body sequence",observation.hip_shoulder_sequence)}${field("Racket side",observation.racket_side_structure)}${field("Follow-through",observation.follow_through)}${field("Footwork / recovery",footwork.recovery || footwork.balance || "unknown")}</div>
    <div class="problems"><h4>Detected problems</h4>${issues.length ? issues.map(issueMarkup).join("") : `<p>No high-confidence issue detected.</p>`}</div>
    <div class="coach"><h4>BadmintonCoachSkill</h4><div class="coach-grid">${field("Primary issue",coach.primary_issue)}${field("Confidence",coach.confidence)}${field("Why it matters",(coach.why || []).join(" · "))}${field("Correction",coach.correction)}${field("Drill",drill)}${field("Retest",(coach.retest || []).join(" · "))}</div></div>
    <p class="missing"><strong>Missing observations:</strong> ${escapeHtml((observation.missing_observations || []).join(" · ") || "None reported")}</p>`;
}

function caseMarkup(item) {
  const modelNames = Object.keys(item.models);
  const selected = item.models[activeModel] ? activeModel : modelNames[0];
  const dataset = item.dataset;
  return `<article class="case" data-id="${escapeHtml(item.sample_id)}"><header class="case-top"><div class="case-title"><h3>${escapeHtml(dataset.stroke_type)}</h3><span class="sample-id">${escapeHtml(item.sample_id)}</span></div><span class="quality ${escapeHtml(dataset.quality_tier)}">${escapeHtml(dataset.quality_tier)} · ${escapeHtml(dataset.quality_rating)}</span></header>
    <div class="case-body"><div class="source-panel"><p class="panel-label">Original stroke · dataset ground truth</p><div class="media">${dataset.media ? `<img src="${escapeHtml(dataset.media)}" alt="Original unmodified ${escapeHtml(dataset.stroke_type)} stroke from BADS_CLL" loading="lazy" />` : `<span class="media-missing">Original GIF not published yet</span>`}</div><div class="dataset-labels">${field("Stroke",dataset.stroke_type)}${field("Quality rating",dataset.quality_rating)}${field("Quality tier",dataset.quality_tier)}${field("Experience",dataset.experience)}</div></div>
    <div class="analysis-panel"><div class="model-tabs" role="tablist" aria-label="Select model">${modelNames.map(name => `<button class="model-tab" type="button" role="tab" aria-selected="${name === selected}" data-model="${escapeHtml(name)}">${escapeHtml(name)}</button>`).join("")}</div><div class="analysis-content">${analysisMarkup(item.models[selected])}</div></div></div></article>`;
}

function renderCases() {
  const data = new FormData($("#filters"));
  activeModel = data.get("model") || activeModel;
  let cases = payload.cases.filter(item => {
    const model = item.models[activeModel];
    const status = model?.coach?.status === "success" ? "success" : "failed";
    return (data.get("stroke") === "all" || item.dataset.stroke_type === data.get("stroke")) && (data.get("quality") === "all" || item.dataset.quality_tier === data.get("quality")) && (data.get("status") === "all" || status === data.get("status"));
  });
  const issues = item => item.models[activeModel]?.coach?.issues?.length || 0;
  const sort = data.get("sort");
  cases.sort((a,b) => sort === "quality-asc" ? a.dataset.quality_rating-b.dataset.quality_rating : sort === "issues-desc" ? issues(b)-issues(a) : sort === "issues-asc" ? issues(a)-issues(b) : b.dataset.quality_rating-a.dataset.quality_rating);
  $("#case-grid").innerHTML = cases.map(caseMarkup).join("");
  $("#case-count").textContent = `${cases.length} / ${payload.cases.length} cases`;
  $("#empty").hidden = cases.length > 0;
}

document.addEventListener("click", event => {
  const tab = event.target.closest(".model-tab");
  if (!tab) return;
  const article = tab.closest(".case");
  const item = payload.cases.find(value => value.sample_id === article.dataset.id);
  article.querySelectorAll(".model-tab").forEach(button => button.setAttribute("aria-selected", String(button === tab)));
  article.querySelector(".analysis-content").innerHTML = analysisMarkup(item.models[tab.dataset.model]);
});

fetch("data/site_results.json").then(response => {
  if (!response.ok) throw new Error(`HTTP ${response.status}`);
  return response.json();
}).then(data => { payload = data; metricCards(); modelTable(); populateControls(); renderCases(); $("#filters").addEventListener("change", renderCases); }).catch(error => {
  metricCards(); modelTable(); $("#case-grid").innerHTML = `<div class="empty">Benchmark data could not be loaded: ${escapeHtml(error.message)}</div>`;
});
