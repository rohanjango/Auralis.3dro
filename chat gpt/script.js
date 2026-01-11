// ===============================
// ✅ Auralis - Frontend Main JS (Audio + Video Upload)
// ✅ Fixes:
//    1) "Failed to fetch" (always calls backend on port 8000)
//    2) Audio duration recognition (mm:ss)
//    3) Video upload + playback controls (play/pause/stop/seek)
//    4) Save to Dashboard confirm + popup feedback
//    5) Strong error messages + safer UI updates
// ===============================

// ---------- Elements ----------
const audio = document.getElementById("audio");
const playBtn = document.getElementById("playBtn");
const bars = document.querySelectorAll(".waveform span");
const waveform = document.getElementById("waveform");

const fileNameDisplay = document.getElementById("fileNameDisplay");
const uploadContainer = document.getElementById("uploadContainer");
const playerContainer = document.getElementById("playerContainer");
const loading = document.getElementById("loading");
const result = document.getElementById("result");
const audioUpload = document.getElementById("audioUpload");
const saveBtn = document.getElementById("saveBtn");

// Optional time display (index.html has it)
const timeDisplay = document.querySelector(".time-display");

// ---------- Video Elements (optional, if present in HTML) ----------
const videoUpload = document.getElementById("videoUpload");
const videoSection = document.getElementById("videoSection");
const videoPlayer = document.getElementById("videoPlayer");
const videoControls = document.getElementById("videoControls");
const vPlayPause = document.getElementById("vPlayPause");
const vStop = document.getElementById("vStop");
const vSeek = document.getElementById("vSeek");
const vTime = document.getElementById("vTime");

// ---------- Backend URL ----------
const API_BASE = "http://127.0.0.1:8000";
const ANALYZE_URL = `${API_BASE}/analyze`;

// ---------- State ----------
let currentFile = null;
let currentAnalysisData = null;
let analysisInProgress = false;

// ---------- Helpers ----------
function setText(id, text) {
  const el = document.getElementById(id);
  if (el) el.innerText = text;
}

function normalizeEvidence(evidence) {
  if (!evidence) return [];
  if (Array.isArray(evidence)) return evidence.map(String).map(s => s.trim()).filter(Boolean);
  if (typeof evidence === "string") return evidence.split(",").map(s => s.trim()).filter(Boolean);
  return [String(evidence)];
}

function formatConfidence(confidence) {
  if (confidence === null || confidence === undefined || confidence === "") return "0%";

  let num = confidence;
  if (typeof num === "string") {
    num = num.replace("%", "").trim();
    num = Number(num);
  }
  if (Number.isNaN(num)) return "0%";

  // if 0..1 => convert to %
  if (num <= 1) num = num * 100;
  num = Math.round(num);

  // clamp
  if (num < 0) num = 0;
  if (num > 100) num = 100;
  return `${num}%`;
}

function formatTime(seconds) {
  if (!Number.isFinite(seconds) || seconds < 0) seconds = 0;
  const m = Math.floor(seconds / 60);
  const s = Math.floor(seconds % 60);
  return `${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`;
}

function showToast(message, type = "success") {
  // lightweight toast without external libs
  const toast = document.createElement("div");
  toast.className = `toast ${type}`;
  toast.innerText = message;
  document.body.appendChild(toast);
  setTimeout(() => toast.classList.add("show"), 10);
  setTimeout(() => {
    toast.classList.remove("show");
    setTimeout(() => toast.remove(), 250);
  }, 2400);
}

// ---------- Audio Duration Recognition ----------
function bindAudioDurationUI() {
  if (!audio) return;

  // When metadata is loaded => duration known
  audio.addEventListener("loadedmetadata", () => {
    if (!timeDisplay) return;
    const dur = Number(audio.duration);
    timeDisplay.textContent = `00:00 / ${formatTime(dur)}`;
  });

  audio.addEventListener("timeupdate", () => {
    if (!timeDisplay) return;
    const cur = Number(audio.currentTime);
    const dur = Number(audio.duration);
    timeDisplay.textContent = `${formatTime(cur)} / ${formatTime(dur)}`;
  });

  audio.addEventListener("ended", () => {
    if (playBtn) playBtn.innerHTML = '<i class="fa-solid fa-play"></i>';
    waveform?.classList.remove("active");
    bars.forEach((b) => (b.style.animationPlayState = "paused"));
  });
}

// ---------- File Upload ----------
audioUpload?.addEventListener("change", function () {
  if (this.files && this.files.length > 0) {
    initAudioPlayer(this.files[0]);
  }
});

