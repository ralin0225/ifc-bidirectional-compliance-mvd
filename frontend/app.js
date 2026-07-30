const STATUS = {
  PASS: { color: [0.086, 0.502, 0.365, 1] },
  FAIL: { color: [0.831, 0.302, 0.247, 1] },
  NOT_APPLICABLE: { color: [0.443, 0.506, 0.541, 1] },
  NOT_CHECKABLE: { color: [0.788, 0.510, 0.086, 1] },
  MANUAL_REVIEW_REQUIRED: { color: [0.463, 0.337, 0.659, 1] },
};

const state = {
  locale: "zh-CN",
  messages: {},
  rules: [],
  results: [],
  elements: [],
  runs: [],
  models: [],
  importJobs: [],
  importNotice: null,
  queryResponse: null,
  ids: null,
  health: null,
  selectedRuleId: null,
  selectedElementGuid: null,
  modelId: null,
  activeStatuses: new Set(Object.keys(STATUS)),
};

const dom = {
  healthDot: document.querySelector("#healthDot"),
  healthText: document.querySelector("#healthText"),
  ruleList: document.querySelector("#ruleList"),
  ruleCount: document.querySelector("#ruleCount"),
  resultsBody: document.querySelector("#resultsBody"),
  statusFilters: document.querySelector("#statusFilters"),
  evidencePanel: document.querySelector("#evidencePanel"),
  idsSummary: document.querySelector("#idsSummary"),
  viewerTitle: document.querySelector("#viewerTitle"),
  viewerEmpty: document.querySelector("#viewerEmpty"),
  legend: document.querySelector("#legend"),
  graph: document.querySelector("#graph"),
  toast: document.querySelector("#toast"),
  runChecks: document.querySelector("#runChecks"),
  resetView: document.querySelector("#resetView"),
  localeSelect: document.querySelector("#localeSelect"),
  reloadRuns: document.querySelector("#reloadRuns"),
  runsBody: document.querySelector("#runsBody"),
  runsEmpty: document.querySelector("#runsEmpty"),
  queryForm: document.querySelector("#queryForm"),
  queryInput: document.querySelector("#queryInput"),
  queryRun: document.querySelector("#queryRun"),
  queryDsl: document.querySelector("#queryDsl"),
  queryFeedback: document.querySelector("#queryFeedback"),
  queryResults: document.querySelector("#queryResults"),
  fitSelection: document.querySelector("#fitSelection"),
  hideSelection: document.querySelector("#hideSelection"),
  isolateSelection: document.querySelector("#isolateSelection"),
  showAll: document.querySelector("#showAll"),
  ghostContext: document.querySelector("#ghostContext"),
  toggleProjection: document.querySelector("#toggleProjection"),
  frontView: document.querySelector("#frontView"),
  topView: document.querySelector("#topView"),
  rightView: document.querySelector("#rightView"),
  toggleSection: document.querySelector("#toggleSection"),
  sectionControl: document.querySelector("#sectionControl"),
  sectionLevel: document.querySelector("#sectionLevel"),
  toggleMeasure: document.querySelector("#toggleMeasure"),
  measurementHud: document.querySelector("#measurementHud"),
  saveView: document.querySelector("#saveView"),
  restoreView: document.querySelector("#restoreView"),
  modelSearch: document.querySelector("#modelSearch"),
  modelTree: document.querySelector("#modelTree"),
  reloadModels: document.querySelector("#reloadModels"),
  modelsBody: document.querySelector("#modelsBody"),
  modelsEmpty: document.querySelector("#modelsEmpty"),
  importForm: document.querySelector("#importForm"),
  ifcFile: document.querySelector("#ifcFile"),
  chooseIfcFile: document.querySelector("#chooseIfcFile"),
  ifcFileName: document.querySelector("#ifcFileName"),
  modelSource: document.querySelector("#modelSource"),
  modelLicense: document.querySelector("#modelLicense"),
  importModel: document.querySelector("#importModel"),
  importProgress: document.querySelector("#importProgress"),
};

const escapeHtml = (value) => String(value ?? "")
  .replaceAll("&", "&amp;")
  .replaceAll("<", "&lt;")
  .replaceAll(">", "&gt;")
  .replaceAll('"', "&quot;");

function t(key, variables = {}) {
  const template = state.messages[state.locale]?.[key]
    ?? state.messages.en?.[key]
    ?? key;
  return Object.entries(variables).reduce(
    (value, [name, replacement]) => value.replaceAll(`{${name}}`, String(replacement)),
    template,
  );
}

function statusLabel(status) {
  return t(`status.${status}`);
}

function preferredLocale() {
  const parameter = new URLSearchParams(window.location.search).get("lang");
  if (["zh-CN", "en"].includes(parameter)) return parameter;
  const saved = localStorage.getItem("ifc-compliance-locale");
  if (["zh-CN", "en"].includes(saved)) return saved;
  return navigator.language.toLowerCase().startsWith("zh") ? "zh-CN" : "en";
}

function applyStaticTranslations() {
  document.documentElement.lang = state.locale;
  document.title = t("app.metaTitle");
  document.querySelectorAll("[data-i18n]").forEach((element) => {
    element.textContent = t(element.dataset.i18n);
  });
  document.querySelectorAll("[data-i18n-aria]").forEach((element) => {
    element.setAttribute("aria-label", t(element.dataset.i18nAria));
  });
  document.querySelectorAll("[data-i18n-placeholder]").forEach((element) => {
    element.setAttribute("placeholder", t(element.dataset.i18nPlaceholder));
  });
  dom.localeSelect.value = state.locale;
}

function syncUrl(updates = {}) {
  const url = new URL(window.location.href);
  const values = {
    lang: state.locale,
    model: state.modelId,
    rule: state.selectedRuleId,
    element: state.selectedElementGuid,
    ...updates,
  };
  Object.entries(values).forEach(([key, value]) => {
    if (value) url.searchParams.set(key, value);
    else url.searchParams.delete(key);
  });
  window.history.replaceState({}, "", url);
}

function withModel(path) {
  const url = new URL(path, window.location.origin);
  url.searchParams.set("model_id", state.modelId);
  return `${url.pathname}${url.search}`;
}

function renderLocalizedUi() {
  applyStaticTranslations();
  if (!state.health) return;
  dom.healthText.textContent = t("health.summary", {
    rules: state.health.rule_count,
    elements: state.health.element_count,
    schema: state.health.storage.schema_version,
  });
  renderRules();
  renderIds();
  renderStatusControls();
  renderResults();
  renderEvidence();
  renderRuns();
  renderModels();
  renderQuery();
  renderModelTree();
  viewer.updateControls();
  renderImportProgress();
  const rule = currentRule();
  if (rule) dom.viewerTitle.textContent = `§${rule.source.section} · ${rule.target.ifc_class}`;
  dom.legend.innerHTML = Object.keys(STATUS).map((status) => `
    <span class="legend-item status-${status}">
      <i class="swatch"></i>${escapeHtml(statusLabel(status))}
    </span>
  `).join("");
}

