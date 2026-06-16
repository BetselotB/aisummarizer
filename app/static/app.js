const TIER_HINTS = {
  concise: "Short chapters, key facts only — fastest to generate.",
  standard: "Balanced chapters with tables, examples, and exam traps.",
  detailed: "AI master plan first, then richer in-depth chapters.",
  comprehensive: "Full AI structural plan, then section-by-section deep notes — best for exams.",
};

const $ = (sel) => document.querySelector(sel);
const LS_KEY = "aisg_v1";

const selectedFiles = [];
let saveTimer = null;
let expandedLogs = new Set(JSON.parse(localStorage.getItem(`${LS_KEY}_expanded_logs`) || "[]"));
let expandedSteps = new Set(JSON.parse(localStorage.getItem(`${LS_KEY}_expanded_steps`) || "[]"));

// ── Persistence ─────────────────────────────────────────────────────────────

function loadLocalState() {
  try {
    return JSON.parse(localStorage.getItem(LS_KEY) || "{}");
  } catch {
    return {};
  }
}

function saveLocalState(partial) {
  const state = { ...loadLocalState(), ...partial, _updated: new Date().toISOString() };
  localStorage.setItem(LS_KEY, JSON.stringify(state));
  flashSaved();
  scheduleServerSync(state);
}

function flashSaved() {
  const el = $("#savedIndicator");
  if (!el) return;
  el.textContent = "saved";
  clearTimeout(flashSaved._t);
  flashSaved._t = setTimeout(() => { el.textContent = ""; }, 2000);
}

function scheduleServerSync(state) {
  clearTimeout(saveTimer);
  saveTimer = setTimeout(async () => {
    try {
      const { theme, jobTitle, jobContext, textTitle, textContext, keyLabelPrefix, fileNames, geminiModel, openrouterModel, grokModel, llmProvider, detailTier, textDetailTier } = state;
      await api("/api/state", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          state: { theme, jobTitle, jobContext, textTitle, textContext, keyLabelPrefix, fileNames, geminiModel, openrouterModel, grokModel, llmProvider, detailTier, textDetailTier },
        }),
      });
    } catch { /* offline ok */ }
  }, 800);
}

async function restoreState() {
  let state = loadLocalState();
  try {
    const remote = await api("/api/state");
    state = { ...remote.state, ...state };
  } catch { /* use local only */ }

  if (state.theme) applyTheme(state.theme);
  if (state.jobTitle) $("#jobTitle").value = state.jobTitle;
  if (state.jobContext) $("#jobContext").value = state.jobContext;
  if (state.textTitle) $("#textTitle").value = state.textTitle;
  if (state.textContext) $("#textContext").value = state.textContext;
  if (state.keyLabelPrefix) $("#keyLabelPrefix").value = state.keyLabelPrefix;
  if (state.geminiModel && $("#geminiModel")) $("#geminiModel").value = state.geminiModel;
  if (state.openrouterModel && $("#openrouterModel")) $("#openrouterModel").value = state.openrouterModel;
  if (state.grokModel && $("#grokModel")) $("#grokModel").value = state.grokModel;
  if (state.llmProvider && $("#llmProvider")) {
    $("#llmProvider").value = state.llmProvider;
    updateProviderUI(state.llmProvider);
  }
  if (state.detailTier && $("#detailTier")) {
    $("#detailTier").value = state.detailTier;
    updateTierHint(state.detailTier);
  }
  if (state.textDetailTier && $("#textDetailTier")) {
    $("#textDetailTier").value = state.textDetailTier;
  }
  if (state.fileNames?.length) {
    const zone = $("#dropZone");
    if (zone) zone.querySelector(".drop-title").textContent =
      `${state.fileNames.length} file(s) remembered — re-add PDFs to run again`;
  }
}

function trackActivity(message, kind = "ui", meta = null) {
  saveLocalState({
    lastActivity: { message, kind, at: new Date().toISOString() },
  });
  api("/api/activity", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ kind, message, meta }),
  }).catch(() => {});
}

function bindAutoSave() {
  const fields = [
    ["#jobTitle", "jobTitle"],
    ["#jobContext", "jobContext"],
    ["#textTitle", "textTitle"],
    ["#textContext", "textContext"],
    ["#keyLabelPrefix", "keyLabelPrefix"],
  ];
  for (const [sel, key] of fields) {
    const el = $(sel);
    if (!el) continue;
    el.addEventListener("input", () => saveLocalState({ [key]: el.value }));
  }
}

