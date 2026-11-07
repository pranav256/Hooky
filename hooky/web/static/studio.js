// Security & Auth Token Integration

const _injectedToken =
  !window.__HOOKY_TOKEN__.includes("PLACEHOLDER") &&
  window.__HOOKY_TOKEN__.length > 10
    ? window.__HOOKY_TOKEN__
    : null;
const _urlParams = new URLSearchParams(window.location.search);
const _queryToken = _urlParams.get("token");

if (_injectedToken) {
  window.__HOOKY_TOKEN__ = _injectedToken;
  try {
    sessionStorage.setItem("hooky_token", _injectedToken);
  } catch (e) {}
  if (_queryToken) {
    const cleanUrl = window.location.pathname + (window.location.hash || "");
    try {
      window.history.replaceState({}, document.title, cleanUrl);
    } catch (e) {}
  }
} else if (_queryToken) {
  window.__HOOKY_TOKEN__ = _queryToken;
  try {
    sessionStorage.setItem("hooky_token", _queryToken);
  } catch (e) {}
} else {
  try {
    const _saved = sessionStorage.getItem("hooky_token");
    if (_saved) {
      window.__HOOKY_TOKEN__ = _saved;
    }
  } catch (e) {}
}

// Intercept fetch to automatically include X-Hooky-Token header on all API calls
const _nativeFetch = window.fetch;
window.fetch = function (input, init) {
  init = init || {};
  init.credentials = init.credentials || "same-origin";
  init.headers = init.headers || {};
  const token = window.__HOOKY_TOKEN__;
  const target = new URL(
    typeof input === "string" ? input : input.url || input,
    window.location.href,
  );
  if (
    target.origin === window.location.origin &&
    target.pathname.startsWith("/api/") &&
    token &&
    !token.includes("PLACEHOLDER")
  ) {
    if (init.headers instanceof Headers) {
      init.headers.set("X-Hooky-Token", token);
    } else if (Array.isArray(init.headers)) {
      init.headers.push(["X-Hooky-Token", token]);
    } else {
      init.headers["X-Hooky-Token"] = token;
    }
  }
  return _nativeFetch(input, init);
};

// State management (starts clean with no preloaded video or fake hooks)
let CURRENT_HOOKS = [];
let currentSourceVideoTitle = "";
let selectedHookId = null;
let activeFramingMode = "auto";
let activeSubtitleMode = "auto";
let autoDetectedFraming = "fit";
let autoDetectedStyle = "gold";
let currentPreviewMode = "player";
let cachedChannels = [];
let cachedEnvConfig = { raw: "", values: {} };
let isPlaying = false;
let wordIdx = 0;
let SCRIPT_WORDS = [];

document.addEventListener("DOMContentLoaded", () => {
  lucide.createIcons();
  document.querySelectorAll("label").forEach((label) => {
    const input = label.parentElement.querySelector("input,select,textarea");
    if (input?.id) label.htmlFor = input.id;
  });
  document.getElementById("source-url").addEventListener("keydown", (event) => {
    if (event.key === "Enter") triggerAnalyze();
  });
  document
    .getElementById("new-channel-input")
    .addEventListener("keydown", (event) => {
      if (event.key === "Enter") addNewChannel();
    });
  document.querySelectorAll("button").forEach((button) => {
    if (!button.textContent.trim() && !button.getAttribute("aria-label"))
      button.setAttribute(
        "aria-label",
        button
          .querySelector("[data-lucide]")
          ?.getAttribute("data-lucide")
          ?.replaceAll("-", " ") || "Studio action",
      );
  });
  switchPreviewMode("player");
  renderHooksList();
  updateSelectedHookDetails();
  loadDoctorReport();
  loadChannels();
  loadOutputs();
  loadEnvConfig();

  setInterval(() => {
    if (
      !isPlaying ||
      currentPreviewMode !== "canvas" ||
      CURRENT_HOOKS.length === 0
    )
      return;
    wordIdx = wordIdx + 1;
    renderSubtitles();
  }, 380);
});

function switchTab(tabId) {
  const names = {
    studio: "Clip studio",
    radar: "Channel radar",
    gallery: "Your clips",
    settings: "Settings",
    doctor: "System health",
  };
  document.getElementById("workspace-label").textContent =
    names[tabId] || "Clip studio";
  ["studio", "radar", "gallery", "settings", "doctor"].forEach((t) => {
    document
      .getElementById(`view-${t}`)
      .classList.toggle("hidden", t !== tabId);
    const btn = document.getElementById(`tab-${t}`);
    if (btn) {
      if (t === tabId) btn.setAttribute("aria-current", "page");
      else btn.removeAttribute("aria-current");
      btn.className = "tab-btn";
    }
  });
  lucide.createIcons();
}

function setFramingMode(mode) {
  activeFramingMode = mode;
  ["auto", "fit", "center"].forEach((m) => {
    const btn = document.getElementById(`frame-mode-${m}`);
    btn.setAttribute("aria-pressed", String(m === mode));
    if (m === mode) {
      btn.className =
        "px-2.5 py-0.5 bg-[#242721] text-white font-medium rounded transition-all";
    } else {
      btn.className =
        "px-2.5 py-0.5 text-slate-400 hover:text-white rounded transition-all";
    }
  });
  applyVisualFramingState();
}

function setSubtitleMode(style) {
  activeSubtitleMode = style;
  ["auto", "gold", "hormozi", "clean", "minimal", "emerald", "crimson"].forEach(
    (s) => {
      const btn = document.getElementById(`sub-mode-${s}`);
      if (btn) {
        btn.setAttribute("aria-pressed", String(s === style));
        if (s === style) {
          btn.className =
            "px-2.5 py-0.5 bg-[#242721] text-white font-medium rounded transition-all";
        } else {
          btn.className =
            "px-2.5 py-0.5 text-slate-400 hover:text-white rounded transition-all";
        }
      }
    },
  );
  renderSubtitles();
}

