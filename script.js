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

let currentFile = null;
let alreadyAnalyzed = false;
let currentAnalysisData = null;

const API_URLS = [
    "http://127.0.0.1:8001/analyze",
    "http://localhost:8001/analyze"
];

// --- FILE UPLOAD HANDLER ---
audioUpload.addEventListener("change", function() {
    if (this.files.length > 0) {
        initPlayer(this.files[0]);
    }
});

function initPlayer(file) {
    currentFile = file;
    alreadyAnalyzed = false;
    currentAnalysisData = null;
    fileNameDisplay.textContent = file.name;
    audio.src = URL.createObjectURL(file);
    audio.load();

    uploadContainer.classList.add("hidden");
    playerContainer.classList.remove("hidden");
    result.classList.add("hidden");
    playBtn.innerHTML = '<i class="fa-solid fa-play"></i>';
}

// --- PLAY BUTTON LOGIC ---
playBtn.addEventListener("click", async () => {
  if (!currentFile) {
    alert("Please upload a file first.");
    return;
  }

  if (!alreadyAnalyzed) {
    await analyzeAudio(currentFile);
    alreadyAnalyzed = true;
  }

  if (audio.paused) {
    audio.play().then(() => {
      playBtn.innerHTML = '<i class="fa-solid fa-pause"></i>';
      waveform.classList.add("active");
      bars.forEach(b => b.style.animationPlayState = "running");
    }).catch(e => console.error("Audio Play Error:", e));
  } else {
    audio.pause();
    playBtn.innerHTML = '<i class="fa-solid fa-play"></i>';
    waveform.classList.remove("active");
    bars.forEach(b => b.style.animationPlayState = "paused");
  }
});

audio.addEventListener("ended", () => {
  playBtn.innerHTML = '<i class="fa-solid fa-play"></i>';
  waveform.classList.remove("active");
  bars.forEach(b => b.style.animationPlayState = "paused");
});

// --- ANALYSIS FUNCTION ---
async function analyzeAudio(file) {
  loading.classList.remove("hidden");
  result.classList.add("hidden");

  let lastError = null;

  // ✅ FIX: create fresh FormData INSIDE the loop (no consumed body bug)
  for (let API_URL of API_URLS) {
    try {
      console.log(`Trying API: ${API_URL}`);

      const formData = new FormData();
      formData.append("file", file);

      const response = await fetch(API_URL, {
        method: "POST",
        body: formData,
        mode: "cors",
        cache: "no-store", // ✅ prevents caching weirdness
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      const data = await response.json();
      console.log("Success:", data);

      // ✅ keep analysis data for save button
      currentAnalysisData = data;

      // ✅ Fill UI safely
      document.getElementById("locationText").textContent = data.location || "Unknown";
      document.getElementById("situationText").textContent = data.situation || "Analysis Complete";

      let conf = data.confidence;
      if (typeof conf === "number") {
        if (conf <= 1) conf = Math.round(conf * 100);
        else conf = Math.round(conf);
        document.getElementById("confidenceText").textContent = conf + "%";
      } else {
        document.getElementById("confidenceText").textContent = "--%";
      }

      document.getElementById("evidenceText").textContent = Array.isArray(data.evidence)
        ? data.evidence.join(", ")
        : (data.evidence || "None");

      document.getElementById("summaryText").textContent = data.summary || "No summary";
      document.getElementById("transcribeText").textContent = data.transcribe || "No transcription";

      loading.classList.add("hidden");
      result.classList.remove("hidden");
      return; // ✅ stop loop on success

    } catch (error) {
      console.warn(`Failed with ${API_URL}:`, error.message);
      lastError = error;
    }
  }

  loading.classList.add("hidden");

  // ✅ FIX: correct command message
  alert(
    "Backend Connection Failed!\n\n" +
    "Solutions:\n" +
    "1) Run backend:\n" +
    "   py -m uvicorn app:app --reload --host 127.0.0.1 --port 8001\n\n" +
    "2) Check backend docs:\n" +
    "   http://127.0.0.1:8001/docs\n\n" +
    "Error: " + (lastError ? lastError.message : "Unknown")
  );
}

// --- SAVE TO DASHBOARD ---
saveBtn.addEventListener("click", function() {
    if (!currentAnalysisData) {
        alert("No analysis data to save!");
        return;
    }

    let history;
    try {
      history = JSON.parse(localStorage.getItem("auralisHistory")) || [];
      if (!Array.isArray(history)) history = [];
    } catch {
      history = [];
    }

    const now = new Date();
    const timestamp = now.toLocaleString('en-US', {
        month: 'short',
        day: 'numeric',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    });

    const historyItem = {
        timestamp: timestamp,
        location: currentAnalysisData.location || "Unknown",
        situation: currentAnalysisData.situation || "Unknown",
        confidence: document.getElementById("confidenceText").textContent || "--%",
        soundType: Array.isArray(currentAnalysisData.evidence)
            ? currentAnalysisData.evidence[0]
            : "Audio Analysis",
        fileName: currentFile ? currentFile.name : "unknown.wav"
    };

    history.unshift(historyItem);

    if (history.length > 50) {
        history = history.slice(0, 50);
    }

    localStorage.setItem("auralisHistory", JSON.stringify(history));

    const originalHTML = saveBtn.innerHTML;

    saveBtn.innerHTML = '<i class="fa-solid fa-check"></i> Saved!';
    saveBtn.style.background = "#28a745";

    setTimeout(() => {
        saveBtn.innerHTML = originalHTML;
        saveBtn.style.background = "";
    }, 2000);

    console.log("Saved to history:", historyItem);
});

// --- DRAG AND DROP FUNCTIONALITY ---
const dropZone = document.querySelector('.upload-container');

if (dropZone) {
  ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
    document.body.addEventListener(eventName, preventDefaults, false);
  });

  function preventDefaults(e) {
    e.preventDefault();
    e.stopPropagation();
  }

  ['dragenter', 'dragover'].forEach(eventName => {
    dropZone.addEventListener(eventName, highlight, false);
  });

  ['dragleave', 'drop'].forEach(eventName => {
    dropZone.addEventListener(eventName, unhighlight, false);
  });

  function highlight(e) {
    dropZone.style.borderColor = '#7f3cff';
    dropZone.style.background = 'rgba(127, 60, 255, 0.1)';
    dropZone.style.transform = 'scale(1.02)';
  }

  function unhighlight(e) {
    dropZone.style.borderColor = '#333';
    dropZone.style.background = 'rgba(255,255,255,0.01)';
    dropZone.style.transform = 'scale(1)';
  }

  dropZone.addEventListener('drop', handleDrop, false);

  function handleDrop(e) {
    const dt = e.dataTransfer;
    const files = dt.files;

    if (files.length > 0) {
      const file = files[0];

      if (file.type.startsWith('audio/')) {
        initPlayer(file);
      } else {
        alert('Please drop an audio file (MP3, WAV, M4A)');
      }
    }
  }
}