function updateTierHint(tier) {
  const hint = $("#tierHint");
  if (hint) hint.textContent = TIER_HINTS[tier] || TIER_HINTS.standard;
}

function applyTheme(theme) {
  document.documentElement.setAttribute("data-theme", theme);
  saveLocalState({ theme });
  $("#themeToggle").textContent = theme === "light" ? "●" : "◐";
}

// ── Files ───────────────────────────────────────────────────────────────────

function fileKey(file) {
  return `${file.name}::${file.size}::${file.lastModified}`;
}

function isPdf(file) {
  return file.name.toLowerCase().endsWith(".pdf") || file.type === "application/pdf";
}

function formatSize(bytes) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function formatDuration(sec) {
  if (sec == null) return "—";
  if (sec < 60) return `${sec}s`;
  const m = Math.floor(sec / 60);
  const s = sec % 60;
  return `${m}m ${s}s`;
}

function addFiles(incoming) {
  let added = 0;
  const existing = new Set(selectedFiles.map(fileKey));
  for (const file of incoming) {
    if (!isPdf(file)) { toast(`Skipped non-PDF: ${file.name}`); continue; }
    const key = fileKey(file);
    if (existing.has(key)) continue;
    existing.add(key);
    selectedFiles.push(file);
    added += 1;
  }
  if (added > 0) {
    renderFileList();
    saveLocalState({ fileNames: selectedFiles.map((f) => f.name) });
    trackActivity(`Added ${added} PDF(s)`, "files");
  } else if (incoming.length > 0 && incoming.some(isPdf)) {
    toast("Those PDFs are already in the list");
  }
  return added;
}

function removeFile(index) {
  selectedFiles.splice(index, 1);
  renderFileList();
  saveLocalState({ fileNames: selectedFiles.map((f) => f.name) });
}

function clearFiles() {
  selectedFiles.length = 0;
  renderFileList();
  saveLocalState({ fileNames: [] });
  $("#fileInput").value = "";
}

function renderFileList() {
  const list = $("#fileList");
  const actions = $("#fileActions");
  const zone = $("#dropZone");
  if (!selectedFiles.length) {
    list.hidden = true;
    actions.hidden = true;
    list.innerHTML = "";
    zone.querySelector(".drop-title").textContent = "Drag & drop PDFs here";
    return;
  }
  list.hidden = false;
  actions.hidden = false;
  zone.querySelector(".drop-title").textContent = `${selectedFiles.length} file${selectedFiles.length === 1 ? "" : "s"} selected`;
  list.innerHTML = selectedFiles.map((file, i) => `
    <li>
      <span class="file-name" title="${escapeHtml(file.name)}">${escapeHtml(file.name)}</span>
      <span class="file-meta">${formatSize(file.size)}</span>
      <button type="button" class="remove-file" data-index="${i}">×</button>
    </li>`).join("");
  list.querySelectorAll(".remove-file").forEach((btn) => {
    btn.addEventListener("click", (e) => { e.stopPropagation(); removeFile(Number(btn.dataset.index)); });
  });
}

function initFileUpload() {
  const zone = $("#dropZone");
  const input = $("#fileInput");
  zone.addEventListener("click", (e) => { if (!e.target.closest(".link-btn")) input.click(); });
  $("#browseFiles").addEventListener("click", (e) => { e.preventDefault(); input.click(); });
  input.addEventListener("change", () => { if (input.files?.length) addFiles(Array.from(input.files)); input.value = ""; });
  $("#clearFiles").addEventListener("click", (e) => { e.stopPropagation(); clearFiles(); });
  ["dragenter", "dragover"].forEach((evt) => zone.addEventListener(evt, (e) => { e.preventDefault(); zone.classList.add("drag-over"); }));
  ["dragleave", "drop"].forEach((evt) => zone.addEventListener(evt, (e) => { e.preventDefault(); zone.classList.remove("drag-over"); }));
  zone.addEventListener("drop", (e) => addFiles(Array.from(e.dataTransfer?.files || [])));
}

// ── API ─────────────────────────────────────────────────────────────────────

function toast(msg) {
  const el = $("#toast");
  el.textContent = msg;
  el.classList.remove("hidden");
  setTimeout(() => el.classList.add("hidden"), 3500);
}

async function api(path, opts = {}) {
  const res = await fetch(path, opts);
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.detail || data.message || res.statusText);
  return data;
}

