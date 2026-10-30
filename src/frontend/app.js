/**
 * NextGen Code Explorer — Frontend Client
 * Grounded code search, explainable ranking, dependency graphs, live evaluation,
 * and cinematic micro-interactions with ambient geometric particle canvas.
 */

// Global State
const state = {
  sessionId: localStorage.getItem("nextgen_session_id") || null,
  activeMode: "hybrid",
  lastSearchResults: [],
  statusPollInterval: null,
};

// Initialize application on DOM load
document.addEventListener("DOMContentLoaded", () => {
  initTheme();
  initBackgroundParticles();
  initTabs();
  initUpload();
  initSearch();
  initMermaid();
  initExplorer();
  initEvaluation();
  initModalListeners();
  checkHealth();

  if (state.sessionId) {
    pollStatus(state.sessionId);
  }
});

/* ==========================================================================
   1. Theme Management (Light / Dark)
   ========================================================================== */
function initTheme() {
  const toggleBtn = document.getElementById("theme-toggle");
  const themeIcon = document.getElementById("theme-icon");
  const hljsLight = document.getElementById("hljs-light");
  const hljsDark = document.getElementById("hljs-dark");

  const savedTheme = localStorage.getItem("nextgen_theme") || "light";
  document.documentElement.setAttribute("data-theme", savedTheme);
  updateThemeIcon(savedTheme);

  toggleBtn.addEventListener("click", () => {
    const current = document.documentElement.getAttribute("data-theme");
    const nextTheme = current === "dark" ? "light" : "dark";
    document.documentElement.setAttribute("data-theme", nextTheme);
    localStorage.setItem("nextgen_theme", nextTheme);
    updateThemeIcon(nextTheme);

    if (nextTheme === "dark") {
      hljsLight.disabled = true;
      hljsDark.disabled = false;
    } else {
      hljsLight.disabled = false;
      hljsDark.disabled = true;
    }
  });

  function updateThemeIcon(theme) {
    themeIcon.textContent = theme === "dark" ? "☀️" : "🌙";
  }
}

/* ==========================================================================
   2. Cinematic Geometric Background Canvas (Techfest Inspired)
   ========================================================================== */