async function api(path, options) {
  const response = await fetch(path, options);
  if (!response.ok) {
    const raw = await response.text();
    let detail = null;
    try {
      detail = JSON.parse(raw).detail;
    } catch {
      detail = raw;
    }
    if (detail?.code) {
      const localized = t(`models.error.${detail.code}`);
      const error = new Error(localized.startsWith("models.error.") ? detail.message : localized);
      error.code = detail.code;
      throw error;
    }
    throw new Error(`${response.status} ${typeof detail === "string" ? detail : JSON.stringify(detail)}`);
  }
  return response.json();
}

function currentRule() {
  return state.rules.find((rule) => rule.rule_id === state.selectedRuleId);
}

function currentRuleResults() {
  return state.results.filter((result) => result.rule_id === state.selectedRuleId);
}

function resultFor(ruleId, guid) {
  return state.results.find((item) => item.rule_id === ruleId && item.element_guid === guid);
}

function showToast(message) {
  dom.toast.textContent = message;
  dom.toast.classList.add("show");
  clearTimeout(showToast.timeout);
  showToast.timeout = setTimeout(() => dom.toast.classList.remove("show"), 2600);
}

function renderRules() {
  dom.ruleCount.textContent = String(state.rules.length);
  dom.ruleList.innerHTML = state.rules.map((rule) => {
    const counts = Object.entries(rule.status_counts || {})
      .map(([status, count]) => `<span class="mini-status">${escapeHtml(statusLabel(status))} ${count}</span>`)
      .join("");
    return `
      <button class="rule-card ${rule.rule_id === state.selectedRuleId ? "selected" : ""}"
        data-rule-id="${escapeHtml(rule.rule_id)}" role="listitem">
        <span class="rule-code">IBC §${escapeHtml(rule.source.section)} · ${escapeHtml(rule.execution_method)}</span>
        <span class="rule-title">${escapeHtml(t(`rules.${rule.rule_id}.title`))}</span>
        <span class="rule-threshold">${escapeHtml(rule.requirement.metric)} ≥ ${rule.requirement.value} ${rule.requirement.unit}</span>
        <span class="rule-statuses">${counts}</span>
      </button>`;
  }).join("");
  dom.ruleList.querySelectorAll("[data-rule-id]").forEach((button) => {
    button.addEventListener("click", () => selectRule(button.dataset.ruleId));
  });
}

function renderIds() {
  if (!state.ids) return;
  dom.idsSummary.innerHTML = state.ids.specifications.map((spec) => `
    <div class="ids-line">
      <span>${escapeHtml(t(`ids.${spec.identifier}`))}</span>
      <strong>${spec.passed_count}/${spec.applicable_count}</strong>
    </div>
  `).join("") + `<p class="ids-purpose">${escapeHtml(t("ids.purpose"))}</p>`;
}

function renderStatusControls() {
  const counts = currentRuleResults().reduce((acc, result) => {
    acc[result.status] = (acc[result.status] || 0) + 1;
    return acc;
  }, {});
  dom.statusFilters.innerHTML = Object.entries(STATUS).map(([status, meta]) => `
    <button class="filter-button ${state.activeStatuses.has(status) ? "active" : ""}"
      data-status="${status}">
      ${escapeHtml(statusLabel(status))} ${counts[status] || 0}
    </button>
  `).join("");
  dom.statusFilters.querySelectorAll("[data-status]").forEach((button) => {
    button.addEventListener("click", () => {
      const status = button.dataset.status;
      if (state.activeStatuses.has(status)) state.activeStatuses.delete(status);
      else state.activeStatuses.add(status);
      renderStatusControls();
      renderResults();
      renderModelTree();
      viewer.render();
    });
  });
}

function metricText(value, unit) {
  return value === null || value === undefined ? "—" : `${Number(value).toFixed(1)} ${unit}`;
}

function renderResults() {
  const results = currentRuleResults().filter((result) => state.activeStatuses.has(result.status));
  dom.resultsBody.innerHTML = results.map((result) => `
    <tr data-guid="${escapeHtml(result.element_guid)}"
      class="${result.element_guid === state.selectedElementGuid ? "selected" : ""}">
      <td><span class="status-pill status-${result.status}">${escapeHtml(statusLabel(result.status))}</span></td>
      <td><strong>${escapeHtml(result.element_name)}</strong><br><span class="guid">${escapeHtml(result.element_guid)}</span></td>
      <td class="metric">${metricText(result.measured_value, result.unit)}</td>
      <td class="metric">${escapeHtml(result.operator)} ${metricText(result.required_value, result.unit)}</td>
      <td>${escapeHtml(result.evidence_source || "—")}</td>
    </tr>
  `).join("");
  dom.resultsBody.querySelectorAll("[data-guid]").forEach((row) => {
    row.addEventListener("click", () => selectElement(row.dataset.guid));
  });
  dom.viewerEmpty.hidden = results.length > 0;
}

function detailRows(details, prefix = "") {
  const rows = [];
  Object.entries(details || {}).forEach(([key, value]) => {
    const label = prefix ? `${prefix}.${key}` : key;
    if (value && typeof value === "object" && !Array.isArray(value)) {
      rows.push(...detailRows(value, label));
    } else {
      rows.push(`<li><strong>${escapeHtml(label)}</strong><br>${escapeHtml(Array.isArray(value) ? value.join(", ") : value)}</li>`);
    }
  });
  return rows.join("");
}

function renderEvidence() {
  const rule = currentRule();
  const guid = state.selectedElementGuid;
  const result = guid ? resultFor(rule?.rule_id, guid) : null;
  if (!rule || !result) {
    dom.evidencePanel.innerHTML = `
      <p class="empty-copy">${escapeHtml(t("evidence.empty"))}</p>
      ${rule ? `<div class="evidence-section"><h3>${escapeHtml(t("evidence.currentClause"))}</h3><p class="clause-excerpt" lang="en">“${escapeHtml(rule.source.excerpt)}”</p></div>` : ""}`;
    return;
  }
  const relevantRules = state.results
    .filter((item) => item.element_guid === guid)
    .map((item) => `${item.clause} · ${item.status}`);
  dom.evidencePanel.innerHTML = `
    <div class="status-banner status-${result.status}">
      <strong>${escapeHtml(statusLabel(result.status))}</strong>
      <span>${escapeHtml(result.evidence_source)}</span>
    </div>
    <h3 class="evidence-title">${escapeHtml(result.element_name)}</h3>
    <div class="guid">${escapeHtml(result.ifc_class)} · ${escapeHtml(result.element_guid)}</div>
    <div class="measure-box">
      <div class="measure-cell"><small>${escapeHtml(t("evidence.measured"))}</small><strong>${metricText(result.measured_value, result.unit)}</strong></div>
      <span class="operator">${escapeHtml(result.operator)}</span>
      <div class="measure-cell"><small>${escapeHtml(t("evidence.threshold"))}</small><strong>${metricText(result.required_value, result.unit)}</strong></div>
    </div>
    <div class="evidence-section">
      <h3>${escapeHtml(t("evidence.why"))}</h3>
      <p>${escapeHtml(t(`evidence.reason.${result.status}`))}</p>
    </div>
    <div class="evidence-section">
      <h3>${escapeHtml(t("evidence.sourceText"))} · IBC ${escapeHtml(rule.source.section)} · PDF ${rule.source.pdf_page}</h3>
      <p class="clause-excerpt" lang="en">“${escapeHtml(rule.source.excerpt)}”</p>
    </div>
    <div class="evidence-section">
      <h3>${escapeHtml(t("evidence.interpretation"))}</h3>
      <p>${escapeHtml(t(`rules.${rule.rule_id}.interpretation`))}</p>
    </div>
    <div class="evidence-section">
      <h3>${escapeHtml(t("evidence.related"))}</h3>
      <ul class="detail-list">${relevantRules.map((item) => `<li>${escapeHtml(item)}</li>`).join("")}</ul>
    </div>
    <div class="evidence-section">
      <h3>${escapeHtml(t("evidence.provenance"))}</h3>
      <ul class="detail-list">${detailRows(result.evidence_details)}</ul>
    </div>`;
}