function applyVisualFramingState() {
  const effectiveMode =
    activeFramingMode === "auto" ? autoDetectedFraming : activeFramingMode;
  const cropBox = document.getElementById("crop-box");
  const backdrop = document.getElementById("ambient-blur-backdrop");
  const tag = document.getElementById("preview-mode-tag");

  if (effectiveMode === "fit") {
    cropBox.style.width = "40%";
    cropBox.style.left = "30%";
    backdrop.style.opacity = "0.35";
    tag.innerText = "Canvas fit (ambient blur)";
    document.getElementById("avatar-host").style.opacity = "0.7";
    document.getElementById("avatar-speaker2").style.opacity = "0.7";
  } else {
    cropBox.style.width = "46%";
    cropBox.style.left = "27%";
    backdrop.style.opacity = "0.08";
    tag.innerText = "Center crop (solo speaker)";
    document.getElementById("avatar-host").style.opacity = "0.2";
    document.getElementById("avatar-speaker2").style.opacity = "0.2";
  }
}

function switchPreviewMode(mode) {
  currentPreviewMode = mode;
  const isPlayer = mode === "player";
  document
    .getElementById("preview-player-container")
    .classList.toggle("hidden", !isPlayer);
  document
    .getElementById("preview-canvas-container")
    .classList.toggle("hidden", isPlayer);

  const tabPlayer = document.getElementById("preview-tab-player");
  const tabCanvas = document.getElementById("preview-tab-canvas");

  if (isPlayer) {
    tabPlayer.className =
      "px-3 py-1 bg-[#242721] text-white font-medium rounded border border-white/10 transition-all";
    tabCanvas.className =
      "px-3 py-1 text-slate-400 hover:text-white rounded transition-all";
  } else {
    tabCanvas.className =
      "px-3 py-1 bg-[#242721] text-white font-medium rounded border border-white/10 transition-all";
    tabPlayer.className =
      "px-3 py-1 text-slate-400 hover:text-white rounded transition-all";
  }
}

function extractYouTubeId(url) {
  if (!url) return null;
  const m = url.match(
    /(?:youtu\.be\/|youtube\.com\/(?:watch\?v=|embed\/|v\/|shorts\/))([\w-]{11})/i,
  );
  return m ? m[1] : null;
}

function selectHook(hookId) {
  selectedHookId = hookId;
  renderHooksList();
  updateSelectedHookDetails();
}

function updateSelectedHookDetails() {
  const hook =
    CURRENT_HOOKS.find((h) => h.id === selectedHookId) ||
    (CURRENT_HOOKS.length > 0 ? CURRENT_HOOKS[0] : null);
  const iframe = document.getElementById("youtube-embed-frame");
  const placeholder = document.getElementById("player-placeholder");
  const timeBadge = document.getElementById("transcript-time-badge");
  const dialogueBox = document.getElementById("dialogue-lines-box");
  const previewElem = document.getElementById("canvas-subtitle-preview");

  if (!hook) {
    if (iframe) {
      iframe.src = "";
      iframe.classList.add("hidden");
    }
    if (placeholder) placeholder.classList.remove("hidden");
    if (timeBadge) timeBadge.innerText = "--:-- - --:--";
    if (dialogueBox)
      dialogueBox.innerHTML =
        '<p class="text-slate-500 text-xs italic">Select or detect a hook to view transcript cues.</p>';
    if (previewElem)
      previewElem.innerHTML =
        '<span class="text-slate-500">Subtitle preview will appear here</span>';
    return;
  }

  if (iframe && hook.youtube_embed_url) {
    iframe.src = hook.youtube_embed_url;
    iframe.classList.remove("hidden");
    if (placeholder) placeholder.classList.add("hidden");
  }
  if (timeBadge) {
    timeBadge.innerText = `${hook.start_fmt} - ${hook.end_fmt} (${hook.duration})`;
  }
  if (dialogueBox && hook.dialogue) {
    dialogueBox.innerHTML = hook.dialogue
      .map(
        (d) => `
          <div class="flex items-start gap-2 hover:bg-white/[0.04] p-1 rounded transition-colors">
            <span class="text-[#d2fa69] select-none text-[10px] w-10 shrink-0 font-medium tabular">${escapeHtml(d.time)}</span>
            <span class="leading-relaxed text-slate-200">${escapeHtml(d.text)}</span>
          </div>
        `,
      )
      .join("");
  }

  renderSubtitles();
}

function renderSubtitles() {
  const hook =
    CURRENT_HOOKS.find((h) => h.id === selectedHookId) ||
    (CURRENT_HOOKS.length > 0 ? CURRENT_HOOKS[0] : null);
  const previewElem = document.getElementById("canvas-subtitle-preview");
  if (!previewElem) return;
  if (!hook) {
    previewElem.innerHTML =
      '<span class="text-slate-500">Subtitle preview will appear here</span>';
    return;
  }

  const style =
    activeSubtitleMode === "auto" ? autoDetectedStyle : activeSubtitleMode;
  const words =
    hook.words && hook.words.length > 0
      ? hook.words
      : hook.title
        ? hook.title.toUpperCase().split(/\s+/)
        : ["HOOKY", "CLIP"];
  const rawWord = words[wordIdx % words.length];
  const activeWord = escapeHtml(
    typeof rawWord === "object" ? rawWord.word || rawWord.text || "" : rawWord,
  );

  let styledHTML = "";
  if (style === "gold") {
    styledHTML = `<span class="text-white">${escapeHtml(hook.title || "")}</span> <span class="text-[#ffd166] font-medium text-sm">${activeWord}</span>`;
  } else if (style === "hormozi") {
    styledHTML = `<span class="bg-[#ffff00] text-black px-1.5 py-0.5 font-bold uppercase text-sm">${activeWord}</span>`;
  } else if (style === "emerald") {
    styledHTML = `<span class="text-white">${escapeHtml(hook.title || "")}</span> <span class="text-[#d2fa69] font-medium underline decoration-1">${activeWord}</span>`;
  } else if (style === "crimson") {
    styledHTML = `<span class="text-[#ef4444] font-medium text-sm">${activeWord}</span>`;
  } else if (style === "minimal") {
    styledHTML = `<span class="text-slate-100 border-b border-white">${activeWord}</span>`;
  } else {
    styledHTML = `<span class="text-white bg-black/80 px-2 py-0.5 border border-white/20">${activeWord}</span>`;
  }
  previewElem.innerHTML = styledHTML;
}

