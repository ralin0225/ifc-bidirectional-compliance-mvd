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
  queryResponse: null,
  ids: null,
  health: null,
  selectedRuleId: null,
  selectedElementGuid: null,
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
  renderQuery();
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
    const detail = await response.text();
    throw new Error(`${response.status} ${detail}`);
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
  const graph = await api(`/api/graph/ego?${query}`);
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
  const response = await api("/api/check-runs?limit=50");
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
    this.program = this.createProgram();
    this.positionLocation = this.gl.getAttribLocation(this.program, "aPosition");
    this.mvpLocation = this.gl.getUniformLocation(this.program, "uMVP");
    this.colorLocation = this.gl.getUniformLocation(this.program, "uColor");
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
      void main() { gl_Position = uMVP * vec4(aPosition, 1.0); }
    `);
    const fragment = compile(gl.FRAGMENT_SHADER, `
      precision mediump float;
      uniform vec4 uColor;
      void main() { gl_FragColor = uColor; }
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
    this.meshes = elements.map((element, index) => {
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
    return multiply(perspective(Math.PI / 4, this.canvas.width / this.canvas.height, .05, 100), lookAt(eye, this.target, [0, 0, 1]));
  }

  meshStatus(mesh) {
    return resultFor(state.selectedRuleId, mesh.element.global_id)?.status || null;
  }

  visible(mesh) {
    const status = this.meshStatus(mesh);
    return Boolean(status) && state.activeStatuses.has(status);
  }

  focusCurrentRule() {
    const visibleMeshes = this.meshes.filter((mesh) => this.meshStatus(mesh));
    if (!visibleMeshes.length) return;
    const minimum = [Infinity, Infinity, Infinity];
    const maximum = [-Infinity, -Infinity, -Infinity];
    visibleMeshes.forEach((mesh) => {
      const bbox = mesh.element.geometry.bbox;
      for (let axis = 0; axis < 3; axis += 1) {
        minimum[axis] = Math.min(minimum[axis], bbox.min[axis]);
        maximum[axis] = Math.max(maximum[axis], bbox.max[axis]);
      }
    });
    this.target = minimum.map((value, axis) => (value + maximum[axis]) / 2);
    const extent = Math.max(...maximum.map((value, axis) => value - minimum[axis]));
    this.distance = Math.max(6, extent * 1.55);
  }

  render(picking = false) {
    this.resize();
    const gl = this.gl;
    gl.useProgram(this.program);
    gl.uniformMatrix4fv(this.mvpLocation, false, this.mvp());
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
        ? [mesh.index / 255, 0, 0, 1]
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
    const mesh = this.meshes.find((item) => item.index === pixel[0]);
    if (mesh) selectElement(mesh.element.global_id);
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
dom.runChecks.addEventListener("click", async () => {
  dom.runChecks.disabled = true;
  dom.runChecks.textContent = t("action.running");
  try {
    const response = await api("/api/checks/run", { method: "POST" });
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
    const [health, rules, results, scene, ids, runs] = await Promise.all([
      api("/api/health"),
      api("/api/rules"),
      api("/api/results"),
      api("/api/scene"),
      api("/api/ids/report"),
      api("/api/check-runs?limit=50"),
    ]);
    state.health = health;
    state.rules = rules;
    state.results = results;
    state.elements = scene.elements;
    state.ids = ids;
    state.runs = runs.items;
    const parameters = new URLSearchParams(window.location.search);
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
    renderLocalizedUi();
    syncUrl();
  } catch (error) {
    dom.healthText.textContent = t("app.loadFailed");
    dom.evidencePanel.innerHTML = `<p class="empty-copy">${escapeHtml(t("toast.failed", { error: error.message }))}</p>`;
    console.error(error);
  }
}

init();