function initBackgroundParticles() {
  const canvas = document.getElementById("bg-canvas");
  if (!canvas) return;

  const ctx = canvas.getContext("2d");
  if (!ctx) return;

  const prefersReduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  let width = (canvas.width = window.innerWidth);
  let height = (canvas.height = window.innerHeight);

  window.addEventListener("resize", () => {
    width = canvas.width = window.innerWidth;
    height = canvas.height = window.innerHeight;
    if (prefersReduced) drawStaticScene();
  });

  // Palette: Electric Blue, Cyan, Neon Violet, Indigo
  const colors = [
    { r: 59, g: 130, b: 246 },   // #3b82f6 Blue
    { r: 6, g: 182, b: 212 },    // #06b6d4 Cyan
    { r: 139, g: 92, b: 246 },   // #8b5cf6 Violet
    { r: 99, g: 102, b: 241 },   // #6366f1 Indigo
  ];

  const shapeTypes = ["diamond", "cube", "hexagon", "triangle", "node"];
  const particleCount = Math.min(Math.floor((width * height) / 36000), 40);
  const particles = [];

  for (let i = 0; i < particleCount; i++) {
    particles.push({
      x: Math.random() * width,
      y: Math.random() * height,
      size: 7 + Math.random() * 16,
      vx: (Math.random() - 0.5) * 0.28,
      vy: (Math.random() - 0.5) * 0.28,
      rotation: Math.random() * Math.PI * 2,
      vRot: (Math.random() - 0.5) * 0.006,
      color: colors[Math.floor(Math.random() * colors.length)],
      shape: shapeTypes[Math.floor(Math.random() * shapeTypes.length)],
      alphaBase: 0.07 + Math.random() * 0.12,
      phase: Math.random() * Math.PI * 2,
    });
  }

  function drawIsometricCube(ctx, x, y, size, r, g, b, alpha) {
    ctx.save();
    ctx.translate(x, y);
    const h = size * 0.577; // 30 deg projection ratio

    // Top face
    ctx.beginPath();
    ctx.moveTo(0, -size);
    ctx.lineTo(size * 0.866, -h * 0.5);
    ctx.lineTo(0, 0);
    ctx.lineTo(-size * 0.866, -h * 0.5);
    ctx.closePath();
    ctx.fillStyle = `rgba(${r}, ${g}, ${b}, ${alpha * 1.3})`;
    ctx.fill();
    ctx.strokeStyle = `rgba(${r}, ${g}, ${b}, ${alpha * 2})`;
    ctx.stroke();

    // Left face
    ctx.beginPath();
    ctx.moveTo(-size * 0.866, -h * 0.5);
    ctx.lineTo(0, 0);
    ctx.lineTo(0, size);
    ctx.lineTo(-size * 0.866, size * 0.5);
    ctx.closePath();
    ctx.fillStyle = `rgba(${r}, ${g}, ${b}, ${alpha * 0.8})`;
    ctx.fill();
    ctx.strokeStyle = `rgba(${r}, ${g}, ${b}, ${alpha * 1.5})`;
    ctx.stroke();

    // Right face
    ctx.beginPath();
    ctx.moveTo(0, 0);
    ctx.lineTo(size * 0.866, -h * 0.5);
    ctx.lineTo(size * 0.866, size * 0.5);
    ctx.lineTo(0, size);
    ctx.closePath();
    ctx.fillStyle = `rgba(${r}, ${g}, ${b}, ${alpha * 1.0})`;
    ctx.fill();
    ctx.strokeStyle = `rgba(${r}, ${g}, ${b}, ${alpha * 1.8})`;
    ctx.stroke();

    ctx.restore();
  }

  function drawHexagon(ctx, x, y, size, r, g, b, alpha, rot) {
    ctx.save();
    ctx.translate(x, y);
    ctx.rotate(rot);
    ctx.beginPath();
    for (let i = 0; i < 6; i++) {
      const angle = (i * Math.PI) / 3;
      const px = size * Math.cos(angle);
      const py = size * Math.sin(angle);
      if (i === 0) ctx.moveTo(px, py);
      else ctx.lineTo(px, py);
    }
    ctx.closePath();
    ctx.strokeStyle = `rgba(${r}, ${g}, ${b}, ${alpha * 1.8})`;
    ctx.lineWidth = 1.2;
    ctx.stroke();
    ctx.fillStyle = `rgba(${r}, ${g}, ${b}, ${alpha * 0.5})`;
    ctx.fill();
    ctx.restore();
  }

  function drawDiamond(ctx, x, y, size, r, g, b, alpha, rot) {
    ctx.save();
    ctx.translate(x, y);
    ctx.rotate(rot);
    ctx.beginPath();
    ctx.moveTo(0, -size);
    ctx.lineTo(size * 0.75, 0);
    ctx.lineTo(0, size);
    ctx.lineTo(-size * 0.75, 0);
    ctx.closePath();
    ctx.strokeStyle = `rgba(${r}, ${g}, ${b}, ${alpha * 1.8})`;
    ctx.lineWidth = 1.2;
    ctx.stroke();
    ctx.fillStyle = `rgba(${r}, ${g}, ${b}, ${alpha * 0.4})`;
    ctx.fill();
    ctx.restore();
  }

  function drawTriangle(ctx, x, y, size, r, g, b, alpha, rot) {
    ctx.save();
    ctx.translate(x, y);
    ctx.rotate(rot);
    ctx.beginPath();
    ctx.moveTo(0, -size);
    ctx.lineTo(size * 0.866, size * 0.5);
    ctx.lineTo(-size * 0.866, size * 0.5);
    ctx.closePath();
    ctx.strokeStyle = `rgba(${r}, ${g}, ${b}, ${alpha * 1.6})`;
    ctx.lineWidth = 1.2;
    ctx.stroke();
    ctx.fillStyle = `rgba(${r}, ${g}, ${b}, ${alpha * 0.4})`;
    ctx.fill();
    ctx.restore();
  }

  function drawNode(ctx, x, y, size, r, g, b, alpha) {
    ctx.save();
    ctx.beginPath();
    ctx.arc(x, y, size * 0.35, 0, Math.PI * 2);
    ctx.fillStyle = `rgba(${r}, ${g}, ${b}, ${alpha * 2})`;
    ctx.fill();
    ctx.strokeStyle = `rgba(${r}, ${g}, ${b}, ${alpha * 0.8})`;
    ctx.lineWidth = 1;
    ctx.stroke();
    ctx.restore();
  }

  function renderFrame(timestamp) {
    ctx.clearRect(0, 0, width, height);
    const isDark = document.documentElement.getAttribute("data-theme") === "dark";
    const themeMultiplier = isDark ? 1.35 : 0.85;

    // Draw connecting faint lines
    for (let i = 0; i < particles.length; i++) {
      for (let j = i + 1; j < particles.length; j++) {
        const dx = particles[i].x - particles[j].x;
        const dy = particles[i].y - particles[j].y;
        const dist = Math.hypot(dx, dy);
        if (dist < 125) {
          const lineAlpha = (1 - dist / 125) * 0.06 * themeMultiplier;
          ctx.beginPath();
          ctx.moveTo(particles[i].x, particles[i].y);
          ctx.lineTo(particles[j].x, particles[j].y);
          ctx.strokeStyle = `rgba(59, 130, 246, ${lineAlpha})`;
          ctx.lineWidth = 0.8;
          ctx.stroke();
        }
      }
    }

    // Draw & update particles
    particles.forEach((p) => {
      const { r, g, b } = p.color;
      const pulseAlpha = (p.alphaBase + Math.sin(timestamp * 0.0012 + p.phase) * 0.03) * themeMultiplier;

      switch (p.shape) {
        case "cube":
          drawIsometricCube(ctx, p.x, p.y, p.size * 0.75, r, g, b, pulseAlpha);
          break;
        case "hexagon":
          drawHexagon(ctx, p.x, p.y, p.size, r, g, b, pulseAlpha, p.rotation);
          break;
        case "diamond":
          drawDiamond(ctx, p.x, p.y, p.size, r, g, b, pulseAlpha, p.rotation);
          break;
        case "triangle":
          drawTriangle(ctx, p.x, p.y, p.size, r, g, b, pulseAlpha, p.rotation);
          break;
        case "node":
        default:
          drawNode(ctx, p.x, p.y, p.size, r, g, b, pulseAlpha);
          break;
      }

      if (!prefersReduced) {
        p.x += p.vx;
        p.y += p.vy;
        p.rotation += p.vRot;

        // Wrap around boundaries smoothly
        if (p.x < -30) p.x = width + 30;
        if (p.x > width + 30) p.x = -30;
        if (p.y < -30) p.y = height + 30;
        if (p.y > height + 30) p.y = -30;
      }
    });

    if (!prefersReduced && !document.hidden) {
      animId = requestAnimationFrame(renderFrame);
    }
  }

  function drawStaticScene() {
    renderFrame(0);
  }

  let animId = null;
  if (!prefersReduced) {
    animId = requestAnimationFrame(renderFrame);

    document.addEventListener("visibilitychange", () => {
      if (document.hidden) {
        if (animId) cancelAnimationFrame(animId);
      } else {
        animId = requestAnimationFrame(renderFrame);
      }
    });
  } else {
    drawStaticScene();
  }
}