async function refreshHealth() {
  try {
    const h = await api("/api/health");
    const el = $("#healthStatus");
    const provider = h.llm_provider || "gemini";
    const model = h.model || h.gemini_model || h.openrouter_model || h.grok_model || "?";
    const keys = h.api_keys ?? h.gemini_keys ?? 0;
    el.textContent = `${provider} · ${keys} keys · ${model} · ${h.active_jobs.length} running`;
    el.className = "status-pill " + (keys > 0 ? "ok" : "bad");
    const gemini = h.gemini_keys ?? 0;
    const or = h.openrouter_keys ?? 0;
    const grok = h.grok_keys ?? 0;
    $("#keyCount").textContent = `${keys} keys (${gemini} Gemini, ${or} OpenRouter, ${grok} Grok)`;
    if (h.llm_provider && $("#llmProvider")) {
      $("#llmProvider").value = h.llm_provider;
      updateProviderUI(h.llm_provider);
    }
    if (h.gemini_model && $("#geminiModel")) $("#geminiModel").value = h.gemini_model;
    if (h.openrouter_model && $("#openrouterModel")) $("#openrouterModel").value = h.openrouter_model;
    if (h.grok_model && $("#grokModel")) $("#grokModel").value = h.grok_model;
  } catch {
    $("#healthStatus").textContent = "Offline";
    $("#healthStatus").className = "status-pill bad";
  }
}

async function loadConfig() {
  try {
    const cfg = await api("/api/config");
    if (cfg.llm_provider && $("#llmProvider")) {
      $("#llmProvider").value = cfg.llm_provider;
      updateProviderUI(cfg.llm_provider);
    }
    if (cfg.gemini_model && $("#geminiModel")) $("#geminiModel").value = cfg.gemini_model;
    if (cfg.openrouter_model && $("#openrouterModel")) $("#openrouterModel").value = cfg.openrouter_model;
    if (cfg.grok_model && $("#grokModel")) $("#grokModel").value = cfg.grok_model;
  } catch { /* ignore */ }
}

function updateProviderUI(provider) {
  const geminiGroup = $("#geminiModelGroup");
  const orGroup = $("#openrouterModelGroup");
  const grokGroup = $("#grokModelGroup");
  if (geminiGroup) geminiGroup.hidden = provider !== "gemini";
  if (orGroup) orGroup.hidden = provider !== "openrouter";
  if (grokGroup) grokGroup.hidden = provider !== "grok";
}

async function saveConfig(partial) {
  await api("/api/config", {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(partial),
  });
  saveLocalState(partial);
  refreshHealth();
}

function initModelSelector() {
  const providerSel = $("#llmProvider");
  if (providerSel) {
    providerSel.addEventListener("change", async () => {
      try {
        await saveConfig({ llm_provider: providerSel.value });
        updateProviderUI(providerSel.value);
        trackActivity(`Provider: ${providerSel.value}`, "config");
        toast(`Provider set to ${providerSel.value}`);
      } catch (err) { toast(err.message); }
    });
  }

  const geminiSel = $("#geminiModel");
  if (geminiSel) {
    geminiSel.addEventListener("change", async () => {
      try {
        await saveConfig({ gemini_model: geminiSel.value });
        trackActivity(`Gemini model: ${geminiSel.value}`, "config");
        toast(`Gemini model set to ${geminiSel.value}`);
      } catch (err) { toast(err.message); }
    });
  }

  const orSel = $("#openrouterModel");
  if (orSel) {
    orSel.addEventListener("change", async () => {
      try {
        await saveConfig({ openrouter_model: orSel.value });
        trackActivity(`OpenRouter model: ${orSel.value}`, "config");
        toast(`OpenRouter model set to ${orSel.value}`);
      } catch (err) { toast(err.message); }
    });
  }

  const grokSel = $("#grokModel");
  if (grokSel) {
    grokSel.addEventListener("change", async () => {
      try {
        await saveConfig({ grok_model: grokSel.value });
        trackActivity(`Grok model: ${grokSel.value}`, "config");
        toast(`Grok model set to ${grokSel.value}`);
      } catch (err) { toast(err.message); }
    });
  }
}