function renderHooksList() {
  document.getElementById("top-render-btn").disabled =
    CURRENT_HOOKS.length === 0;
  const container = document.getElementById("hooks-container");
  if (!container) return;

  document.getElementById("hook-count").innerText =
    `${CURRENT_HOOKS.length} hooks detected`;

  if (CURRENT_HOOKS.length === 0) {
    container.innerHTML = `
          <div class="studio-empty p-8 border border-white/[0.08] bg-[#191b18] rounded-lg text-center space-y-3">
            <i data-lucide="video" class="w-8 h-8 text-slate-500 mx-auto"></i>
            <div>
              <p class="text-sm font-medium text-slate-300">The next good moment starts here.</p>
              <p class="text-xs text-slate-500 mt-1 font-mono">Paste a video link and choose “Detect hooks”. Your AI-selected moments will appear here.</p>
            </div>
          </div>
        `;
    lucide.createIcons();
    return;
  }

  container.innerHTML = CURRENT_HOOKS.map((h, idx) => {
    const isSelected = h.id === selectedHookId;
    const borderClass = isSelected
      ? "border-[#d2fa69] bg-[#242721]"
      : "border-white/[0.08] bg-[#191b18] hover:border-white/20";

    return `
          <div
            class="hook-card p-4 border ${borderClass} rounded-lg transition-all cursor-pointer space-y-2.5 group"
          >
            <div class="flex items-center justify-between">
              <div class="flex items-center gap-2">
                <span class="w-5 h-5 grid place-items-center bg-[#101110] text-slate-400 font-mono text-[10px] rounded border border-white/10">0${idx + 1}</span>
                <span class="text-[11px] font-mono px-2 py-0.5 bg-white/5 text-slate-300 border border-white/10 rounded">
                  ${escapeHtml(h.category || "AI-selected")}
                </span>
              </div>
              <div class="flex items-center gap-1 font-mono text-xs tabular">
                <span class="text-[#d2fa69] font-medium">${h.retention_score}%</span>
                <span class="text-slate-500 text-[10px]">AI score</span>
              </div>
            </div>

            <div>
              <h4 class="font-medium text-sm text-white group-hover:text-white transition-colors leading-snug">
                <button type="button" class="hook-select" data-hook-id="${escapeHtml(h.id)}" onclick="selectHook(this.dataset.hookId)" aria-pressed="${isSelected}">${escapeHtml(h.title)}</button>
              </h4>
              <p class="text-xs text-slate-400 mt-1 line-clamp-2 font-mono leading-relaxed">
                "${escapeHtml(h.hook_quote)}"
              </p>
            </div>

            <div class="flex items-center justify-between pt-2 border-t border-white/[0.06] text-[11px] font-mono">
              <span class="text-slate-400 tabular">
                ${h.start_fmt} - ${h.end_fmt} (${h.duration})
              </span>
              <button
                data-hook-id="${escapeHtml(h.id)}" onclick="event.stopPropagation(); renderSingleHookById(this.dataset.hookId)"
                class="px-2.5 py-1 bg-[#242721] hover:bg-white hover:text-black border border-white/10 text-white rounded transition-all"
              >
                Export reel →
              </button>
            </div>
          </div>
        `;
  }).join("");
  lucide.createIcons();
}

function nudgeTime(type, delta) {
  const hook = CURRENT_HOOKS.find((h) => h.id === selectedHookId);
  if (!hook) return;

  if (type === "start") {
    hook.start = Math.min(hook.end - 5, Math.max(0, hook.start + delta));
    hook.start_fmt = formatSecondsToMMSS(hook.start);
  } else {
    hook.end = Math.max(hook.start + 5, hook.end + delta);
    hook.end_fmt = formatSecondsToMMSS(hook.end);
  }
  hook.duration = `${(hook.end - hook.start).toFixed(1)}s`;
  const vidId = extractYouTubeId(
    document.getElementById("source-url").value.trim(),
  );
  if (vidId) {
    hook.youtube_embed_url = `https://www.youtube-nocookie.com/embed/${vidId}?start=${Math.floor(hook.start)}&end=${Math.floor(hook.end)}&autoplay=1&enablejsapi=1`;
  }

  updateSelectedHookDetails();
  renderHooksList();
  appendConsoleLog(
    `[nudge] Adjusted ${type} boundary by ${delta > 0 ? "+" : ""}${delta}s -> [${hook.start_fmt} - ${hook.end_fmt}]`,
  );
}

function formatSecondsToMMSS(sec) {
  const m = Math.floor(sec / 60);
  const s = Math.floor(sec % 60);
  return `${m}:${s < 10 ? "0" : ""}${s}`;
}

function escapeHtml(value) {
  return String(value ?? "").replace(
    /[&<>"']/g,
    (char) =>
      ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[
        char
      ],
  );
}
function appendConsoleLog(msg) {
  if (/\[[^\]]*error\]/i.test(msg)) {
    const alert = document.getElementById("studio-alert");
    alert.textContent = String(msg).replace(/^\[[^\]]*error\]\s*/i, "");
    alert.classList.remove("hidden");
  }
  const box = document.getElementById("live-engine-console");
  if (!box) return;
  const line = document.createElement("p");
  line.innerText = msg;
  box.appendChild(line);
  box.scrollTop = box.scrollHeight;
}