/* ==========================================================================
   3. Health & System Capabilities
   ========================================================================== */
async function checkHealth() {
  try {
    const res = await fetch("/api/health");
    const data = await res.json();

    const chipAi = document.getElementById("chip-ai");
    const chipSem = document.getElementById("chip-semantic");

    if (data.ai_available) {
      chipAi.textContent = "AI Available (Featherless)";
      chipAi.className = "status-chip chip-success";
    } else {
      chipAi.textContent = "AI Offline (No API Key)";
      chipAi.className = "status-chip chip-warning";
    }

    if (data.semantic_available) {
      chipSem.textContent = "Semantic Available";
      chipSem.className = "status-chip chip-success";
    } else {
      chipSem.textContent = "Lexical Mode (BM25F)";
      chipSem.className = "status-chip chip-neutral";
    }
  } catch (err) {
    console.warn("Health check failed:", err);
  }
}

/* ==========================================================================
   4. Navigation Tabs with Smooth Transitions
   ========================================================================== */
function initTabs() {
  const tabButtons = document.querySelectorAll(".tab-btn");
  tabButtons.forEach(btn => {
    btn.addEventListener("click", () => {
      tabButtons.forEach(b => b.classList.remove("active"));
      document.querySelectorAll(".tab-content").forEach(tc => tc.classList.remove("active"));

      btn.classList.add("active");
      const targetId = btn.getAttribute("data-tab");
      const targetContent = document.getElementById(targetId);
      if (targetContent) {
        targetContent.classList.add("active");
      }

      if (targetId === "tab-graph") {
        loadDependencyGraph();
      } else if (targetId === "tab-evaluation") {
        loadEvaluationData();
      }
    });
  });
}

/* ==========================================================================
   5. Repository Ingestion & Progress
   ========================================================================== */
function initUpload() {
  const dropZone = document.getElementById("drop-zone");
  const fileInput = document.getElementById("file-input");
  const btnBrowse = document.getElementById("btn-browse-file");
  const btnSample = document.getElementById("btn-sample-repo");
  const btnToggleSkips = document.getElementById("btn-toggle-skip-details");

  dropZone.addEventListener("click", () => fileInput.click());
  btnBrowse.addEventListener("click", () => fileInput.click());

  // Drag-and-drop feedback
  dropZone.addEventListener("dragenter", (e) => {
    e.preventDefault();
    dropZone.classList.add("dragover");
  });

  dropZone.addEventListener("dragover", (e) => {
    e.preventDefault();
    dropZone.classList.add("dragover");
  });

  dropZone.addEventListener("dragleave", (e) => {
    if (!dropZone.contains(e.relatedTarget)) {
      dropZone.classList.remove("dragover");
    }
  });

  dropZone.addEventListener("drop", (e) => {
    e.preventDefault();
    dropZone.classList.remove("dragover");
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      uploadFile(e.dataTransfer.files[0]);
    }
  });

  fileInput.addEventListener("change", () => {
    if (fileInput.files && fileInput.files[0]) {
      uploadFile(fileInput.files[0]);
    }
  });

  btnSample.addEventListener("click", async () => {
    btnSample.disabled = true;
    btnSample.innerHTML = "<span>⏳</span> Loading Sample Project...";
    try {
      const res = await fetch("/api/sample", { method: "POST" });
      const data = await res.json();
      state.sessionId = data.session_id;
      localStorage.setItem("nextgen_session_id", state.sessionId);
      startPollingStatus(state.sessionId);
      showToast("Loading bundled sample project (ShopStream)...");
    } catch (err) {
      showToast("Failed to load sample project: " + err.message);
    } finally {
      btnSample.disabled = false;
      btnSample.innerHTML = "<span>🚀</span> Load Sample Project (ShopStream)";
    }
  });

  btnToggleSkips.addEventListener("click", () => {
    const details = document.getElementById("skipped-details");
    details.classList.toggle("hidden");
  });
}