async function renderGraph() {
  const query = state.selectedElementGuid
    ? `element_guid=${encodeURIComponent(state.selectedElementGuid)}`
    : `rule_id=${encodeURIComponent(state.selectedRuleId)}`;
  const graph = await api(`/api/graph/ego?${query}&model_id=${encodeURIComponent(state.modelId)}`);
  const svg = dom.graph;
  const width = svg.clientWidth || 420;
  const height = svg.clientHeight || 250;
  svg.setAttribute("viewBox", `0 0 ${width} ${height}`);
  svg.innerHTML = "";
  const center = { x: width / 2, y: height / 2 };
  const radiusX = Math.max(80, Math.min(150, width * .31));
  const radiusY = 84;
  const positions = new Map();
  graph.nodes.forEach((node, index) => {
    const isAnchor = node.id === `element:${state.selectedElementGuid}` || node.id === `rule:${state.selectedRuleId}`;
    const angle = ((index - 1) / Math.max(1, graph.nodes.length - 1)) * Math.PI * 2 - Math.PI / 2;
    positions.set(node.id, isAnchor
      ? center
      : { x: center.x + Math.cos(angle) * radiusX, y: center.y + Math.sin(angle) * radiusY });
  });
  graph.edges.forEach((edge) => {
    const from = positions.get(edge.source);
    const to = positions.get(edge.target);
    if (!from || !to) return;
    const line = document.createElementNS("http://www.w3.org/2000/svg", "line");
    line.setAttribute("x1", from.x); line.setAttribute("y1", from.y);
    line.setAttribute("x2", to.x); line.setAttribute("y2", to.y);
    line.setAttribute("class", "graph-edge");
    svg.append(line);
    const label = document.createElementNS("http://www.w3.org/2000/svg", "text");
    label.setAttribute("x", (from.x + to.x) / 2);
    label.setAttribute("y", (from.y + to.y) / 2 - 3);
    label.setAttribute("text-anchor", "middle");
    label.setAttribute("class", "graph-edge-label");
    label.textContent = edge.type;
    svg.append(label);
  });
  const colors = { Clause: "#147ea0", Rule: "#14262d", IfcElement: "#e95645", ComplianceResult: "#c98216" };
  graph.nodes.forEach((node) => {
    const position = positions.get(node.id);
    const group = document.createElementNS("http://www.w3.org/2000/svg", "g");
    group.setAttribute("class", "graph-node");
    group.setAttribute("tabindex", "0");
    group.setAttribute("role", "button");
    const circle = document.createElementNS("http://www.w3.org/2000/svg", "circle");
    circle.setAttribute("cx", position.x); circle.setAttribute("cy", position.y);
    circle.setAttribute("r", node.kind === "ComplianceResult" ? 12 : 16);
    circle.setAttribute("fill", node.status ? cssColor(node.status) : (colors[node.kind] || "#71818a"));
    group.append(circle);
    const text = document.createElementNS("http://www.w3.org/2000/svg", "text");
    text.setAttribute("x", position.x);
    text.setAttribute("y", position.y + 29);
    text.setAttribute("text-anchor", "middle");
    text.textContent = node.label.length > 28 ? `${node.label.slice(0, 25)}…` : node.label;
    group.append(text);
    const activate = () => {
      if (node.rule_id) selectRule(node.rule_id);
      if (node.global_id) selectElement(node.global_id);
    };
    group.addEventListener("click", activate);
    group.addEventListener("keydown", (event) => {
      if (event.key === "Enter" || event.key === " ") activate();
    });
    svg.append(group);
  });
}

function cssColor(status) {
  const values = STATUS[status]?.color || [.44, .5, .54, 1];
  return `rgb(${values.slice(0, 3).map((value) => Math.round(value * 255)).join(",")})`;
}

function selectRule(ruleId) {
  const ruleChanged = state.selectedRuleId !== ruleId;
  state.selectedRuleId = ruleId;
  const hasElement = state.selectedElementGuid && resultFor(ruleId, state.selectedElementGuid);
  if (!hasElement) state.selectedElementGuid = null;
  const rule = currentRule();
  dom.viewerTitle.textContent = `§${rule.source.section} · ${rule.target.ifc_class}`;
  renderRules();
  renderStatusControls();
  renderResults();
  renderEvidence();
  renderModelTree();
  if (ruleChanged || !state.selectedElementGuid) viewer.focusCurrentRule();
  viewer.render();
  renderGraph().catch(console.error);
  syncUrl();
}

function selectElement(guid) {
  state.selectedElementGuid = guid;
  if (!resultFor(state.selectedRuleId, guid)) {
    const first = state.results.find((result) => result.element_guid === guid);
    if (first) state.selectedRuleId = first.rule_id;
  }
  renderRules();
  renderStatusControls();
  renderResults();
  renderEvidence();
  renderModelTree();
  viewer.render();
  renderGraph().catch(console.error);
  syncUrl();
}