function toggleTerminalLogs() {
  const consoleBox = document.getElementById("live-engine-console");
  const label = document.getElementById("terminal-toggle-label");
  consoleBox.classList.toggle("hidden");
  label.innerText = consoleBox.classList.contains("hidden")
    ? "Show console logs"
    : "Hide console logs";
}

// ==================== ENGINE API CALLS ====================

async function triggerAnalyze() {
  const urlInput = document.getElementById("source-url");
  const url = urlInput.value.trim();
  if (!url) {
    appendConsoleLog("[error] Please paste a YouTube or video URL first.");
    return;
  }

  document.getElementById("studio-alert").classList.add("hidden");
  const analyzeBtn = document.getElementById("analyze-btn");
  analyzeBtn.disabled = true;
  analyzeBtn.innerHTML = `<i data-lucide="loader" class="w-4 h-4 animate-spin"></i><span>Analyzing...</span>`;
  lucide.createIcons();

  const stepper = document.getElementById("pipeline-stepper");
  stepper.classList.remove("hidden");

  try {
    appendConsoleLog(`[pipeline] Dispatching hook analysis request for ${url}`);
    const startRes = await fetch("/api/analyze/start", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ url }),
    });

    if (!startRes.ok) {
      const errData = await startRes
        .json()
        .catch(() => ({ detail: `HTTP ${startRes.status}` }));
      throw new Error(
        errData.detail || `Server returned HTTP ${startRes.status}`,
      );
    }

    const startData = await startRes.json();
    const job_id = startData.job_id;
    if (!job_id) {
      throw new Error("Server did not return a valid job ID");
    }
    document.getElementById("active-task-id").innerText = job_id;

    const pollInterval = setInterval(async () => {
      try {
        const sRes = await fetch(`/api/analyze/status/${job_id}`);
        if (!sRes.ok) {
          const err = await sRes
            .json()
            .catch(() => ({ detail: `HTTP ${sRes.status}` }));
          throw new Error(err.detail || `Polling failed (HTTP ${sRes.status})`);
        }
        const job = await sRes.json();
        if (!job || job.detail) {
          throw new Error(job?.detail || "Invalid job response");
        }

        document.getElementById("stepper-status-text").innerText =
          job.step || "Running AI hook detection...";
        document.getElementById("stepper-percent").innerText =
          `${job.progress || 10}%`;
        document.getElementById("stepper-progress-fill").style.width =
          `${job.progress || 10}%`;

        if (job.logs && job.logs.length > 0) {
          job.logs.forEach((l) => appendConsoleLog(l));
        }

        if (job.status === "completed" || job.status === "failed") {
          clearInterval(pollInterval);
          analyzeBtn.disabled = false;
          analyzeBtn.innerHTML = `<i data-lucide="sparkles" class="w-4 h-4"></i><span>Detect hooks</span>`;
          lucide.createIcons();

          if (job.status === "failed") {
            appendConsoleLog(
              `[pipeline error] Hook detection failed: ${job.error || "Unknown error"}`,
            );
            return;
          }

          if (job.result && job.result.hooks && job.result.hooks.length > 0) {
            CURRENT_HOOKS = job.result.hooks;
            currentSourceVideoTitle = job.result.video_title || "";
            selectedHookId = CURRENT_HOOKS[0].id;
            isPlaying = true;
            autoDetectedFraming = job.result.recommended_framing || "fit";
            autoDetectedStyle = job.result.recommended_style || "gold";

            document.getElementById("smart-recommendation-text").innerText =
              `Auto-tuned: ${autoDetectedFraming === "fit" ? "Canvas fit" : "Center crop"} + ${autoDetectedStyle}`;

            setFramingMode(autoDetectedFraming);
            setSubtitleMode(autoDetectedStyle);
            renderHooksList();
            updateSelectedHookDetails();
            appendConsoleLog(
              `[pipeline] Hook analysis completed successfully. ${CURRENT_HOOKS.length} moments ready.`,
            );
          } else {
            appendConsoleLog(`[pipeline] No hooks found in video transcript.`);
          }
        }
      } catch (pollErr) {
        clearInterval(pollInterval);
        appendConsoleLog(`[pipeline error] ${pollErr.message}`);
        analyzeBtn.disabled = false;
        analyzeBtn.innerHTML = `<i data-lucide="sparkles" class="w-4 h-4"></i><span>Detect hooks</span>`;
        lucide.createIcons();
      }
    }, 1000);
  } catch (e) {
    console.error(e);
    appendConsoleLog(`[analyzer error] ${e.message}`);
    analyzeBtn.disabled = false;
    analyzeBtn.innerHTML = `<i data-lucide="sparkles" class="w-4 h-4"></i><span>Detect hooks</span>`;
    lucide.createIcons();
  }
}

async function renderSelectedHook() {
  if (!CURRENT_HOOKS || CURRENT_HOOKS.length === 0) {
    appendConsoleLog(
      "[error] No hooks available. Please enter a video URL and detect hooks first.",
    );
    return;
  }
  const hook =
    CURRENT_HOOKS.find((h) => h.id === selectedHookId) || CURRENT_HOOKS[0];
  if (!hook) {
    appendConsoleLog("[error] Please select a hook to export.");
    return;
  }
  await renderSingleHookById(hook.id);
}