async function uploadFile(file) {
  if (!file.name.endsWith(".zip")) {
    showToast("Please upload a .zip archive.");
    return;
  }

  const formData = new FormData();
  formData.append("file", file);

  showProgressSection();
  updateProgressUI({ progress_pct: 10, message: "Uploading archive to server..." });

  try {
    const res = await fetch("/api/upload", {
      method: "POST",
      body: formData,
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || "Upload failed");

    state.sessionId = data.session_id;
    localStorage.setItem("nextgen_session_id", state.sessionId);
    startPollingStatus(state.sessionId);
    showToast("ZIP archive uploaded successfully. Indexing started.");
  } catch (err) {
    showToast("Upload error: " + err.message);
    hideProgressSection();
  }
}

function showProgressSection() {
  document.getElementById("progress-container").classList.remove("hidden");
  document.getElementById("stats-container").classList.add("hidden");
}

function hideProgressSection() {
  document.getElementById("progress-container").classList.add("hidden");
}

function startPollingStatus(sessionId) {
  if (state.statusPollInterval) clearInterval(state.statusPollInterval);
  showProgressSection();
  pollStatus(sessionId);
  state.statusPollInterval = setInterval(() => pollStatus(sessionId), 1000);
}

async function pollStatus(sessionId) {
  try {
    const res = await fetch(`/api/status/${sessionId}`);
    if (!res.ok) return;
    const status = await res.json();
    updateProgressUI(status);

    if (status.status === "ready") {
      clearInterval(state.statusPollInterval);
      state.statusPollInterval = null;
      hideProgressSection();
      renderStats(status);
      document.getElementById("search-empty-state").classList.add("hidden");
      showToast("Repository indexing complete! Ready to search.");
    } else if (status.status === "error") {
      clearInterval(state.statusPollInterval);
      showToast("Indexing error: " + status.error);
    }
  } catch (err) {
    console.warn("Status poll error:", err);
  }
}

function updateProgressUI(status) {
  const container = document.getElementById("progress-container");
  const bar = document.getElementById("progress-bar-fill");
  const msg = document.getElementById("progress-status-msg");
  bar.style.width = `${status.progress_pct}%`;
  msg.textContent = status.message || "Processing...";

  // Scanning radar beam animation active when scanning or parsing
  const stage = status.status;
  if (stage === "scanning" || stage === "parsing") {
    container.classList.add("scanning-active");
  } else {
    container.classList.remove("scanning-active");
  }

  const steps = ["step-extract", "step-scan", "step-parse", "step-index", "step-ready"];

  steps.forEach(id => {
    const el = document.getElementById(id);
    if (!el) return;
    el.classList.remove("active", "done");
  });

  if (stage === "extracting") document.getElementById("step-extract").classList.add("active");
  if (stage === "scanning") {
    document.getElementById("step-extract").classList.add("done");
    document.getElementById("step-scan").classList.add("active");
  }
  if (stage === "parsing") {
    document.getElementById("step-extract").classList.add("done");
    document.getElementById("step-scan").classList.add("done");
    document.getElementById("step-parse").classList.add("active");
  }
  if (stage === "indexing") {
    document.getElementById("step-extract").classList.add("done");
    document.getElementById("step-scan").classList.add("done");
    document.getElementById("step-parse").classList.add("done");
    document.getElementById("step-index").classList.add("active");
  }
  if (stage === "ready") {
    steps.forEach(id => document.getElementById(id).classList.add("done"));
  }
}

function renderStats(status) {
  const statsBox = document.getElementById("stats-container");
  statsBox.classList.remove("hidden");

  document.getElementById("stat-files-indexed").textContent = status.files_indexed || 0;
  document.getElementById("stat-files-skipped").textContent = status.files_skipped || 0;
  document.getElementById("stat-symbols").textContent = status.symbols_count || 0;
  document.getElementById("stat-terms").textContent = status.unique_terms_count || 0;

  // Language tags
  const langContainer = document.getElementById("stat-languages");
  langContainer.innerHTML = "";
  if (status.languages) {
    for (const [lang, count] of Object.entries(status.languages)) {
      const badge = document.createElement("span");
      badge.className = "lang-badge";
      badge.textContent = `${lang} (${count})`;
      langContainer.appendChild(badge);
    }
  }

  // Skipped reasons list
  const reasonsList = document.getElementById("skipped-reasons-list");
  reasonsList.innerHTML = "";
  if (status.skip_reasons) {
    for (const [reason, count] of Object.entries(status.skip_reasons)) {
      const li = document.createElement("li");
      li.textContent = `${reason}: ${count} files`;
      reasonsList.appendChild(li);
    }
  }
}

/* ==========================================================================
   6. Search & Grounded AI Explanation
   ========================================================================== */
function initSearch() {
  const searchForm = document.getElementById("search-form");
  const searchInput = document.getElementById("search-input");
  const clearBtn = document.getElementById("search-clear-btn");
  const modeHybrid = document.getElementById("btn-mode-hybrid");
  const modeLexical = document.getElementById("btn-mode-lexical");

  // Mode toggles
  modeHybrid.addEventListener("click", () => {
    modeHybrid.classList.add("active");
    modeLexical.classList.remove("active");
    state.activeMode = "hybrid";
  });

  modeLexical.addEventListener("click", () => {
    modeLexical.classList.add("active");
    modeHybrid.classList.remove("active");
    state.activeMode = "lexical";
  });

  // Example query chips
  document.querySelectorAll(".query-chips-row .chip").forEach(chip => {
    chip.addEventListener("click", () => {
      searchInput.value = chip.textContent;
      clearBtn.classList.remove("hidden");
      executeSearch();
    });
  });

  searchInput.addEventListener("input", () => {
    clearBtn.classList.toggle("hidden", !searchInput.value);
  });

  clearBtn.addEventListener("click", () => {
    searchInput.value = "";
    clearBtn.classList.add("hidden");
    searchInput.focus();
  });

  searchForm.addEventListener("submit", (e) => {
    e.preventDefault();
    executeSearch();
  });
}

async function executeSearch() {
  const query = document.getElementById("search-input").value.trim();
  if (!query) return;

  if (!state.sessionId) {
    showToast("Please upload a repository or load the sample project first.");
    return;
  }

  const topK = parseInt(document.getElementById("select-top-k").value, 10);
  const language = document.getElementById("select-language").value || null;
  const useAiRewrite = document.getElementById("check-ai-rewrite").checked;

  const submitBtn = document.getElementById("search-submit-btn");
  submitBtn.disabled = true;
  submitBtn.textContent = "Searching...";

  // Prepare UI
  document.getElementById("search-empty-state").classList.add("hidden");
  document.getElementById("results-section").classList.remove("hidden");
  const resultsList = document.getElementById("results-list");
  resultsList.innerHTML = `<div class="empty-state"><p>Searching inverted index & ranking results...</p></div>`;

  try {
    const payload = {
      session_id: state.sessionId,
      query,
      top_k: topK,
      mode: state.activeMode,
      language,
      use_ai_query_rewrite: useAiRewrite,
    };

    const res = await fetch("/api/search", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || "Search failed");

    state.lastSearchResults = data.results || [];
    renderSearchResults(data);

    // Render Query Trace Mermaid diagram
    if (data.query_trace_mermaid) {
      renderQueryTrace(data.query_trace_mermaid);
    }

    // Trigger Grounded AI Explanation
    if (data.results && data.results.length > 0) {
      requestAiExplanation(query, data.results.slice(0, 5).map(r => r.chunk_id));
    } else {
      document.getElementById("ai-explanation-section").classList.add("hidden");
    }

  } catch (err) {
    showToast("Search error: " + err.message);
    resultsList.innerHTML = `<div class="empty-state"><p>Error executing search: ${err.message}</p></div>`;
  } finally {
    submitBtn.disabled = false;
    submitBtn.textContent = "Search";
  }
}

function renderSearchResults(data) {
  const container = document.getElementById("results-list");
  const countLabel = document.getElementById("results-count-label");
  const results = data.results || [];

  countLabel.textContent = `${results.length} verified code evidence items (${data.mode})`;

  if (results.length === 0) {
    container.innerHTML = `
      <div class="empty-state">
        <p>No matching code snippets found for <strong>"${escapeHtml(data.query)}"</strong>.</p>
        <span class="sub-label">Try fewer keywords or check your language filter.</span>
      </div>`;
    return;
  }

  container.innerHTML = "";
  results.forEach((res, idx) => {
    const card = document.createElement("article");
    card.className = "result-card";
    card.id = `evidence-${res.evidence_id}`;
    // Assign staggered index for smooth entrance
    card.style.setProperty("--index", idx);

    // Highlight query terms in code
    const highlightedCode = buildHighlightedLines(res.code, res.start_line, data.normalized_query_terms);

    // Boost badges list
    const boostsList = Object.entries(res.breakdown.boosts_applied || {})
      .map(([b, val]) => `<span class="badge-pill">+${val} ${escapeHtml(b)}</span>`)
      .join(" ");

    card.innerHTML = `
      <div class="card-top-bar">
        <div class="top-bar-left">
          <span class="evidence-id-tag">[${res.evidence_id}]</span>
          <span class="file-path">${escapeHtml(res.path)}</span>
          <span class="line-range-tag">L${res.start_line} - L${res.end_line}</span>
          <span class="lang-badge">${res.language}</span>
        </div>
        <div class="top-bar-right">
          <span class="score-badge" title="Retrieved Score">Score: ${res.score}</span>
        </div>
      </div>

      <div class="symbol-banner">
        <span class="symbol-kind">${escapeHtml(res.kind)}</span>
        <span class="symbol-name">${escapeHtml(res.symbol || "module scope")}</span>
        ${res.docstring ? `<div class="docstring-preview">&ldquo;${escapeHtml(res.docstring.slice(0, 160))}&rdquo;</div>` : ""}
      </div>

      <div class="snippet-box">
        <div class="code-with-lines">${highlightedCode}</div>
      </div>

      <div class="card-actions">
        <div class="card-actions-left">
          <button class="btn btn-secondary btn-sm btn-show-context" data-path="${escapeHtml(res.path)}" data-start="${res.start_line}" data-end="${res.end_line}">
            Show Context (&plusmn;10 lines)
          </button>
          <button class="btn btn-outline btn-sm btn-copy-loc" data-loc="${escapeHtml(res.path)}:${res.start_line}-${res.end_line}">
            Copy ${escapeHtml(res.path)}:${res.start_line}-${res.end_line}
          </button>
        </div>
        <button class="btn-link btn-toggle-why" data-target="why-${res.evidence_id}">
          Why this result? ▾
        </button>
      </div>

      <div class="why-panel hidden" id="why-${res.evidence_id}">
        <div class="why-row">
          <span class="why-label">Explanation:</span> ${escapeHtml(res.breakdown.explanation || "Direct term match.")}
        </div>
        <div class="why-row">
          <span class="why-label">Matched Query Terms:</span> 
          ${(res.breakdown.matched_terms || []).map(t => `<span class="badge-pill">${escapeHtml(t)}</span>`).join(" ")}
        </div>
        ${boostsList ? `<div class="why-row"><span class="why-label">Boosts Applied:</span> ${boostsList}</div>` : ""}
        <div class="ranks-comparison">
          <span class="rank-chip">Lexical Rank: #${res.breakdown.lexical_rank || "-"}</span>
          <span class="rank-chip">Semantic Rank: #${res.breakdown.semantic_rank || "N/A"}</span>
          ${res.breakdown.fused_rank ? `<span class="rank-chip">Fused Rank: #${res.breakdown.fused_rank}</span>` : ""}
        </div>
      </div>
    `;

    // Event listeners
    card.querySelector(".btn-toggle-why").addEventListener("click", (e) => {
      const whyBox = card.querySelector(".why-panel");
      whyBox.classList.toggle("hidden");
      e.target.textContent = whyBox.classList.contains("hidden") ? "Why this result? ▾" : "Why this result? ▴";
    });

    card.querySelector(".btn-show-context").addEventListener("click", () => {
      openFileModal(res.path, res.start_line, res.end_line);
    });

    card.querySelector(".btn-copy-loc").addEventListener("click", () => {
      copyToClipboard(`${res.path}:${res.start_line}-${res.end_line}`);
      showToast(`Copied ${res.path}:${res.start_line}-${res.end_line} to clipboard!`);
    });

    container.appendChild(card);
  });
}

function buildHighlightedLines(code, startLine, queryTerms) {
  const lines = code.split("\n");
  const lowerTerms = (queryTerms || []).map(t => t.toLowerCase());

  return lines.map((lineText, idx) => {
    const lineNo = startLine + idx;
    let safeLine = escapeHtml(lineText);

    // Highlight query terms safely
    lowerTerms.forEach(term => {
      if (term.length > 2) {
        const regex = new RegExp(`(${term})`, "gi");
        safeLine = safeLine.replace(regex, `<span class="highlight-term">$1</span>`);
      }
    });

    return `
      <div class="code-line">
        <span class="line-no">${lineNo}</span>
        <span class="line-code">${safeLine}</span>
      </div>`;
  }).join("");
}

/* ==========================================================================
   7. AI Grounded Explanation Request & Citations
   ========================================================================== */
async function requestAiExplanation(query, resultIds) {
  const aiSection = document.getElementById("ai-explanation-section");
  const aiText = document.getElementById("ai-explanation-text");
  const aiCitations = document.getElementById("ai-citations-list");
  const aiSpinner = document.getElementById("ai-spinner");

  aiSection.classList.remove("hidden");
  aiSpinner.classList.remove("hidden");
  aiText.textContent = "Synthesizing strictly grounded explanation from retrieved code snippets...";
  aiCitations.innerHTML = "";

  try {
    const res = await fetch("/api/explain", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        session_id: state.sessionId,
        query,
        result_ids: resultIds,
      }),
    });

    const data = await res.json();
    aiSpinner.classList.add("hidden");

    if (data.explanation) {
      aiText.innerHTML = renderCitationsInText(data.explanation);

      // Render citation pill buttons
      if (data.valid_citations && data.valid_citations.length > 0) {
        data.valid_citations.forEach(c => {
          const pill = document.createElement("button");
          pill.className = "citation-pill";
          pill.textContent = `[${c.evidence_id}] ${c.path}:${c.start_line}-${c.end_line}`;
          pill.addEventListener("click", () => scrollToEvidence(c.evidence_id));
          aiCitations.appendChild(pill);
        });
      }
    } else {
      aiText.textContent = "AI explanation unavailable. Refer directly to the verified source evidence cards.";
    }

  } catch (err) {
    aiSpinner.classList.add("hidden");
    aiText.textContent = "AI explanation request failed: " + err.message;
  }
}

function renderCitationsInText(text) {
  // Convert [E1], [E2] into clickable links
  return escapeHtml(text).replace(/\[(E\d+)\]/g, (match, p1) => {
    return `<a href="#evidence-${p1}" class="citation-pill" onclick="scrollToEvidence('${p1}'); return false;">[${p1}]</a>`;
  });
}

function scrollToEvidence(evidenceId) {
  const target = document.getElementById(`evidence-${evidenceId}`);
  if (target) {
    target.scrollIntoView({ behavior: "smooth", block: "center" });
    target.classList.add("highlighted");
    setTimeout(() => target.classList.remove("highlighted"), 2500);
  }
}

/* ==========================================================================
   8. Mermaid Diagram Renderers (Query Trace & Dependency Graph)
   ========================================================================== */
function initMermaid() {
  if (window.mermaid) {
    mermaid.initialize({
      startOnLoad: false,
      theme: document.documentElement.getAttribute("data-theme") === "dark" ? "dark" : "default",
      flowchart: { useMaxWidth: true, htmlLabels: true, curve: "basis" },
    });
  }

  // Toggle Query Trace collapsible
  const traceToggle = document.getElementById("trace-toggle-header");
  if (traceToggle) {
    traceToggle.addEventListener("click", () => {
      const body = document.getElementById("trace-body");
      const icon = document.getElementById("trace-toggle-icon");
      body.classList.toggle("hidden");
      icon.textContent = body.classList.contains("hidden") ? "▸" : "▾";
    });
  }

  // Refresh graph button
  const btnRefreshGraph = document.getElementById("btn-refresh-graph");
  if (btnRefreshGraph) {
    btnRefreshGraph.addEventListener("click", () => loadDependencyGraph());
  }

  const btnResetFocus = document.getElementById("btn-reset-graph-focus");
  if (btnResetFocus) {
    btnResetFocus.addEventListener("click", () => {
      btnResetFocus.classList.add("hidden");
      loadDependencyGraph(null);
    });
  }
}

async function renderQueryTrace(mermaidMarkup) {
  const container = document.getElementById("query-trace-mermaid");
  document.getElementById("query-trace-section").classList.remove("hidden");
  try {
    const id = "trace-" + Date.now();
    const { svg } = await mermaid.render(id, mermaidMarkup);
    container.innerHTML = svg;
  } catch (err) {
    container.innerHTML = `<p class="sub-label">Trace diagram rendering notice: ${err.message}</p>`;
  }
}

async function loadDependencyGraph(focusFile = null) {
  if (!state.sessionId) return;
  const container = document.getElementById("dependency-mermaid");
  container.innerHTML = `<div class="empty-state"><p>Generating dependency graph...</p></div>`;

  try {
    const highlights = state.lastSearchResults.map(r => r.path).join(",");
    let url = `/api/graph/${state.sessionId}?highlights=${encodeURIComponent(highlights)}`;
    if (focusFile) url += `&focus=${encodeURIComponent(focusFile)}`;

    const res = await fetch(url);
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || "Graph loading failed");

    const id = "depgraph-" + Date.now();
    const { svg } = await mermaid.render(id, data.mermaid);
    container.innerHTML = svg;

    if (focusFile) {
      document.getElementById("btn-reset-graph-focus").classList.remove("hidden");
    }

  } catch (err) {
    container.innerHTML = `<div class="empty-state"><p>Dependency graph rendering: ${escapeHtml(err.message)}</p></div>`;
  }
}

/* ==========================================================================
   9. Inverted Index Explorer
   ========================================================================== */
function initExplorer() {
  const btnInspect = document.getElementById("btn-inspect-term");
  const inputTerm = document.getElementById("index-term-input");

  btnInspect.addEventListener("click", () => inspectTerm());
  inputTerm.addEventListener("keypress", (e) => {
    if (e.key === "Enter") inspectTerm();
  });
}

async function inspectTerm() {
  const term = document.getElementById("index-term-input").value.trim();
  if (!term) return;

  if (!state.sessionId) {
    showToast("Please index a repository first.");
    return;
  }

  try {
    const res = await fetch(`/api/index/${state.sessionId}/terms?q=${encodeURIComponent(term)}`);
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || "Term lookup failed");

    document.getElementById("index-term-details").classList.remove("hidden");
    document.getElementById("metric-term").textContent = data.term;
    document.getElementById("metric-df").textContent = `${data.document_frequency} chunks`;

    const tableBody = document.getElementById("postings-table-body");
    tableBody.innerHTML = "";

    if (!data.top_chunks || data.top_chunks.length === 0) {
      tableBody.innerHTML = `<tr><td colspan="5" class="text-center">No chunks contain this term.</td></tr>`;
      return;
    }

    data.top_chunks.forEach(c => {
      const row = document.createElement("tr");
      row.innerHTML = `
        <td><code>${escapeHtml(c.chunk_id)}</code></td>
        <td>${escapeHtml(c.path)}</td>
        <td><strong>${escapeHtml(c.symbol || "-")}</strong></td>
        <td><span class="badge-pill">${c.term_frequency}x</span></td>
        <td>${c.fields.map(f => `<span class="badge-pill">${f}</span>`).join(" ")}</td>
      `;
      tableBody.appendChild(row);
    });

  } catch (err) {
    showToast("Error inspecting term: " + err.message);
  }
}

/* ==========================================================================
   10. Evaluation Benchmark
   ========================================================================== */
function initEvaluation() {
  const btnRun = document.getElementById("btn-run-eval");
  btnRun.addEventListener("click", () => runEvaluationSuite());
}

async function loadEvaluationData() {
  try {
    const res = await fetch("/docs/eval_results.json");
    if (res.ok) {
      const data = await res.json();
      renderEvaluationResults(data);
    } else {
      runEvaluationSuite();
    }
  } catch {
    runEvaluationSuite();
  }
}

async function runEvaluationSuite() {
  const btn = document.getElementById("btn-run-eval");
  btn.disabled = true;
  btn.textContent = "Running Benchmark...";

  try {
    const targetSession = state.sessionId || "sample_repo";
    const res = await fetch(`/api/eval/run?session_id=${encodeURIComponent(targetSession)}`, {
      method: "POST",
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || "Evaluation failed");

    renderEvaluationResults(data);
    showToast("Benchmark evaluation completed!");
  } catch (err) {
    showToast("Evaluation error: " + err.message);
  } finally {
    btn.disabled = false;
    btn.textContent = "Re-run Evaluation";
  }
}

function renderEvaluationResults(data) {
  const summaryContainer = document.getElementById("eval-metrics-summary");
  const tableBody = document.getElementById("eval-table-body");

  summaryContainer.innerHTML = "";
  tableBody.innerHTML = "";

  const modes = data.modes || {};
  for (const [mode, metrics] of Object.entries(modes)) {
    const card = document.createElement("div");
    card.className = "stat-card";
    card.innerHTML = `
      <span class="stat-label">[${mode.toUpperCase()}] Retrieval Accuracy</span>
      <div style="margin-top: 0.5rem; font-size: 0.9rem;">
        <div><strong>Hit@1:</strong> ${metrics.hit_at_1_pct}</div>
        <div><strong>Hit@3:</strong> ${metrics.hit_at_3_pct}</div>
        <div><strong>MRR:</strong> ${metrics.mrr}</div>
      </div>
    `;
    summaryContainer.appendChild(card);
  }

  const primaryMode = modes["hybrid"] || modes["lexical"];
  if (!primaryMode || !primaryMode.questions) return;

  primaryMode.questions.forEach((q, idx) => {
    const row = document.createElement("tr");
    const h1Class = q.hit_1 > 0 ? "badge-pass" : "badge-fail";
    const h3Class = q.hit_3 > 0 ? "badge-pass" : "badge-fail";
    const rankStr = q.first_hit_rank ? `#${q.first_hit_rank}` : "-";

    row.innerHTML = `
      <td>${idx + 1}</td>
      <td><strong>${escapeHtml(q.question)}</strong></td>
      <td><span class="${h1Class}">${q.hit_1 > 0 ? "PASS" : "FAIL"}</span></td>
      <td><span class="${h3Class}">${q.hit_3 > 0 ? "PASS" : "FAIL"}</span></td>
      <td><code>${rankStr}</code></td>
      <td><code>${escapeHtml(q.top_result_symbol || q.top_result_path || "-")}</code></td>
      <td>${(q.expected_files || []).map(f => `<span class="badge-pill">${f}</span>`).join(" ")}</td>
    `;
    tableBody.appendChild(row);
  });
}

/* ==========================================================================
   11. Modal Interactions with Smooth Animated Entrance & Exit (Requirement 2)
   ========================================================================== */
function initModalListeners() {
  const modalCloseBtn = document.getElementById("modal-close-btn");
  const modalBackdrop = document.getElementById("modal-backdrop");

  if (modalCloseBtn) {
    modalCloseBtn.addEventListener("click", closeModal);
  }
  if (modalBackdrop) {
    modalBackdrop.addEventListener("click", closeModal);
  }

  // Smooth close on Escape key
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") {
      closeModal();
    }
  });
}