function formatDate(value) {
  return new Intl.DateTimeFormat(state.locale, {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

function renderModels() {
  dom.modelsEmpty.hidden = state.models.length > 0;
  dom.modelsBody.innerHTML = state.models.map((model) => {
    const current = model.model_id === state.modelId;
    return `
      <tr>
        <td>
          <strong>${escapeHtml(model.name)}</strong>
          ${current ? `<span class="model-active">${escapeHtml(t("models.current"))}</span>` : ""}
          <span class="guid">${escapeHtml(model.model_id)} · ${escapeHtml(
            t(model.source_kind === "FIXTURE" ? "models.fixture" : "models.upload"),
          )}</span>
        </td>
        <td>${escapeHtml(model.schema_version)}</td>
        <td class="metric">${model.element_count}</td>
        <td><span class="model-hash" title="${escapeHtml(model.source_sha256)}">${escapeHtml(model.source_sha256)}</span></td>
        <td>
          ${current ? "—" : `<button class="model-open" type="button"
            data-open-model="${escapeHtml(model.model_id)}">${escapeHtml(t("models.open"))}</button>`}
        </td>
      </tr>`;
  }).join("");
  dom.modelsBody.querySelectorAll("[data-open-model]").forEach((button) => {
    button.addEventListener("click", () => {
      const url = new URL(window.location.href);
      url.searchParams.set("model", button.dataset.openModel);
      ["rule", "element", "run", "view"].forEach((key) => url.searchParams.delete(key));
      window.location.assign(url);
    });
  });
}

async function loadModels() {
  const [models, jobs] = await Promise.all([
    api("/api/models"),
    api("/api/import-jobs?limit=20"),
  ]);
  state.models = models;
  state.importJobs = jobs.items;
  renderModels();
}

function renderImportProgress() {
  const notice = state.importNotice;
  dom.ifcFileName.textContent = dom.ifcFile.files[0]?.name || t("models.noFile");
  if (!notice) return;
  if (notice.type === "progress") {
    dom.importProgress.className = "import-progress";
    dom.importProgress.textContent = `${t(`models.phase.${notice.phase}`)} · ${notice.progress}%`;
  } else if (notice.type === "success") {
    dom.importProgress.className = "import-progress success";
    dom.importProgress.textContent = t("models.imported", { modelId: notice.modelId });
  } else {
    dom.importProgress.className = "import-progress error";
    dom.importProgress.textContent = t("models.failed", {
      error: t(`models.error.${notice.code || "UNKNOWN"}`),
    });
  }
}

function renderRuns() {
  dom.runsEmpty.hidden = state.runs.length > 0;
  dom.runsBody.innerHTML = state.runs.map((run) => {
    const counts = Object.entries(run.status_counts || {})
      .map(([status, count]) => `<span class="mini-status status-${status}">${escapeHtml(statusLabel(status))} ${count}</span>`)
      .join("");
    const runUrl = new URL(window.location.href);
    runUrl.searchParams.set("run", run.run_id);
    runUrl.hash = "runs";
    const exportUrl = (format) => (
      `/api/check-runs/${encodeURIComponent(run.run_id)}/export?format=${format}&locale=${encodeURIComponent(state.locale)}`
    );
    return `
      <tr data-run-id="${escapeHtml(run.run_id)}">
        <td>
          <a class="run-link" href="${escapeHtml(runUrl.pathname + runUrl.search + runUrl.hash)}">${escapeHtml(run.run_id.slice(0, 16))}…</a>
          <span class="guid">${escapeHtml(run.execution_id)}</span>
        </td>
        <td>${escapeHtml(formatDate(run.started_at))}</td>
        <td class="metric">${run.duration_ms === null ? "—" : `${Number(run.duration_ms).toFixed(1)} ms`}</td>
        <td class="metric">${run.result_count}</td>
        <td><span class="run-statuses">${counts}</span></td>
        <td>
          <span class="export-links">
            <a href="${exportUrl("json")}" download>${escapeHtml(t("runs.exportJson"))}</a>
            <a href="${exportUrl("csv")}" download>${escapeHtml(t("runs.exportCsv"))}</a>
            <a href="${exportUrl("html")}" target="_blank">${escapeHtml(t("runs.exportHtml"))}</a>
            <a href="${exportUrl("bcf")}" download>${escapeHtml(t("runs.exportBcf"))}</a>
          </span>
        </td>
      </tr>`;
  }).join("");
}

async function loadRuns() {
  const response = await api(withModel("/api/check-runs?limit=50"));
  state.runs = response.items;
  renderRuns();
}

function renderQuery() {
  const response = state.queryResponse;
  if (!response) {
    dom.queryDsl.textContent = "—";
    dom.queryFeedback.className = "empty-copy";
    dom.queryFeedback.textContent = t("query.empty");
    dom.queryResults.innerHTML = "";
    return;
  }
  dom.queryDsl.textContent = JSON.stringify(response.parsed.dsl, null, 2);
  if (response.parsed.warnings.length) {
    dom.queryFeedback.className = "query-warning";
    dom.queryFeedback.textContent = response.parsed.warnings
      .map((warning) => t(`query.warning.${warning}`))
      .join(" ");
  } else {
    dom.queryFeedback.className = "";
    dom.queryFeedback.textContent = t("query.matched", {
      total: response.total,
      returned: response.returned,
    });
  }
  dom.queryResults.innerHTML = response.rows.length
    ? response.rows.map((row) => `
      <button class="query-result status-${row.status}" type="button"
        data-query-rule="${escapeHtml(row.rule_id)}"
        data-query-guid="${escapeHtml(row.element_guid)}">
        <strong>${escapeHtml(row.element_name)} · ${escapeHtml(statusLabel(row.status))}</strong>
        <span>${escapeHtml(t(`rules.${row.rule_id}.title`))} · ${escapeHtml(row.element_guid)}</span>
      </button>
    `).join("")
    : `<p class="empty-copy">${escapeHtml(t("query.noRows"))}</p>`;
  dom.queryResults.querySelectorAll("[data-query-guid]").forEach((button) => {
    button.addEventListener("click", () => {
      state.selectedRuleId = button.dataset.queryRule;
      selectElement(button.dataset.queryGuid);
      document.querySelector("#workspace").scrollIntoView({ behavior: "smooth" });
    });
  });
}

function renderModelTree() {
  const query = dom.modelSearch.value.trim().toLocaleLowerCase(state.locale);
  const elements = state.elements.filter((element) => {
    if (!query) return true;
    const searchable = [
      element.global_id,
      element.name,
      element.ifc_class,
      JSON.stringify(element.properties || {}),
      ...(element.spatial_path || []).flatMap((node) => [node.name, node.ifc_class, node.global_id]),
    ].join(" ").toLocaleLowerCase(state.locale);
    return searchable.includes(query);
  });

  const root = { children: new Map(), elements: [] };
  elements.forEach((element) => {
    let cursor = root;
    (element.spatial_path || []).forEach((spatial) => {
      const key = `${spatial.ifc_class}:${spatial.global_id}`;
      if (!cursor.children.has(key)) {
        cursor.children.set(key, { spatial, children: new Map(), elements: [] });
      }
      cursor = cursor.children.get(key);
    });
    cursor.elements.push(element);
  });

  const renderElements = (items) => {
    const byClass = new Map();
    items.forEach((element) => {
      if (!byClass.has(element.ifc_class)) byClass.set(element.ifc_class, []);
      byClass.get(element.ifc_class).push(element);
    });
    return [...byClass.entries()].sort(([left], [right]) => left.localeCompare(right)).map(([ifcClass, members]) => `
      <details class="tree-class" open>
        <summary>${escapeHtml(ifcClass)} <span>${members.length}</span></summary>
        <div class="tree-elements">
          ${members.map((element) => {
            const status = resultFor(state.selectedRuleId, element.global_id)?.status;
            const classes = [
              "tree-element",
              status ? `status-${status}` : "",
              element.global_id === state.selectedElementGuid ? "selected" : "",
              viewer.hiddenGuids.has(element.global_id) ? "hidden-element" : "",
              viewer.isolatedGuid === element.global_id ? "isolated-element" : "",
            ].filter(Boolean).join(" ");
            return `
              <button type="button" class="${classes}" data-tree-guid="${escapeHtml(element.global_id)}">
                <i aria-hidden="true"></i>
                <span><strong>${escapeHtml(element.name || element.ifc_class)}</strong>
                <small>${escapeHtml(element.global_id)}</small></span>
              </button>`;
          }).join("")}
        </div>
      </details>
    `).join("");
  };

  const renderSpatial = (node) => [...node.children.values()].map((child) => `
    <details class="tree-spatial" open>
      <summary>
        <span>${escapeHtml(child.spatial.name || child.spatial.ifc_class)}</span>
        <small>${escapeHtml(child.spatial.ifc_class)}</small>
      </summary>
      <div class="tree-branch">
        ${renderSpatial(child)}
        ${renderElements(child.elements)}
      </div>
    </details>
  `).join("");

  dom.modelTree.innerHTML = elements.length
    ? renderSpatial(root) + renderElements(root.elements)
    : `<p class="tree-empty">${escapeHtml(t("query.noRows"))}</p>`;
  dom.modelTree.querySelectorAll("[data-tree-guid]").forEach((button) => {
    button.addEventListener("click", () => {
      const mesh = viewer.meshes.find((item) => item.element.global_id === button.dataset.treeGuid);
      if (mesh) viewer.measure(mesh);
      selectElement(button.dataset.treeGuid);
    });
  });
}

class IFCWebGLViewer {
  constructor(canvas) {
    this.canvas = canvas;
    this.gl = canvas.getContext("webgl", { antialias: true, alpha: false });
    if (!this.gl) throw new Error("WebGL is unavailable in this browser");
    this.meshes = [];
    this.yaw = 1.25;
    this.pitch = .42;
    this.distance = 19;
    this.target = [6.7, 1.6, 1.0];
    this.drag = null;
    this.hiddenGuids = new Set();
    this.isolatedGuid = null;
    this.ghostContext = false;
    this.projection = "perspective";
    this.sectionEnabled = false;
    this.sectionZ = 4;
    this.measureEnabled = false;
    this.measurePoints = [];
    this.program = this.createProgram();
    this.positionLocation = this.gl.getAttribLocation(this.program, "aPosition");
    this.mvpLocation = this.gl.getUniformLocation(this.program, "uMVP");
    this.colorLocation = this.gl.getUniformLocation(this.program, "uColor");
    this.clipEnabledLocation = this.gl.getUniformLocation(this.program, "uClipEnabled");
    this.clipZLocation = this.gl.getUniformLocation(this.program, "uClipZ");
    this.initEvents();
    new ResizeObserver(() => this.render()).observe(canvas);
  }

  createProgram() {
    const gl = this.gl;
    const compile = (type, source) => {
      const shader = gl.createShader(type);
      gl.shaderSource(shader, source);
      gl.compileShader(shader);
      if (!gl.getShaderParameter(shader, gl.COMPILE_STATUS)) throw new Error(gl.getShaderInfoLog(shader));
      return shader;
    };
    const vertex = compile(gl.VERTEX_SHADER, `
      attribute vec3 aPosition;
      uniform mat4 uMVP;
      varying float vWorldZ;
      void main() {
        vWorldZ = aPosition.z;
        gl_Position = uMVP * vec4(aPosition, 1.0);
      }
    `);
    const fragment = compile(gl.FRAGMENT_SHADER, `
      precision mediump float;
      uniform vec4 uColor;
      uniform bool uClipEnabled;
      uniform float uClipZ;
      varying float vWorldZ;
      void main() {
        if (uClipEnabled && vWorldZ > uClipZ) discard;
        gl_FragColor = uColor;
      }
    `);
    const program = gl.createProgram();
    gl.attachShader(program, vertex);
    gl.attachShader(program, fragment);
    gl.linkProgram(program);
    if (!gl.getProgramParameter(program, gl.LINK_STATUS)) throw new Error(gl.getProgramInfoLog(program));
    return program;
  }

  load(elements) {
    const gl = this.gl;
    let minimumZ = Infinity;
    let maximumZ = -Infinity;
    this.meshes = elements.map((element, index) => {
      minimumZ = Math.min(minimumZ, element.geometry.bbox.min[2]);
      maximumZ = Math.max(maximumZ, element.geometry.bbox.max[2]);
      const positions = new Float32Array(element.geometry.positions);
      const indices = new Uint16Array(element.geometry.indices);
      const edges = [];
      const seen = new Set();
      for (let i = 0; i < indices.length; i += 3) {
        [[indices[i], indices[i + 1]], [indices[i + 1], indices[i + 2]], [indices[i + 2], indices[i]]]
          .forEach(([a, b]) => {
            const key = a < b ? `${a}:${b}` : `${b}:${a}`;
            if (!seen.has(key)) { seen.add(key); edges.push(a, b); }
          });
      }
      const vertexBuffer = gl.createBuffer();
      gl.bindBuffer(gl.ARRAY_BUFFER, vertexBuffer);
      gl.bufferData(gl.ARRAY_BUFFER, positions, gl.STATIC_DRAW);
      const indexBuffer = gl.createBuffer();
      gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER, indexBuffer);
      gl.bufferData(gl.ELEMENT_ARRAY_BUFFER, indices, gl.STATIC_DRAW);
      const edgeBuffer = gl.createBuffer();
      gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER, edgeBuffer);
      gl.bufferData(gl.ELEMENT_ARRAY_BUFFER, new Uint16Array(edges), gl.STATIC_DRAW);
      return { element, index: index + 1, vertexBuffer, indexBuffer, edgeBuffer, count: indices.length, edgeCount: edges.length };
    });
    if (Number.isFinite(minimumZ) && Number.isFinite(maximumZ)) {
      dom.sectionLevel.min = String(minimumZ);
      dom.sectionLevel.max = String(maximumZ);
      dom.sectionLevel.step = String(Math.max(.01, (maximumZ - minimumZ) / 100));
      dom.sectionLevel.value = String(maximumZ);
      this.sectionZ = maximumZ;
    }
    this.updateControls();
    this.render();
  }

  resize() {
    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    const width = Math.max(1, Math.round(this.canvas.clientWidth * dpr));
    const height = Math.max(1, Math.round(this.canvas.clientHeight * dpr));
    if (this.canvas.width !== width || this.canvas.height !== height) {
      this.canvas.width = width;
      this.canvas.height = height;
    }
    this.gl.viewport(0, 0, width, height);
  }

  mvp() {
    const eye = [
      this.target[0] + Math.cos(this.pitch) * Math.cos(this.yaw) * this.distance,
      this.target[1] + Math.cos(this.pitch) * Math.sin(this.yaw) * this.distance,
      this.target[2] + Math.sin(this.pitch) * this.distance,
    ];
    const aspect = this.canvas.width / this.canvas.height;
    const projection = this.projection === "orthographic"
      ? orthographic(
        -this.distance * .45 * aspect,
        this.distance * .45 * aspect,
        -this.distance * .45,
        this.distance * .45,
        .05,
        100,
      )
      : perspective(Math.PI / 4, aspect, .05, 100);
    return multiply(projection, lookAt(eye, this.target, [0, 0, 1]));
  }

  meshStatus(mesh) {
    return resultFor(state.selectedRuleId, mesh.element.global_id)?.status || null;
  }

  visible(mesh) {
    const status = this.meshStatus(mesh);
    if (!status || !state.activeStatuses.has(status)) return false;
    if (this.hiddenGuids.has(mesh.element.global_id)) return false;
    if (this.isolatedGuid && mesh.element.global_id !== this.isolatedGuid) return this.ghostContext;
    return true;
  }

  isGhost(mesh) {
    return Boolean(
      this.isolatedGuid
      && mesh.element.global_id !== this.isolatedGuid
      && this.ghostContext,
    );
  }

  selection() {
    return this.meshes.find((mesh) => mesh.element.global_id === state.selectedElementGuid) || null;
  }

  focusMeshes(meshes) {
    if (!meshes.length) return;
    const minimum = [Infinity, Infinity, Infinity];
    const maximum = [-Infinity, -Infinity, -Infinity];
    meshes.forEach((mesh) => {
      const bbox = mesh.element.geometry.bbox;
      for (let axis = 0; axis < 3; axis += 1) {
        minimum[axis] = Math.min(minimum[axis], bbox.min[axis]);
        maximum[axis] = Math.max(maximum[axis], bbox.max[axis]);
      }
    });
    this.target = minimum.map((value, axis) => (value + maximum[axis]) / 2);
    const extent = Math.max(...maximum.map((value, axis) => value - minimum[axis]));
    this.distance = Math.max(3, extent * 1.8);
  }

  focusCurrentRule() {
    const visibleMeshes = this.meshes.filter((mesh) => this.meshStatus(mesh));
    this.focusMeshes(visibleMeshes);
  }

  fitSelection() {
    const selected = this.selection();
    if (!selected) return false;
    this.focusMeshes([selected]);
    this.render();
    return true;
  }

  hideSelection() {
    const selected = this.selection();
    if (!selected) return false;
    this.hiddenGuids.add(selected.element.global_id);
    if (this.isolatedGuid === selected.element.global_id) this.isolatedGuid = null;
    this.updateControls();
    renderModelTree();
    this.render();
    return true;
  }

  isolateSelection() {
    const selected = this.selection();
    if (!selected) return false;
    this.hiddenGuids.delete(selected.element.global_id);
    this.isolatedGuid = selected.element.global_id;
    this.focusMeshes([selected]);
    this.updateControls();
    renderModelTree();
    this.render();
    return true;
  }

  showAll() {
    this.hiddenGuids.clear();
    this.isolatedGuid = null;
    this.updateControls();
    renderModelTree();
    this.render();
  }

  standardView(view) {
    if (view === "top") {
      this.yaw = 0;
      this.pitch = 1.48;
    } else if (view === "front") {
      this.yaw = -Math.PI / 2;
      this.pitch = .08;
    } else {
      this.yaw = 0;
      this.pitch = .08;
    }
    this.render();
  }

  toggleProjection() {
    this.projection = this.projection === "perspective" ? "orthographic" : "perspective";
    this.updateControls();
    this.render();
  }

  toggleSection() {
    this.sectionEnabled = !this.sectionEnabled;
    this.updateControls();
    this.render();
  }

  toggleMeasure() {
    this.measureEnabled = !this.measureEnabled;
    this.measurePoints = [];
    dom.measurementHud.hidden = !this.measureEnabled;
    dom.measurementHud.textContent = this.measureEnabled ? t("viewer.measureHint") : "";
    this.updateControls();
  }

  measure(mesh) {
    if (!this.measureEnabled) return;
    if (this.measurePoints.length >= 2) this.measurePoints = [];
    const bbox = mesh.element.geometry.bbox;
    const point = bbox.min.map((value, axis) => (value + bbox.max[axis]) / 2);
    this.measurePoints.push(point);
    dom.measurementHud.hidden = false;
    dom.measurementHud.textContent = this.measurePoints.length < 2
      ? t("viewer.measureHint")
      : t("viewer.measureResult", {
        distance: Math.hypot(
          ...this.measurePoints[0].map((value, axis) => value - this.measurePoints[1][axis]),
        ).toFixed(2),
      });
  }

  encodeViewpoint() {
    const payload = {
      yaw: this.yaw,
      pitch: this.pitch,
      distance: this.distance,
      target: this.target,
      projection: this.projection,
      hidden: [...this.hiddenGuids],
      isolated: this.isolatedGuid,
      ghost: this.ghostContext,
      section: this.sectionEnabled,
      sectionZ: this.sectionZ,
      element: state.selectedElementGuid,
    };
    return btoa(JSON.stringify(payload))
      .replaceAll("+", "-")
      .replaceAll("/", "_")
      .replace(/=+$/, "");
  }

  restoreViewpoint(encoded) {
    if (!encoded) return false;
    try {
      const normalized = encoded.replaceAll("-", "+").replaceAll("_", "/");
      const padded = normalized.padEnd(Math.ceil(normalized.length / 4) * 4, "=");
      const payload = JSON.parse(atob(padded));
      const knownGuids = new Set(this.meshes.map((mesh) => mesh.element.global_id));
      if (![payload.yaw, payload.pitch, payload.distance, payload.sectionZ].every(Number.isFinite)) return false;
      if (!Array.isArray(payload.target) || payload.target.length !== 3 || !payload.target.every(Number.isFinite)) return false;
      this.yaw = payload.yaw;
      this.pitch = payload.pitch;
      this.distance = Math.max(3, Math.min(80, payload.distance));
      this.target = payload.target;
      this.projection = payload.projection === "orthographic" ? "orthographic" : "perspective";
      this.hiddenGuids = new Set((payload.hidden || []).filter((guid) => knownGuids.has(guid)));
      this.isolatedGuid = knownGuids.has(payload.isolated) ? payload.isolated : null;
      this.ghostContext = Boolean(payload.ghost);
      this.sectionEnabled = Boolean(payload.section);
      this.sectionZ = Number(payload.sectionZ);
      dom.sectionLevel.value = String(this.sectionZ);
      if (knownGuids.has(payload.element)) state.selectedElementGuid = payload.element;
      this.updateControls();
      renderModelTree();
      this.render();
      return true;
    } catch {
      return false;
    }
  }

  updateControls() {
    dom.ghostContext.setAttribute("aria-pressed", String(this.ghostContext));
    dom.toggleProjection.setAttribute("aria-pressed", String(this.projection === "orthographic"));
    dom.toggleSection.setAttribute("aria-pressed", String(this.sectionEnabled));
    dom.toggleMeasure.setAttribute("aria-pressed", String(this.measureEnabled));
    dom.sectionControl.hidden = !this.sectionEnabled;
  }

  render(picking = false) {
    this.resize();
    const gl = this.gl;
    gl.useProgram(this.program);
    gl.uniformMatrix4fv(this.mvpLocation, false, this.mvp());
    gl.uniform1i(this.clipEnabledLocation, this.sectionEnabled ? 1 : 0);
    gl.uniform1f(this.clipZLocation, this.sectionZ);
    gl.enable(gl.DEPTH_TEST);
    gl.disable(gl.BLEND);
    gl.clearColor(picking ? 0 : .91, picking ? 0 : .95, picking ? 0 : .95, 1);
    gl.clear(gl.COLOR_BUFFER_BIT | gl.DEPTH_BUFFER_BIT);
    this.meshes.forEach((mesh) => {
      if (!this.visible(mesh)) return;
      gl.bindBuffer(gl.ARRAY_BUFFER, mesh.vertexBuffer);
      gl.enableVertexAttribArray(this.positionLocation);
      gl.vertexAttribPointer(this.positionLocation, 3, gl.FLOAT, false, 0, 0);
      gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER, mesh.indexBuffer);
      const status = this.meshStatus(mesh);
      const color = picking
        ? [
          (mesh.index & 255) / 255,
          ((mesh.index >> 8) & 255) / 255,
          ((mesh.index >> 16) & 255) / 255,
          1,
        ]
        : this.isGhost(mesh)
          ? [.70, .76, .77, 1]
          : status
            ? STATUS[status].color
            : [.66, .74, .75, 1];
      gl.uniform4fv(this.colorLocation, color);
      gl.drawElements(gl.TRIANGLES, mesh.count, gl.UNSIGNED_SHORT, 0);
    });
    if (!picking && state.selectedElementGuid) {
      const selected = this.meshes.find((mesh) => mesh.element.global_id === state.selectedElementGuid && this.visible(mesh));
      if (selected) {
        gl.bindBuffer(gl.ARRAY_BUFFER, selected.vertexBuffer);
        gl.vertexAttribPointer(this.positionLocation, 3, gl.FLOAT, false, 0, 0);
        gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER, selected.edgeBuffer);
        gl.disable(gl.DEPTH_TEST);
        gl.uniform4fv(this.colorLocation, [1, .85, .12, 1]);
        gl.drawElements(gl.LINES, selected.edgeCount, gl.UNSIGNED_SHORT, 0);
      }
    }
  }

  pick(clientX, clientY) {
    this.render(true);
    const rect = this.canvas.getBoundingClientRect();
    const x = Math.floor((clientX - rect.left) * this.canvas.width / rect.width);
    const y = Math.floor((rect.bottom - clientY) * this.canvas.height / rect.height);
    const pixel = new Uint8Array(4);
    this.gl.readPixels(x, y, 1, 1, this.gl.RGBA, this.gl.UNSIGNED_BYTE, pixel);
    this.render(false);
    const pickedIndex = pixel[0] + pixel[1] * 256 + pixel[2] * 65536;
    const mesh = this.meshes.find((item) => item.index === pickedIndex);
    if (mesh) {
      this.measure(mesh);
      selectElement(mesh.element.global_id);
    }
  }

  reset() {
    this.yaw = 1.25; this.pitch = .42; this.distance = 19;
    this.focusCurrentRule();
    this.render();
  }

  initEvents() {
    this.canvas.addEventListener("pointerdown", (event) => {
      this.canvas.setPointerCapture(event.pointerId);
      this.canvas.classList.add("dragging");
      this.drag = { x: event.clientX, y: event.clientY, startX: event.clientX, startY: event.clientY };
    });
    this.canvas.addEventListener("pointermove", (event) => {
      if (!this.drag) return;
      const dx = event.clientX - this.drag.x;
      const dy = event.clientY - this.drag.y;
      this.yaw -= dx * .008;
      this.pitch = Math.max(-.05, Math.min(1.35, this.pitch + dy * .008));
      this.drag.x = event.clientX; this.drag.y = event.clientY;
      this.render();
    });
    this.canvas.addEventListener("pointerup", (event) => {
      if (!this.drag) return;
      const movement = Math.hypot(event.clientX - this.drag.startX, event.clientY - this.drag.startY);
      this.drag = null;
      this.canvas.classList.remove("dragging");
      if (movement < 5) this.pick(event.clientX, event.clientY);
    });
    this.canvas.addEventListener("wheel", (event) => {
      event.preventDefault();
      this.distance = Math.max(5, Math.min(45, this.distance * Math.exp(event.deltaY * .001)));
      this.render();
    }, { passive: false });
  }
}