function initAudioPlayer(file) {
  currentFile = file;
  currentAnalysisData = null;
  analysisInProgress = false;

  // Validate audio format basic check
  const okTypes = ["audio/mpeg", "audio/mp3", "audio/wav", "audio/x-wav", "audio/aac", "audio/mp4", "audio/x-m4a", "audio/ogg", "audio/webm"];
  if (file.type && !okTypes.includes(file.type)) {
    showToast("Unsupported audio format. Try MP3/WAV/AAC.", "error");
  }

  fileNameDisplay && (fileNameDisplay.textContent = file.name);
  audio.src = URL.createObjectURL(file);
  audio.load();

  uploadContainer?.classList.add("hidden");
  playerContainer?.classList.remove("hidden");

  loading?.classList.add("hidden");
  result?.classList.add("hidden");

  // Reset UI
  playBtn && (playBtn.innerHTML = '<i class="fa-solid fa-play"></i>');
  waveform?.classList.remove("active");
  bars.forEach((b) => (b.style.animationPlayState = "paused"));

  // Save disabled until analysis complete
  if (saveBtn) saveBtn.disabled = true;

  console.log("🎧 File loaded:", file.name, "| Type:", file.type, "| Size:", file.size);
}

// ---------- Audio Play/Analyze ----------
playBtn?.addEventListener("click", async () => {
  if (!currentFile) {
    showToast("Please upload an audio file first.", "error");
    return;
  }

  // Analyze first time before play
  if (!currentAnalysisData && !analysisInProgress) {
    await analyzeAudio(currentFile);
  }

  // Still allow play even if analysis failed
  if (audio.paused) {
    audio.play();
    playBtn.innerHTML = '<i class="fa-solid fa-pause"></i>';
    waveform?.classList.add("active");
    bars.forEach((b) => (b.style.animationPlayState = "running"));
  } else {
    audio.pause();
    playBtn.innerHTML = '<i class="fa-solid fa-play"></i>';
    waveform?.classList.remove("active");
    bars.forEach((b) => (b.style.animationPlayState = "paused"));
  }
});

async function analyzeAudio(file) {
  if (!file) return;

  analysisInProgress = true;
  currentAnalysisData = null;

  // UI loading
  loading?.classList.remove("hidden");
  result?.classList.add("hidden");

  playBtn && (playBtn.disabled = true);
  if (saveBtn) saveBtn.disabled = true;

  const formData = new FormData();
  formData.append("file", file); // backend expects "file"

  try {
    // ✅ quick backend check (avoids Failed to fetch)
    try {
      const health = await fetch(`${API_BASE}/`, { method: "GET" });
      if (!health.ok) throw new Error("Backend unreachable");
    } catch {
      throw new Error(
        "Failed to reach backend.

✅ Fix:
1) Run backend: python app.py
2) Backend on http://127.0.0.1:8000
3) Test: http://127.0.0.1:8000/docs"
      );
    }

    console.log("🚀 Sending file to backend:", file.name);
    console.log("🌐 URL:", ANALYZE_URL);

    // ✅ Backend health check (gives clear error instantly)
    try {
      const health = await fetch(`${API_BASE}/`, { method: "GET" });
      if (!health.ok) throw new Error();
    } catch {
      throw new Error(
        "Failed to reach backend.

✅ Fix:
1) Run backend: python app.py
2) Backend on http://127.0.0.1:8000
3) Test: http://127.0.0.1:8000/docs"
      );
    }

    const response = await fetch(ANALYZE_URL, { method: "POST", body: formData });

    if (!response.ok) {
      const text = await response.text().catch(() => "");
      throw new Error(`Server error ${response.status} ${response.statusText}\n${text}`);
    }

    let data;
    try {
      data = await response.json();
    } catch {
      throw new Error("Backend response is not valid JSON.");
    }

    if (data?.error) throw new Error(data.error);

    currentAnalysisData = data;

    // Update UI
    setText("locationText", data.location || "Unknown");
    setText("situationText", data.situation || "Unknown");
    const evidenceList = normalizeEvidence(data.evidence);
    setText("evidenceText", evidenceList.length ? evidenceList.join(", ") : "None");
    setText("confidenceText", formatConfidence(data.confidence));
    setText("summaryText", data.summary || "No summary.");
    setText("transcribeText", data.transcribed || "No speech detected.");

    loading?.classList.add("hidden");
    result?.classList.remove("hidden");

    if (saveBtn) saveBtn.disabled = false;

    showToast("Analysis completed ✅", "success");
  } catch (error) {
    console.error("❌ Analysis Failed:", error);
    let msg = error?.message || String(error);

    if (msg.toLowerCase().includes("failed to fetch")) {
      msg =
        "Failed to reach backend.\n\n✅ Fix:\n1) Run backend: python app.py\n2) Backend on http://127.0.0.1:8000\n3) Test: http://127.0.0.1:8000/docs";
    }

    showToast("Analysis failed ❌", "error");

    loading?.classList.add("hidden");
    result?.classList.add("hidden");
    if (saveBtn) saveBtn.disabled = true;
  } finally {
    analysisInProgress = false;
    playBtn && (playBtn.disabled = false);
  }
}

