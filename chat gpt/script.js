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
const timeDisplay = document.querySelector(".time-display");

let currentFile = null;
let alreadyAnalyzed = false;
let currentAnalysisData = null;

// ✅ FIXED: Corrected API URL (Removed extra 'e')
const API_URL = "http://127.0.0.1:8000/analyze";

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

    timeDisplay.textContent = "00:00 / 00:00";

    uploadContainer.classList.add("hidden");
    playerContainer.classList.remove("hidden");
    result.classList.add("hidden");
    playBtn.innerHTML = '<i class="fa-solid fa-play"></i>';
}

// --- TIME DISPLAY LOGIC ---
function formatTime(seconds) {
    if (isNaN(seconds)) return "00:00";
    const minutes = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${minutes.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
}

audio.addEventListener("timeupdate", () => {
    const current = formatTime(audio.currentTime);
    const total = formatTime(audio.duration);
    timeDisplay.textContent = `${current} / ${total}`;
});

audio.addEventListener("loadedmetadata", () => {
    timeDisplay.textContent = `00:00 / ${formatTime(audio.duration)}`;
});

// --- PLAY BUTTON LOGIC ---
playBtn.addEventListener("click", async () => {
    if (!currentFile) {
        alert("Please upload a file first.");
        return;
    }

    if (!alreadyAnalyzed) {
        // Pause audio UI while analyzing
        await analyzeAudio(currentFile);
        alreadyAnalyzed = true;
    }

    if (audio.paused) {
        audio.play()
            .then(() => {
                playBtn.innerHTML = '<i class="fa-solid fa-pause"></i>';
                waveform.classList.add("active");
                bars.forEach(b => b.style.animationPlayState = "running");
            })
            .catch(e => console.error("Audio Play Error:", e));
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

    try {
        console.log(`🔄 Sending to API: ${API_URL}`);

        const formData = new FormData();
        formData.append("file", file);

        // Fetch with error handling
        const response = await fetch(API_URL, {
            method: "POST",
            body: formData,
        });

        if (!response.ok) {
            throw new Error(`Server Error: ${response.status} ${response.statusText}`);
        }

        const data = await response.json();

        if (data.error) {
            throw new Error(data.error);
        }

        console.log("✅ API Success:", data);
        currentAnalysisData = data;

        // UI Updates
        document.getElementById("locationText").textContent = data.location || "Unknown";
        document.getElementById("situationText").textContent = data.situation || "Analysis Complete";

        let conf = data.confidence;
        if (typeof conf === "number") {
            // Format 0.85 -> 85%
            document.getElementById("confidenceText").textContent = Math.round(conf * 100) + "%";
        } else {
            document.getElementById("confidenceText").textContent = "--%";
        }

        // Format evidence list
        if (Array.isArray(data.evidence)) {
            document.getElementById("evidenceText").textContent = data.evidence.join(", ");
        } else {
            document.getElementById("evidenceText").textContent = data.evidence || "None";
        }

        document.getElementById("summaryText").textContent = data.summary || "No summary available";
        document.getElementById("transcribeText").textContent = data.transcribed || "No transcription";

        loading.classList.add("hidden");
        result.classList.remove("hidden");

    } catch (error) {
        console.error("❌ Analysis Failed:", error);
        loading.classList.add("hidden");
        alert(
            "🚨 Backend Connection Failed!\n\n" +
            "1. Make sure 'app.py' is running.\n" +
            "2. Check the console for errors.\n" +
            "Error details: " + error.message
        );
    }
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
        month: 'short', day: 'numeric', year: 'numeric',
        hour: '2-digit', minute: '2-digit'
    });

    const evidenceStr = Array.isArray(currentAnalysisData.evidence) 
        ? currentAnalysisData.evidence[0] 
        : "Audio Analysis";

    const historyItem = {
        timestamp: timestamp,
        location: currentAnalysisData.location || "Unknown",
        situation: currentAnalysisData.situation || "Unknown",
        confidence: document.getElementById("confidenceText").textContent || "--%",
        soundType: evidenceStr,
        fileName: currentFile ? currentFile.name : "unknown.wav",
        transcription: currentAnalysisData.transcribed || "No text"
    };

    history.unshift(historyItem);
    if (history.length > 50) history = history.slice(0, 50); // Keep last 50

    localStorage.setItem("auralisHistory", JSON.stringify(history));

    // Visual feedback
    const originalHTML = saveBtn.innerHTML;
    saveBtn.innerHTML = '<i class="fa-solid fa-check"></i> Saved!';
    saveBtn.style.background = "#28a745";

    setTimeout(() => {
        saveBtn.innerHTML = originalHTML;
        saveBtn.style.background = "";
    }, 2000);
});

// --- DRAG AND DROP ---
const dropZone = document.querySelector('.upload-container');
if (dropZone) {
    ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
        document.body.addEventListener(eventName, (e) => {
            e.preventDefault(); e.stopPropagation();
        }, false);
    });

    ['dragenter', 'dragover'].forEach(evt => {
        dropZone.addEventListener(evt, () => {
            dropZone.style.borderColor = '#7f3cff';
            dropZone.style.background = 'rgba(127, 60, 255, 0.1)';
            dropZone.style.transform = 'scale(1.02)';
        });
    });

    ['dragleave', 'drop'].forEach(evt => {
        dropZone.addEventListener(evt, () => {
            dropZone.style.borderColor = '#333';
            dropZone.style.background = 'rgba(255,255,255,0.01)';
            dropZone.style.transform = 'scale(1)';
        });
    });

    dropZone.addEventListener('drop', (e) => {
        const files = e.dataTransfer.files;
        if (files.length > 0) {
            if (files[0].type.startsWith('audio/')) {
                initPlayer(files[0]);
            } else {
                alert('⚠️ Please drop an audio file (MP3, WAV, M4A)');
            }
        }
    });
}