function normalize(v) {
  const length = Math.hypot(...v) || 1;
  return v.map((value) => value / length);
}
function cross(a, b) {
  return [a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]];
}
function lookAt(eye, target, up) {
  const z = normalize(eye.map((value, index) => value - target[index]));
  const x = normalize(cross(up, z));
  const y = cross(z, x);
  return new Float32Array([
    x[0], y[0], z[0], 0,
    x[1], y[1], z[1], 0,
    x[2], y[2], z[2], 0,
    -x.reduce((sum, value, i) => sum + value * eye[i], 0),
    -y.reduce((sum, value, i) => sum + value * eye[i], 0),
    -z.reduce((sum, value, i) => sum + value * eye[i], 0),
    1,
  ]);
}
function perspective(fov, aspect, near, far) {
  const f = 1 / Math.tan(fov / 2);
  return new Float32Array([
    f / aspect, 0, 0, 0,
    0, f, 0, 0,
    0, 0, (far + near) / (near - far), -1,
    0, 0, (2 * far * near) / (near - far), 0,
  ]);
}
function orthographic(left, right, bottom, top, near, far) {
  return new Float32Array([
    2 / (right - left), 0, 0, 0,
    0, 2 / (top - bottom), 0, 0,
    0, 0, -2 / (far - near), 0,
    -(right + left) / (right - left),
    -(top + bottom) / (top - bottom),
    -(far + near) / (far - near),
    1,
  ]);
}
function multiply(a, b) {
  const out = new Float32Array(16);
  for (let column = 0; column < 4; column += 1) {
    for (let row = 0; row < 4; row += 1) {
      out[column * 4 + row] =
        a[0 * 4 + row] * b[column * 4 + 0] +
        a[1 * 4 + row] * b[column * 4 + 1] +
        a[2 * 4 + row] * b[column * 4 + 2] +
        a[3 * 4 + row] * b[column * 4 + 3];
    }
  }
  return out;
}

