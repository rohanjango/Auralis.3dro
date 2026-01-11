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

// ✅ FIXED: Updated API URLs to match your backend
const API_URLS = [
    "https://k47lgpmd-8000.inc1.devtunnels.ms/analyze"
]

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

  // ✅ FIX: Create fresh FormData for each attempt
  for (let API_URL of API_URLS) {
    try {
      console.log(`🔄 Trying API: ${API_URL}`);

      const formData = new FormData();
      formData.append("file", file);

      const response = await fetch(API_URL, {
        method: "POST",
        body: formData,
        mode: "cors",
        cache: "no-store",
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      const data = await response.json();
      
      // ✅ FIX: Check if backend returned an error
      if (data.error) {
        throw new Error(data.error);
      }

      console.log("✅ Success:", data);

      // ✅ Store analysis data for save button
      currentAnalysisData = data;

      // ✅ FIXED: Handle app2.py response format
      // app2.py returns: location, situation, confidence, evidence, summary, transcribed
      
      document.getElementById("locationText").textContent = data.location || "Unknown";
      document.getElementById("situationText").textContent = data.situation || "Analysis Complete";

      // ✅ Handle confidence (app2.py returns it as decimal like 0.85)
      let conf = data.confidence;
      if (typeof conf === "number") {
        if (conf <= 1) {
          conf = Math.round(conf * 100);
        } else {
          conf = Math.round(conf);
        }
        document.getElementById("confidenceText").textContent = conf + "%";
      } else {
        document.getElementById("confidenceText").textContent = "--%";
      }

      // ✅ Handle evidence array
      if (Array.isArray(data.evidence)) {
        document.getElementById("evidenceText").textContent = data.evidence.join(", ");
      } else {
        document.getElementById("evidenceText").textContent = data.evidence || "None";
      }

      // ✅ Handle summary
      document.getElementById("summaryText").textContent = data.summary || "No summary available";
      
      // ✅ FIXED: app2.py uses "transcribed" not "transcribe"
      document.getElementById("transcribeText").textContent = data.transcribed || data.transcribe || "No transcription";

      loading.classList.add("hidden");
      result.classList.remove("hidden");
      return; // ✅ Stop loop on success

    } catch (error) {
      console.warn(`❌ Failed with ${API_URL}:`, error.message);
      lastError = error;
    }
  }

  // ✅ All attempts failed
  loading.classList.add("hidden");

  alert(
    "🚨 Backend Connection Failed!\n\n" +
    "Solutions:\n" +
    "1) Make sure backend is running:\n" +
    "   uvicorn app2:app --reload --host 127.0.0.1 --port 8000\n\n" +
    "2) Check backend docs:\n" +
    "   http://127.0.0.1:8000/docs\n\n" +
    "3) Check console for detailed error\n\n" +
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

    // ✅ FIXED: Handle both "transcribed" and "transcribe" fields
    const transcription = currentAnalysisData.transcribed || currentAnalysisData.transcribe || "No transcription";

    const historyItem = {
        timestamp: timestamp,
        location: currentAnalysisData.location || "Unknown",
        situation: currentAnalysisData.situation || "Unknown",
        confidence: document.getElementById("confidenceText").textContent || "--%",
        soundType: Array.isArray(currentAnalysisData.evidence)
            ? currentAnalysisData.evidence[0]
            : "Audio Analysis",
        fileName: currentFile ? currentFile.name : "unknown.wav",
        transcription: transcription
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

    console.log("💾 Saved to history:", historyItem);
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
        alert('⚠️ Please drop an audio file (MP3, WAV, M4A, MP4)');
      }
    }
  }
}