// ---------- Save to Dashboard ----------
saveBtn?.addEventListener("click", function () {
  if (!currentAnalysisData || !currentFile) {
    showToast("Analyze an audio first, then save.", "error");
    return;
  }

  const confirmSave = confirm("Do you want to save this analysis to Dashboard?");
  if (!confirmSave) return;

  try {
    let history = JSON.parse(localStorage.getItem("auralisHistory")) || [];

    const evidenceList = normalizeEvidence(currentAnalysisData.evidence);
    const soundType = evidenceList.length ? evidenceList[0] : "Audio";

    const newItem = {
      timestamp: new Date().toLocaleString(),
      location: currentAnalysisData.location || "Unknown",
      situation: currentAnalysisData.situation || "Unknown",
      confidence: formatConfidence(currentAnalysisData.confidence),
      soundType,
      fileName: currentFile.name,
      transcription: currentAnalysisData.transcribed || ""
    };

    history.unshift(newItem);
    history = history.slice(0, 50); // max 50
    localStorage.setItem("auralisHistory", JSON.stringify(history));

    // UI feedback
    const originalHTML = saveBtn.innerHTML;
    saveBtn.innerHTML = '<i class="fa-solid fa-check"></i> Saved!';
    saveBtn.classList.add("saved");
    setTimeout(() => {
      saveBtn.innerHTML = originalHTML;
      saveBtn.classList.remove("saved");
    }, 1700);

    showToast("Saved to Dashboard ✅", "success");
    console.log("💾 Saved:", newItem);
  } catch (e) {
    console.error("❌ Save failed:", e);
    showToast("Save failed ❌. See console.", "error");
  }
});

// ===============================
// 🎬 VIDEO UPLOAD + PLAYBACK CONTROLS
// ===============================
function setupVideoPlayer() {
  if (!videoUpload || !videoPlayer) return;

  videoUpload.addEventListener("change", function () {
    if (!this.files || this.files.length === 0) return;

    const file = this.files[0];

    // basic type validation
    const okVideo = ["video/mp4", "video/quicktime", "video/x-msvideo", "video/webm", "video/ogg", "video/x-matroska"];
    if (file.type && !okVideo.includes(file.type)) {
      showToast("Unsupported video format. Try MP4/MOV/AVI.", "error");
      return;
    }

    videoPlayer.src = URL.createObjectURL(file);
    videoPlayer.load();

    videoSection?.classList.remove("hidden");
    videoControls?.classList.remove("hidden");

    showToast("Video loaded ✅", "success");
  });

  vPlayPause?.addEventListener("click", () => {
    if (videoPlayer.paused) {
      videoPlayer.play();
      vPlayPause.innerHTML = '<i class="fa-solid fa-pause"></i> Pause';
    } else {
      videoPlayer.pause();
      vPlayPause.innerHTML = '<i class="fa-solid fa-play"></i> Play';
    }
  });

  vStop?.addEventListener("click", () => {
    videoPlayer.pause();
    videoPlayer.currentTime = 0;
    vPlayPause.innerHTML = '<i class="fa-solid fa-play"></i> Play';
  });

  videoPlayer.addEventListener("loadedmetadata", () => {
    if (vSeek) vSeek.max = String(videoPlayer.duration || 0);
    if (vTime) vTime.textContent = `00:00 / ${formatTime(videoPlayer.duration || 0)}`;
  });

  videoPlayer.addEventListener("timeupdate", () => {
    if (vSeek && !vSeek.dragging) vSeek.value = String(videoPlayer.currentTime || 0);
    if (vTime) vTime.textContent = `${formatTime(videoPlayer.currentTime || 0)} / ${formatTime(videoPlayer.duration || 0)}`;
  });

  vSeek?.addEventListener("input", () => {
    // Seek while dragging
    const t = Number(vSeek.value);
    if (Number.isFinite(t)) videoPlayer.currentTime = t;
  });

  videoPlayer.addEventListener("ended", () => {
    vPlayPause.innerHTML = '<i class="fa-solid fa-play"></i> Play';
  });
}

// ---------- Init ----------
bindAudioDurationUI();
setupVideoPlayer();