const viewer = new IFCWebGLViewer(document.querySelector("#viewer"));
dom.resetView.addEventListener("click", () => viewer.reset());
const withSelection = (operation) => {
  if (!operation()) showToast(t("viewer.noSelection"));
};
dom.fitSelection.addEventListener("click", () => withSelection(() => viewer.fitSelection()));
dom.hideSelection.addEventListener("click", () => withSelection(() => viewer.hideSelection()));
dom.isolateSelection.addEventListener("click", () => withSelection(() => viewer.isolateSelection()));
dom.showAll.addEventListener("click", () => viewer.showAll());
dom.ghostContext.addEventListener("click", () => {
  viewer.ghostContext = !viewer.ghostContext;
  viewer.updateControls();
  viewer.render();
});
dom.toggleProjection.addEventListener("click", () => viewer.toggleProjection());
dom.frontView.addEventListener("click", () => viewer.standardView("front"));
dom.topView.addEventListener("click", () => viewer.standardView("top"));
dom.rightView.addEventListener("click", () => viewer.standardView("right"));
dom.toggleSection.addEventListener("click", () => viewer.toggleSection());
dom.sectionLevel.addEventListener("input", () => {
  viewer.sectionZ = Number(dom.sectionLevel.value);
  viewer.render();
});
dom.toggleMeasure.addEventListener("click", () => viewer.toggleMeasure());
dom.saveView.addEventListener("click", () => {
  const encoded = viewer.encodeViewpoint();
  localStorage.setItem("ifc-compliance-viewpoint", encoded);
  syncUrl({ view: encoded });
  showToast(t("viewer.viewSaved"));
});
dom.restoreView.addEventListener("click", () => {
  const parameters = new URLSearchParams(window.location.search);
  const restored = viewer.restoreViewpoint(
    parameters.get("view") || localStorage.getItem("ifc-compliance-viewpoint"),
  );
  if (!restored) {
    showToast(t("viewer.noSavedView"));
    return;
  }
  if (state.selectedElementGuid) selectElement(state.selectedElementGuid);
  else renderLocalizedUi();
  showToast(t("viewer.viewRestored"));
});
dom.modelSearch.addEventListener("input", () => renderModelTree());
dom.reloadRuns.addEventListener("click", () => loadRuns().catch((error) => {
  showToast(t("toast.failed", { error: error.message }));
}));
dom.queryForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  dom.queryRun.disabled = true;
  dom.queryRun.textContent = t("query.running");
  try {
    state.queryResponse = await api("/api/query/execute", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        utterance: dom.queryInput.value,
        locale: state.locale,
        context: {
          rule_id: state.selectedRuleId,
          element_guid: state.selectedElementGuid,
          model_id: state.modelId,
        },
      }),
    });
    renderQuery();
  } catch (error) {
    showToast(t("toast.failed", { error: error.message }));
  } finally {
    dom.queryRun.disabled = false;
    dom.queryRun.textContent = t("query.run");
  }
});
dom.localeSelect.addEventListener("change", () => {
  state.locale = dom.localeSelect.value;
  localStorage.setItem("ifc-compliance-locale", state.locale);
  syncUrl();
  renderLocalizedUi();
  renderGraph().catch(console.error);
});
dom.reloadModels.addEventListener("click", () => loadModels().catch((error) => {
  showToast(t("toast.failed", { error: error.message }));
}));
dom.chooseIfcFile.addEventListener("click", () => dom.ifcFile.click());
dom.ifcFile.addEventListener("change", () => renderImportProgress());
dom.importForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const file = dom.ifcFile.files[0];
  if (!file) {
    showToast(t("models.chooseFile"));
    return;
  }
  dom.importModel.disabled = true;
  dom.importModel.textContent = t("models.importing");
  state.importNotice = { type: "progress", phase: "queued", progress: 0 };
  renderImportProgress();
  try {
    const parameters = new URLSearchParams({
      filename: file.name,
      source: dom.modelSource.value.trim() || "local user upload",
      license: dom.modelLicense.value.trim() || "user-provided; redistribution not granted",
    });
    const submitted = await api(`/api/import-jobs?${parameters}`, {
      method: "POST",
      headers: { "Content-Type": file.type || "application/x-step" },
      body: file,
    });
    let job = submitted;
    for (let attempt = 0; attempt < 120; attempt += 1) {
      job = await api(submitted.poll_url);
      state.importNotice = {
        type: "progress",
        phase: job.phase,
        progress: job.progress,
      };
      renderImportProgress();
      if (["COMPLETED", "FAILED", "CANCELLED"].includes(job.status)) break;
      await new Promise((resolve) => setTimeout(resolve, 250));
    }
    if (job.status !== "COMPLETED") {
      const code = job.error?.code || "UNKNOWN";
      const error = new Error(t(`models.error.${code}`));
      error.code = code;
      throw error;
    }
    state.importNotice = { type: "success", modelId: job.model_id };
    renderImportProgress();
    await loadModels();
    showToast(t("models.imported", { modelId: job.model_id }));
  } catch (error) {
    state.importNotice = { type: "error", code: error.code || "UNKNOWN" };
    renderImportProgress();
  } finally {
    dom.importModel.disabled = false;
    dom.importModel.textContent = t("models.import");
  }
});
dom.runChecks.addEventListener("click", async () => {
  dom.runChecks.disabled = true;
  dom.runChecks.textContent = t("action.running");
  try {
    const response = await api(withModel("/api/checks/run"), { method: "POST" });
    state.results = response.results;
    renderStatusControls();
    renderResults();
    renderEvidence();
    viewer.render();
    await loadRuns();
    syncUrl({ run: response.run_id });
    showToast(t("toast.completed", {
      count: response.result_count,
      runId: response.run_id.slice(0, 16),
    }));
  } catch (error) {
    showToast(t("toast.failed", { error: error.message }));
  } finally {
    dom.runChecks.disabled = false;
    dom.runChecks.textContent = t("action.run");
  }
});