async function renderSingleHookById(hookId) {
  const hook = CURRENT_HOOKS.find((h) => h.id === hookId);
  if (!hook) {
    appendConsoleLog("[error] Selected hook was not found.");
    return;
  }

  const urlVal = document.getElementById("source-url").value.trim();
  if (!urlVal) {
    appendConsoleLog("[error] Missing source video URL.");
    return;
  }

  const btn = document.getElementById("top-render-btn");
  btn.disabled = true;
  btn.innerHTML = `<i data-lucide="loader" class="w-4 h-4 animate-spin"></i><span>Exporting...</span>`;
  lucide.createIcons();

  const stepper = document.getElementById("pipeline-stepper");
  stepper.classList.remove("hidden");

  const framing =
    activeFramingMode === "auto" ? autoDetectedFraming : activeFramingMode;
  const style =
    activeSubtitleMode === "auto" ? autoDetectedStyle : activeSubtitleMode;

  try {
    appendConsoleLog(
      `[renderer] Initiating 9:16 export: "${hook.title}" [${hook.start}s - ${hook.end}s]`,
    );
    const res = await fetch("/api/jobs/render_clip", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        url: urlVal,
        start: hook.start,
        end: hook.end,
        style: style,
        framing: framing,
        title: hook.title,
        video_title: currentSourceVideoTitle || "",
      }),
    });

    if (!res.ok) {
      const errData = await res
        .json()
        .catch(() => ({ detail: `HTTP ${res.status}` }));
      throw new Error(errData.detail || `Server returned HTTP ${res.status}`);
    }

    const data = await res.json();
    const job_id = data.job_id;
    if (!job_id) {
      throw new Error("Server did not return a valid job ID");
    }
    document.getElementById("active-task-id").innerText = job_id;

    let lastRenderLogIndex = 0;
    const pollRender = setInterval(async () => {
      try {
        const sRes = await fetch(`/api/jobs/${job_id}`);
        if (!sRes.ok) {
          const err = await sRes
            .json()
            .catch(() => ({ detail: `HTTP ${sRes.status}` }));
          throw new Error(
            err.detail || `Render status check failed (HTTP ${sRes.status})`,
          );
        }
        const job = await sRes.json();
        if (!job || job.detail) {
          throw new Error(job?.detail || "Invalid render job response");
        }

        document.getElementById("stepper-status-text").innerText =
          job.step || "Encoding vertical 1080x1920 reel...";
        document.getElementById("stepper-percent").innerText =
          `${job.progress || 10}%`;
        document.getElementById("stepper-progress-fill").style.width =
          `${job.progress || 10}%`;

        if (job.logs && job.logs.length > lastRenderLogIndex) {
          const newLogs = job.logs.slice(lastRenderLogIndex);
          newLogs.forEach((l) => appendConsoleLog(l));
          lastRenderLogIndex = job.logs.length;
        }

        if (job.status === "completed" || job.status === "failed") {
          clearInterval(pollRender);
          btn.disabled = false;
          btn.innerHTML = `<i data-lucide="video" class="w-4 h-4"></i><span>Export 9:16</span>`;
          lucide.createIcons();

          if (job.status === "failed") {
            appendConsoleLog(
              `[render error] ${job.error || "Video export failed"}`,
            );
            return;
          }

          if (job.status === "completed") {
            appendConsoleLog(
              `[renderer] Reel rendered successfully: ${job.output_file}`,
            );
            await loadOutputs();
            switchTab("gallery");
            if (job.output_file) {
              playOutputVideo(job.output_file, hook.title);
            }
          }
        }
      } catch (pollErr) {
        clearInterval(pollRender);
        appendConsoleLog(`[render error] ${pollErr.message}`);
        btn.disabled = false;
        btn.innerHTML = `<i data-lucide="video" class="w-4 h-4"></i><span>Export 9:16</span>`;
        lucide.createIcons();
      }
    }, 1000);
  } catch (e) {
    console.error(e);
    appendConsoleLog(`[render error] ${e.message}`);
    btn.disabled = false;
    btn.innerHTML = `<i data-lucide="video" class="w-4 h-4"></i><span>Export 9:16</span>`;
    lucide.createIcons();
  }
}

async function triggerMakePipeline() {
  const target = document.getElementById("source-url").value.trim();
  if (!target) {
    appendConsoleLog("[error] Please enter a URL or target to run pipeline.");
    return;
  }

  const btn = document.getElementById("execute-make-btn");
  btn.disabled = true;
  btn.innerHTML = `<i data-lucide="loader" class="w-3.5 h-3.5 animate-spin"></i><span>Running...</span>`;
  lucide.createIcons();

  const stepper = document.getElementById("pipeline-stepper");
  stepper.classList.remove("hidden");

  try {
    const res = await fetch("/api/jobs/make", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        target: target,
        framing:
          activeFramingMode === "auto"
            ? autoDetectedFraming
            : activeFramingMode,
        style:
          activeSubtitleMode === "auto"
            ? autoDetectedStyle
            : activeSubtitleMode,
      }),
    });

    if (!res.ok) {
      const errData = await res
        .json()
        .catch(() => ({ detail: `HTTP ${res.status}` }));
      throw new Error(errData.detail || `Server returned HTTP ${res.status}`);
    }

    const data = await res.json();
    const job_id = data.job_id;
    if (!job_id) {
      throw new Error("Server did not return a valid job ID");
    }
    document.getElementById("active-task-id").innerText = job_id;

    let lastMakeLogIndex = 0;
    const pollMake = setInterval(async () => {
      try {
        const sRes = await fetch(`/api/jobs/${job_id}`);
        if (!sRes.ok) {
          const err = await sRes
            .json()
            .catch(() => ({ detail: `HTTP ${sRes.status}` }));
          throw new Error(
            err.detail || `Pipeline check failed (HTTP ${sRes.status})`,
          );
        }
        const job = await sRes.json();
        if (!job || job.detail) {
          throw new Error(job?.detail || "Invalid pipeline response");
        }

        document.getElementById("stepper-status-text").innerText =
          job.step || "Autonomous pipeline active...";
        document.getElementById("stepper-percent").innerText =
          `${job.progress || 10}%`;
        document.getElementById("stepper-progress-fill").style.width =
          `${job.progress || 10}%`;

        if (job.logs && job.logs.length > lastMakeLogIndex) {
          const newLogs = job.logs.slice(lastMakeLogIndex);
          newLogs.forEach((l) => appendConsoleLog(l));
          lastMakeLogIndex = job.logs.length;
        }

        if (job.status === "completed" || job.status === "failed") {
          clearInterval(pollMake);
          btn.disabled = false;
          btn.innerHTML = `<i data-lucide="play" class="w-3.5 h-3.5 text-[#d2fa69]"></i><span>Run pipeline</span>`;
          lucide.createIcons();
          if (job.status === "failed") {
            appendConsoleLog(
              `[pipeline error] Job failed: ${job.error || "Unknown error"}`,
            );
          }
          loadOutputs();
        }
      } catch (pollErr) {
        clearInterval(pollMake);
        appendConsoleLog(`[pipeline error] ${pollErr.message}`);
        btn.disabled = false;
        btn.innerHTML = `<i data-lucide="play" class="w-3.5 h-3.5 text-[#d2fa69]"></i><span>Run pipeline</span>`;
        lucide.createIcons();
      }
    }, 1000);
  } catch (e) {
    console.error(e);
    appendConsoleLog(`[pipeline error] ${e.message}`);
    btn.disabled = false;
    btn.innerHTML = `<i data-lucide="play" class="w-3.5 h-3.5 text-[#d2fa69]"></i><span>Run pipeline</span>`;
    lucide.createIcons();
  }
}