async function loadKeys() {
  const { keys } = await api("/api/keys");
  const list = $("#keyList");
  if (!keys.length) {
    list.innerHTML = '<li class="empty">No keys yet.</li>';
    return;
  }
  list.innerHTML = keys.map((k) => `
    <li>
      <div>
        <div>${escapeHtml(k.label)} <span class="badge">${k.provider || "?"}</span> ${k.enabled ? "" : "(off)"}</div>
        <div class="meta">${k.masked_key} · ${k.requests_count} calls</div>
        ${k.last_error ? `<div class="meta">${escapeHtml(k.last_error.slice(0, 80))}</div>` : ""}
      </div>
      <div class="actions">
        <button class="btn ghost" data-toggle="${k.id}" data-enabled="${k.enabled ? "1" : "0"}">${k.enabled ? "Disable" : "Enable"}</button>
        <button class="btn danger" data-delete="${k.id}">Remove</button>
      </div>
    </li>`).join("");

  list.querySelectorAll("[data-delete]").forEach((btn) => {
    btn.addEventListener("click", async () => {
      await api(`/api/keys/${btn.dataset.delete}`, { method: "DELETE" });
      trackActivity("Removed API key", "keys");
      loadKeys(); refreshHealth();
    });
  });
  list.querySelectorAll("[data-toggle]").forEach((btn) => {
    btn.addEventListener("click", async () => {
      await api(`/api/keys/${btn.dataset.toggle}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ enabled: btn.dataset.enabled !== "1" }),
      });
      loadKeys(); refreshHealth();
    });
  });
}

async function loadActivity() {
  try {
    const { activity } = await api("/api/activity");
    const list = $("#activityList");
    $("#activityCount").textContent = `${activity.length} events`;
    if (!activity.length) {
      list.innerHTML = '<li class="empty">No activity yet.</li>';
      return;
    }
    list.innerHTML = [...activity].reverse().slice(0, 50).map((a) => `
      <li>
        <div class="act-time">${new Date(a.created_at).toLocaleString()} · ${escapeHtml(a.kind)}</div>
        <div class="act-msg">${escapeHtml(a.message)}</div>
      </li>`).join("");
  } catch { /* ignore */ }
}

// ── Jobs ────────────────────────────────────────────────────────────────────

function stepIcon(status) {
  if (status === "done") return "✓";
  if (status === "running") return "→";
  if (status === "failed") return "✗";
  return "·";
}

function renderSteps(job) {
  const steps = job.stats?.steps || [];
  if (!steps.length) return "";
  const show = expandedSteps.has(job.id) || job.status === "running" || job.status === "failed";
  if (!show && steps.length > 4) {
    return `<button type="button" class="btn ghost toggle-steps" data-job="${job.id}">Show ${steps.length} steps</button>`;
  }
  return `<ul class="step-list">${steps.map((s) => `
    <li class="${s.status}">
      <span class="step-icon ${s.status}">${stepIcon(s.status)}</span>
      <div class="step-body">
        ${escapeHtml(s.label)}
        ${s.error ? `<div class="step-error">${escapeHtml(s.error)}</div>` : ""}
      </div>
    </li>`).join("")}</ul>`;
}

function renderStats(job) {
  const s = job.stats || {};
  const elapsed = s.elapsed_seconds ?? (job.started_at && job.status === "running"
    ? Math.floor((Date.now() - new Date(job.started_at).getTime()) / 1000) : null);
  return `<div class="job-stats">
    <div class="stat-box"><div class="stat-label">Progress</div><div class="stat-value">${Math.round(job.progress || 0)}%</div></div>
    <div class="stat-box"><div class="stat-label">Elapsed</div><div class="stat-value">${formatDuration(elapsed)}</div></div>
    <div class="stat-box"><div class="stat-label">API calls</div><div class="stat-value">${s.api_calls ?? 0}</div></div>
    <div class="stat-box"><div class="stat-label">Chapters</div><div class="stat-value">${s.chapters_done ?? 0}/${s.chapters_total ?? "—"}</div></div>
    <div class="stat-box"><div class="stat-label">Source</div><div class="stat-value">${s.source_chars ? `${(s.source_chars / 1000).toFixed(1)}k` : "—"} chars</div></div>
    <div class="stat-box"><div class="stat-label">Files</div><div class="stat-value">${(s.source_file_names || []).length || "—"}</div></div>
  </div>`;
}

function renderJob(job) {
  const pct = job.status === "completed" ? 100 : Math.min(99, Math.round(job.progress || 0));
  const isActive = job.status === "running" || job.status === "pending";
  const logsOpen = expandedLogs.has(job.id) || job.status === "failed" || job.status === "running";

  let body = renderStats(job);

  if (isActive || job.status === "completed") {
    body += `<div class="progress-wrap">
      <div class="progress-header"><span>${job.status}</span><span>${pct}%</span></div>
      <div class="progress-bar"><div class="progress-fill" style="width:${pct}%"></div></div>
      <div class="progress-msg">${escapeHtml(job.message || "Working…")}</div>
    </div>`;
  }

  body += renderSteps(job);

  if (job.status === "failed") {
    body += `<div class="error-banner">${escapeHtml(job.error || "Unknown error")}</div>`;
    if (job.stats?.error_step) {
      body += `<div class="progress-msg">Failed at step: <b>${escapeHtml(job.stats.error_step)}</b></div>`;
    }
    if (job.can_resume) {
      const saved = job.chapters_saved ?? job.stats?.chapters_done ?? 0;
      const total = job.chapters_total ?? job.stats?.chapters_total ?? "?";
      body += `<div class="progress-msg">Checkpoint: ${saved}/${total} chapters saved — resume skips completed work</div>`;
    }
  }

  const actions = [];
  if (job.can_resume) {
    const busy = resumingJobs.has(job.id);
    actions.push(
      `<button type="button" class="linkish resume-job" data-job="${job.id}" ${busy ? "disabled" : ""}>${busy ? "Resuming…" : "Resume job"}</button>`
    );
  }
  if (job.status === "completed") {
    actions.push(`<a href="/api/jobs/${job.id}/download">Download PDF</a>`);
    actions.push(`<a href="/api/jobs/${job.id}/document.json">Download JSON</a>`);
  }
  actions.push(`<button type="button" class="linkish toggle-logs" data-job="${job.id}">${logsOpen ? "Hide" : "Show"} logs</button>`);
  if (job.stats?.steps?.length > 4) {
    actions.push(`<button type="button" class="linkish toggle-steps" data-job="${job.id}">${expandedSteps.has(job.id) ? "Hide" : "Show"} steps</button>`);
  }

  return `<div class="job-item ${job.status}" data-id="${job.id}">
    <div class="job-top">
      <div>
        <div class="job-title">${escapeHtml(job.title)}</div>
        <div class="job-meta">${new Date(job.created_at).toLocaleString()} · ${job.id.slice(0, 8)}${job.detail_tier ? ` · <span class="badge">${escapeHtml(job.detail_tier)}</span>` : ""}</div>
      </div>
      <span class="status ${job.status}">${job.status}</span>
    </div>
    ${body}
    <div class="job-actions">${actions.join("")}</div>
    <div class="log-box ${logsOpen ? "open" : ""}" id="logs-${job.id}"></div>
  </div>`;
}

function escapeHtml(s) {
  return String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}

async function loadJobLogs(jobId, box) {
  const { logs } = await api(`/api/jobs/${jobId}/logs`);
  box.innerHTML = logs.map((l) =>
    `<div class="${l.level === "error" ? "log-error" : ""}">[${l.created_at.slice(11, 19)}] ${escapeHtml(l.message)}</div>`
  ).join("");
}

let resumingJobs = new Set();

async function loadJobs() {
  const { jobs } = await api("/api/jobs");
  const el = $("#jobList");
  if (!jobs.length) {
    el.innerHTML = '<div class="empty">No jobs yet.</div>';
    return;
  }
  el.innerHTML = jobs.map(renderJob).join("");

  for (const job of jobs) {
    const box = document.getElementById(`logs-${job.id}`);
    if (box?.classList.contains("open")) await loadJobLogs(job.id, box);
  }

  el.querySelectorAll(".toggle-logs").forEach((btn) => {
    btn.addEventListener("click", async () => {
      const box = document.getElementById(`logs-${btn.dataset.job}`);
      if (box.classList.contains("open")) {
        box.classList.remove("open");
        expandedLogs.delete(btn.dataset.job);
      } else {
        await loadJobLogs(btn.dataset.job, box);
        box.classList.add("open");
        expandedLogs.add(btn.dataset.job);
      }
      localStorage.setItem(`${LS_KEY}_expanded_logs`, JSON.stringify([...expandedLogs]));
      loadJobs();
    });
  });

  el.querySelectorAll(".toggle-steps").forEach((btn) => {
    btn.addEventListener("click", () => {
      const id = btn.dataset.job;
      if (expandedSteps.has(id)) expandedSteps.delete(id);
      else expandedSteps.add(id);
      localStorage.setItem(`${LS_KEY}_expanded_steps`, JSON.stringify([...expandedSteps]));
      loadJobs();
    });
  });

  el.querySelectorAll(".resume-job").forEach((btn) => {
    btn.addEventListener("click", async () => {
      const jobId = btn.dataset.job;
      if (resumingJobs.has(jobId)) return;
      resumingJobs.add(jobId);
      loadJobs();
      try {
        const res = await api(`/api/jobs/${jobId}/resume`, { method: "POST" });
        trackActivity(`Resumed job from ${res.resume_from}`, "job_resumed", { job_id: res.job_id });
        toast(`Resuming from ${res.resume_from}`);
        poll();
      } catch (err) {
        toast(err.message);
      } finally {
        resumingJobs.delete(jobId);
        loadJobs();
      }
    });
  });
}

// ── Forms ───────────────────────────────────────────────────────────────────

$("#jobForm").addEventListener("submit", async (e) => {
  e.preventDefault();
  if (!selectedFiles.length) { toast("Add at least one PDF"); return; }
  const btn = $("#submitBtn");
  btn.disabled = true;
  btn.textContent = "Starting…";
  const fd = new FormData();
  fd.append("title", $("#jobTitle").value.trim());
  fd.append("extra_context", $("#jobContext").value.trim());
  const providerSel = $("#llmProvider");
  if (providerSel) fd.append("llm_provider", providerSel.value);
  const tierSel = $("#detailTier");
  if (tierSel) fd.append("detail_tier", tierSel.value);
  for (const file of selectedFiles) fd.append("files", file, file.name);
  try {
    const { job } = await api("/api/jobs", { method: "POST", body: fd });
    trackActivity(`Started job: ${$("#jobTitle").value.trim()}`, "job_started", { job_id: job.id });
    toast("Job started");
    clearFiles();
    loadJobs(); loadActivity(); refreshHealth();
    poll();
  } catch (err) { toast(err.message); }
  finally { btn.disabled = false; btn.textContent = "Generate study guide"; }
});

$("#textForm").addEventListener("submit", async (e) => {
  e.preventDefault();
  const title = $("#textTitle").value.trim();
  const extra_context = $("#textContext").value.trim();
  try {
    const { job } = await api("/api/jobs/text-only", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        title,
        extra_context,
        llm_provider: $("#llmProvider")?.value || "gemini",
        detail_tier: $("#textDetailTier")?.value || $("#detailTier")?.value || "standard",
      }),
    });
    trackActivity(`Started text job: ${title}`, "job_started", { job_id: job.id });
    toast("Text job started");
    loadJobs(); loadActivity();
    poll();
  } catch (err) { toast(err.message); }
});

$("#bulkKeyForm").addEventListener("submit", async (e) => {
  e.preventDefault();
  try {
    const res = await api("/api/keys/bulk", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ keys_text: $("#bulkKeys").value, label_prefix: $("#keyLabelPrefix").value || "API" }),
    });
    trackActivity(`Added ${res.added} API key(s)`, "keys");
    toast(`Added ${res.added} key(s)`);
    if (res.rejected?.length) {
      toast(`${res.rejected.length} key(s) rejected — use AIza…, sk-or-v1-…, or xai-… keys`);
    }
    $("#bulkKeys").value = "";
    loadKeys(); refreshHealth(); loadActivity();
  } catch (err) { toast(err.message); }
});

$("#refreshJobs").addEventListener("click", () => { loadJobs(); loadActivity(); });
$("#themeToggle").addEventListener("click", () => {
  const next = document.documentElement.getAttribute("data-theme") === "light" ? "dark" : "light";
  applyTheme(next);
  trackActivity(`Theme: ${next}`, "ui");
});

async function poll() {
  const { jobs } = await api("/api/jobs");
  const running = jobs.some((j) => j.status === "running" || j.status === "pending");
  await loadJobs();
  await loadActivity();
  if (running) setTimeout(poll, 2500);
}

function initDetailTier() {
  const tierSel = $("#detailTier");
  if (!tierSel) return;
  tierSel.addEventListener("change", () => {
    updateTierHint(tierSel.value);
    saveLocalState({ detailTier: tierSel.value });
  });
  const textTier = $("#textDetailTier");
  if (textTier) {
    textTier.addEventListener("change", () => saveLocalState({ textDetailTier: textTier.value }));
  }
  updateTierHint(tierSel.value);
}

// ── Boot ────────────────────────────────────────────────────────────────────

initFileUpload();
initModelSelector();
initDetailTier();
bindAutoSave();
loadConfig();
restoreState().then(() => {
  refreshHealth();
  loadKeys();
  loadJobs();
  loadActivity();
  api("/api/jobs").then(({ jobs }) => {
    if (jobs.some((j) => j.status === "running" || j.status === "pending")) poll();
  });
});
setInterval(refreshHealth, 15000);