async function init() {
  try {
    state.messages = await api("/static/i18n.json");
    state.locale = preferredLocale();
    applyStaticTranslations();
    const [models, importJobs] = await Promise.all([
      api("/api/models"),
      api("/api/import-jobs?limit=20"),
    ]);
    state.models = models;
    state.importJobs = importJobs.items;
    const parameters = new URLSearchParams(window.location.search);
    const requestedModel = parameters.get("model");
    state.modelId = models.some((model) => model.model_id === requestedModel)
      ? requestedModel
      : models.find((model) => model.source_kind === "FIXTURE")?.model_id
        || models[0]?.model_id;
    if (!state.modelId) throw new Error("No local model is available.");
    const [health, rules, results, scene, ids, runs] = await Promise.all([
      api("/api/health"),
      api(withModel("/api/rules")),
      api(withModel("/api/results")),
      api(withModel("/api/scene")),
      api(withModel("/api/ids/report")),
      api(withModel("/api/check-runs?limit=50")),
    ]);
    state.health = { ...health, element_count: scene.elements.length };
    state.rules = rules;
    state.results = results;
    state.elements = scene.elements;
    state.ids = ids;
    state.runs = runs.items;
    const requestedRule = parameters.get("rule");
    const requestedElement = parameters.get("element");
    state.selectedRuleId = rules.some((rule) => rule.rule_id === requestedRule)
      ? requestedRule
      : rules[0]?.rule_id || null;
    state.selectedElementGuid = scene.elements.some((element) => element.global_id === requestedElement)
      ? requestedElement
      : null;
    dom.healthDot.classList.add("ready");
    viewer.load(scene.elements);
    selectRule(state.selectedRuleId);
    const restored = viewer.restoreViewpoint(
      parameters.get("view") || localStorage.getItem("ifc-compliance-viewpoint"),
    );
    if (restored && state.selectedElementGuid) selectElement(state.selectedElementGuid);
    renderLocalizedUi();
    syncUrl();
  } catch (error) {
    dom.healthText.textContent = t("app.loadFailed");
    dom.evidencePanel.innerHTML = `<p class="empty-copy">${escapeHtml(t("toast.failed", { error: error.message }))}</p>`;
    console.error(error);
  }
}

init();