// ==================== SETTINGS & .ENV MANAGEMENT ====================
async function loadEnvConfig() {
  try {
    const res = await fetch("/api/env");
    const data = await res.json();
    cachedEnvConfig = data;
    const vals = data.values || {};

    document.getElementById("env-gemini-key").value = vals.GEMINI_API_KEY || "";
    if (vals.GEMINI_MODEL)
      document.getElementById("env-gemini-model").value = vals.GEMINI_MODEL;
    if (vals.SUB_STYLE)
      document.getElementById("env-sub-style").value = vals.SUB_STYLE;
    if (vals.GEMINI_MODEL_FALLBACKS)
      document.getElementById("env-gemini-fallbacks").value =
        vals.GEMINI_MODEL_FALLBACKS;
    if (vals.AUTO_CLIP_DENSITY_MINUTES)
      document.getElementById("env-density-minutes").value =
        vals.AUTO_CLIP_DENSITY_MINUTES;
    if (vals.FFMPEG_THREADS)
      document.getElementById("env-ffmpeg-threads").value = vals.FFMPEG_THREADS;

    document.getElementById("env-raw-textarea").value = data.raw || "";
  } catch (e) {
    console.error(e);
  }
}

async function saveEnvForm() {
  const activeIsRaw = !document
    .getElementById("env-raw-view")
    .classList.contains("hidden");
  let payload = {};

  if (activeIsRaw) {
    payload = { raw: document.getElementById("env-raw-textarea").value };
  } else {
    payload = {
      values: {
        GEMINI_API_KEY: document.getElementById("env-gemini-key").value.trim(),
        GEMINI_MODEL: document.getElementById("env-gemini-model").value,
        SUB_STYLE: document.getElementById("env-sub-style").value,
        GEMINI_MODEL_FALLBACKS: document
          .getElementById("env-gemini-fallbacks")
          .value.trim(),
        AUTO_CLIP_DENSITY_MINUTES: document.getElementById(
          "env-density-minutes",
        ).value,
        FFMPEG_THREADS: document.getElementById("env-ffmpeg-threads").value,
      },
    };
  }

  try {
    const res = await fetch("/api/env", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    if (res.ok) {
      const alertElem = document.getElementById("env-status-alert");
      alertElem.classList.remove("hidden");
      setTimeout(() => alertElem.classList.add("hidden"), 3500);
      await loadEnvConfig();
    }
  } catch (e) {
    console.error(e);
  }
}

function switchEnvTab(mode) {
  const isRaw = mode === "raw";
  document.getElementById("env-form-view").classList.toggle("hidden", isRaw);
  document.getElementById("env-raw-view").classList.toggle("hidden", !isRaw);

  const tabForm = document.getElementById("env-tab-form");
  const tabRaw = document.getElementById("env-tab-raw");

  if (isRaw) {
    tabRaw.className =
      "px-3 py-1.5 bg-[#242721] text-white font-medium rounded-md border border-white/10 transition-all";
    tabForm.className =
      "px-3 py-1.5 text-slate-400 hover:text-white rounded-md transition-all";
  } else {
    tabForm.className =
      "px-3 py-1.5 bg-[#242721] text-white font-medium rounded-md border border-white/10 transition-all";
    tabRaw.className =
      "px-3 py-1.5 text-slate-400 hover:text-white rounded-md transition-all";
  }
}

function togglePasswordVisibility(fieldId, btn) {
  const field = document.getElementById(fieldId);
  if (field.type === "password") {
    field.type = "text";
    btn.innerHTML = `<i data-lucide="eye-off" class="w-4 h-4"></i>`;
  } else {
    field.type = "password";
    btn.innerHTML = `<i data-lucide="eye" class="w-4 h-4"></i>`;
  }
  lucide.createIcons();
}

// ==================== CHANNELS.TXT RADAR ====================
async function loadChannels() {
  try {
    const res = await fetch("/api/channels");
    const data = await res.json();
    cachedChannels = data.channels || [];
    renderChannelsTable();
  } catch (e) {
    console.error(e);
  }
}

function renderChannelsTable() {
  const tbody = document.getElementById("channels-table-body");
  if (!tbody) return;

  if (cachedChannels.length === 0) {
    tbody.innerHTML = `<tr><td colspan="4" class="p-6 text-center text-slate-500 font-mono">No channels configured in channels.txt</td></tr>`;
    return;
  }

  tbody.innerHTML = cachedChannels
    .map((line, idx) => {
      const parts = line.split("|").map((s) => s.trim());
      const handle = parts[0] || "";
      const clips = parts.find((p) => p.startsWith("clips=")) || "clips=auto";
      const focus =
        parts.find((p) => p.startsWith("focus=")) || "focus=general";

      return `
          <tr class="hover:bg-white/[0.02] transition-colors">
            <td class="p-3 font-mono font-medium text-white">${handle}</td>
            <td class="p-3 text-slate-400 font-mono tabular">${clips}</td>
            <td class="p-3 text-slate-400 font-mono">${focus}</td>
            <td class="p-3 text-right">
              <button onclick="removeChannel(${idx})" class="text-red-400 hover:text-red-300 font-mono text-[11px]">
                Remove
              </button>
            </td>
          </tr>
        `;
    })
    .join("");
}

function addNewChannel() {
  const input = document.getElementById("new-channel-input");
  const val = input.value.trim();
  if (!val) return;
  cachedChannels.push(val);
  input.value = "";
  renderChannelsTable();
}

function removeChannel(idx) {
  cachedChannels.splice(idx, 1);
  renderChannelsTable();
}

async function saveActiveChannels() {
  try {
    await fetch("/api/channels", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ channels: cachedChannels }),
    });
    appendConsoleLog("[channels] Successfully saved channels.txt");
  } catch (e) {
    console.error(e);
  }
}