function closeModal() {
  const modal = document.getElementById("context-modal");
  if (!modal || modal.classList.contains("hidden")) return;

  modal.classList.add("modal-closing");
  setTimeout(() => {
    modal.classList.add("hidden");
    modal.classList.remove("modal-closing");
  }, 220);
}

async function openFileModal(path, startLine, endLine) {
  const modal = document.getElementById("context-modal");
  const pathLabel = document.getElementById("modal-file-path");
  const rangeLabel = document.getElementById("modal-line-range");
  const codeContent = document.getElementById("modal-code-content");

  pathLabel.textContent = path;
  rangeLabel.textContent = `Lines ${Math.max(1, startLine - 10)} - ${endLine + 10}`;
  codeContent.textContent = "Loading file context...";
  modal.classList.remove("hidden", "modal-closing");

  try {
    const res = await fetch(
      `/api/file?session_id=${encodeURIComponent(state.sessionId)}&path=${encodeURIComponent(path)}&start=${startLine}&end=${endLine}&context=10`
    );
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || "Failed to load file context");

    codeContent.textContent = data.code;
    hljs.highlightElement(codeContent);
  } catch (err) {
    codeContent.textContent = "Failed to load source context: " + err.message;
  }
}

/* ==========================================================================
   12. Utilities & Toast Notifications
   ========================================================================== */
function copyToClipboard(text) {
  if (navigator.clipboard) {
    navigator.clipboard.writeText(text);
  } else {
    const textarea = document.createElement("textarea");
    textarea.value = text;
    document.body.appendChild(textarea);
    textarea.select();
    document.execCommand("copy");
    document.body.removeChild(textarea);
  }
}

function showToast(message) {
  const container = document.getElementById("toast-container");
  const toast = document.createElement("div");
  toast.className = "toast";
  toast.textContent = message;
  container.appendChild(toast);
  setTimeout(() => {
    toast.style.opacity = "0";
    toast.style.transform = "translateY(12px)";
    toast.style.transition = "opacity 0.25s, transform 0.25s";
    setTimeout(() => toast.remove(), 250);
  }, 3200);
}

function escapeHtml(str) {
  if (!str) return "";
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}