// ==================== GALLERY & OUTPUTS ====================
async function loadOutputs() {
  try {
    const res = await fetch("/api/outputs");
    const data = await res.json();
    const files = data.files || [];
    const folders = data.folders || [];
    document.getElementById("gallery-count").innerText = files.length;

    const container =
      document.getElementById("outputs-grid") ||
      document.getElementById("outputs-container");
    if (!container) return;

    if (files.length === 0) {
      container.innerHTML = `
            <div class="p-12 border border-white/[0.08] bg-[#191b18] rounded-xl text-center space-y-3">
              <div class="w-10 h-10 rounded-full bg-[#242721] border border-white/10 flex items-center justify-center mx-auto text-slate-400">
                <i data-lucide="video" class="w-5 h-5"></i>
              </div>
              <div>
                <p class="text-sm font-medium text-slate-300">No rendered video clips in output/ yet</p>
                <p class="text-xs text-slate-500 mt-1 font-mono">Use "Export 9:16" or "Run pipeline" to generate high-retention vertical reels.</p>
              </div>
            </div>
          `;
      lucide.createIcons();
      return;
    }

    const tokenParam = window.__HOOKY_TOKEN__
      ? `?token=${encodeURIComponent(window.__HOOKY_TOKEN__)}`
      : "";

    // Render foldered collections grouped by source video title
    if (folders.length > 0) {
      container.innerHTML = folders
        .map((folder) => {
          const folderFiles = folder.files || [];
          return `
              <div class="border border-white/[0.08] bg-[#141519] rounded-xl overflow-hidden transition-all">
                <div class="px-5 py-3.5 bg-[#191b18] border-b border-white/[0.06] flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                  <div class="flex items-center gap-3">
                    <div class="w-8 h-8 rounded-lg bg-[#242721] border border-white/10 flex items-center justify-center text-[#ffd166] shrink-0">
                      <i data-lucide="folder-video" class="w-4 h-4"></i>
                    </div>
                    <div>
                      <h3 class="text-sm font-medium text-white tracking-tight leading-snug">${folder.name}</h3>
                      <p class="text-[11px] text-slate-400 font-mono">Source collection • ${folderFiles.length} ${folderFiles.length === 1 ? "reel" : "reels"}</p>
                    </div>
                  </div>
                  <span class="self-start sm:self-auto text-[11px] font-mono px-2.5 py-0.5 bg-white/5 text-slate-300 border border-white/10 rounded-full tabular">
                    ${folderFiles.length} ${folderFiles.length === 1 ? "clip" : "clips"}
                  </span>
                </div>

                <div class="p-4 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                  ${folderFiles
                    .map((f) => {
                      const rankMatch = f.name.match(
                        /reel_rank(\d+)_(\d+)pts/i,
                      );
                      const badgeHTML = rankMatch
                        ? `<span class="text-[10px] font-mono px-2 py-0.5 bg-[#ffd166]/10 text-[#ffd166] border border-[#ffd166]/20 rounded font-semibold">Rank #${parseInt(rankMatch[1])} • ${rankMatch[2]}pts</span>`
                        : `<span class="text-[10px] font-mono px-2 py-0.5 bg-white/5 text-slate-300 border border-white/10 rounded font-medium">1080×1920 MP4</span>`;

                      const cleanDisplayName =
                        f.name
                          .replace(/^reel_rank\d+_\d+pts_/, "")
                          .replace(/^reel_/, "")
                          .replace(/_\d+\.mp4$/, "")
                          .replace(/_/g, " ") || f.name;
                      const encodedUrl = `/api/outputs/${String(f.rel_path).replace(/\\/g, "/").split("/").map(encodeURIComponent).join("/")}${tokenParam}`;

                      return `
                      <div class="p-4 bg-[#191b18] border border-white/[0.08] hover:border-white/20 rounded-lg transition-all space-y-3 font-mono flex flex-col justify-between">
                        <div class="space-y-2">
                          <div class="flex items-center justify-between gap-2">
                            ${badgeHTML}
                            <span class="text-[11px] text-slate-400 tabular">${f.size_mb} MB</span>
                          </div>
                          <div>
                            <h4 class="font-medium text-white text-xs truncate max-w-full font-sans capitalize" title="${f.name}">${cleanDisplayName}</h4>
                            <p class="text-[10px] text-slate-500 mt-0.5">${new Date(f.mtime * 1000).toLocaleString()}</p>
                          </div>
                        </div>
                        <div class="flex items-center gap-2 pt-2 border-t border-white/[0.06]">
                          <button
                            onclick="playOutputVideo('${String(f.rel_path).replace(/\\/g, "/").replace(/'/g, "\\'")}', '${cleanDisplayName.replace(/'/g, "\\'")}')"
                            class="flex-1 py-1.5 bg-[#242721] hover:bg-[#2b2e38] text-white border border-white/10 rounded text-xs font-medium flex items-center justify-center gap-1.5 transition-all"
                          >
                            <i data-lucide="play" class="w-3.5 h-3.5 text-[#d2fa69]"></i>
                            <span>Watch</span>
                          </button>
                          <a
                            href="${encodedUrl}"
                            download
                            class="px-3 py-1.5 bg-[#101110] text-slate-300 hover:text-white border border-white/[0.08] rounded text-xs transition-all"
                            title="Download MP4"
                          >
                            <i data-lucide="download" class="w-3.5 h-3.5 inline"></i>
                          </a>
                        </div>
                      </div>
                    `;
                    })
                    .join("")}
                </div>
              </div>
            `;
        })
        .join("");
    } else {
      container.innerHTML = files
        .map((f) => {
          const cleanDisplayName =
            f.name
              .replace(/^reel_/, "")
              .replace(/_\d+\.mp4$/, "")
              .replace(/_/g, " ") || f.name;
          const encodedUrl = `/api/outputs/${String(f.rel_path).replace(/\\/g, "/").split("/").map(encodeURIComponent).join("/")}${tokenParam}`;
          return `
              <div class="p-4 bg-[#191b18] border border-white/[0.08] hover:border-white/20 rounded-lg transition-all space-y-3 font-mono">
                <div class="flex items-center justify-between">
                  <span class="text-xs px-2 py-0.5 bg-white/5 text-slate-300 border border-white/10 rounded font-medium">1080×1920 MP4</span>
                  <span class="text-xs text-slate-400 tabular">${f.size_mb} MB</span>
                </div>
                <div>
                  <h4 class="font-medium text-white text-xs truncate max-w-full font-sans capitalize" title="${f.name}">${cleanDisplayName}</h4>
                  <p class="text-[11px] text-slate-500 mt-0.5">${new Date(f.mtime * 1000).toLocaleString()}</p>
                </div>
                <div class="flex items-center gap-2 pt-2 border-t border-white/[0.06]">
                  <button
                    onclick="playOutputVideo('${String(f.rel_path).replace(/\\/g, "/").replace(/'/g, "\\'")}', '${cleanDisplayName.replace(/'/g, "\\'")}')"
                    class="flex-1 py-1.5 bg-[#242721] hover:bg-[#2b2e38] text-white border border-white/10 rounded text-xs font-medium flex items-center justify-center gap-1.5 transition-all"
                  >
                    <i data-lucide="play" class="w-3.5 h-3.5 text-[#d2fa69]"></i>
                    <span>Watch</span>
                  </button>
                  <a
                    href="${encodedUrl}"
                    download
                    class="px-3 py-1.5 bg-[#101110] text-slate-300 hover:text-white border border-white/[0.08] rounded text-xs transition-all"
                  >
                    <i data-lucide="download" class="w-3.5 h-3.5 inline"></i>
                  </a>
                </div>
              </div>
            `;
        })
        .join("");
    }
    lucide.createIcons();
  } catch (e) {
    console.error(e);
  }
}

function playOutputVideo(filepath, title) {
  const box = document.getElementById("active-video-player-box");
  box.classList.remove("hidden");
  document.getElementById("active-playing-title").innerText = title || filepath;

  const player = document.getElementById("html5-video-player");
  const srcElem = document.getElementById("video-source-elem");
  const tokenParam = window.__HOOKY_TOKEN__
    ? `?token=${encodeURIComponent(window.__HOOKY_TOKEN__)}`
    : "";
  const cleanPath = String(filepath).replace(/\\/g, "/");
  const encodedPath = cleanPath.split("/").map(encodeURIComponent).join("/");
  srcElem.src = `/api/outputs/${encodedPath}${tokenParam}`;
  player.load();
  player.play().catch(() => {});
  box.scrollIntoView({ behavior: "smooth" });
}

function closeActivePlayer() {
  const box = document.getElementById("active-video-player-box");
  box.classList.add("hidden");
  const player = document.getElementById("html5-video-player");
  player.pause();
}

// ==================== SYSTEM DOCTOR ====================
async function loadDoctorReport() {
  try {
    const res = await fetch("/api/doctor");
    const data = await res.json();
    const container = document.getElementById("doctor-checks-container");
    if (!container) return;

    if (data.gpu) {
      document.getElementById("gpu-text").innerText = data.gpu;
    }

    const checks = data.checks || [];
    container.innerHTML = checks
      .map(
        (c) => `
          <div class="p-3 bg-[#191b18] border border-white/[0.08] rounded-md flex items-center justify-between text-xs font-mono">
            <div class="flex items-center gap-2">
              <span class="${c.ok ? "text-[#d2fa69]" : "text-red-400"} font-medium">
                ${c.ok ? "✓ pass" : "✗ fail"}
              </span>
              <span class="text-white font-medium">${c.name}</span>
            </div>
            <span class="text-slate-400 text-[11px] truncate max-w-[200px]" title="${c.detail}">${c.detail}</span>
          </div>
        `,
      )
      .join("");
  } catch (e) {
    console.error(e);
  }
}
