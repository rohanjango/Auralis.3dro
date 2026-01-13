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

// --- RECORDING VARIABLES ---
const recordBtn = document.getElementById("recordBtn");
const recordStatus = document.getElementById("recordStatus");
const recordTimer = document.getElementById("recordTimer");

let currentFile = null;
let alreadyAnalyzed = false;
let currentAnalysisData = null;
let mediaRecorder;
let audioChunks = [];
let recordTimerInterval;

// ✅ CORRECT API URL
const API_URL = "https://ideal-space-funicular-69pj75q9r6rvcr7qw-8000.app.github.dev/analyze";

// --- FILE UPLOAD HANDLER ---
audioUpload.addEventListener("change", function() {
    if (this.files.length > 0) {
        initPlayer(this.files[0]);
    }
});

// --- RECORDING LOGIC ---
if(recordBtn) {
    recordBtn.addEventListener("click", async () => {
        if (!mediaRecorder || mediaRecorder.state === "inactive") {
            // START RECORDING
            try {
                const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
                mediaRecorder = new MediaRecorder(stream);
                mediaRecorder.start();
                
                // Reset chunks
                audioChunks = [];
                
                // UI Updates
                recordBtn.innerHTML = '<i class="fa-solid fa-stop"></i> Stop';
                recordBtn.style.background = "#ff0000"; // Red
                recordStatus.classList.remove("hidden");
                
                // Timer
                let seconds = 0;
                recordTimerInterval = setInterval(() => {
                    seconds++;
                    const mins = Math.floor(seconds/60).toString().padStart(2,'0');
                    const secs = (seconds%60).toString().padStart(2,'0');
                    recordTimer.textContent = `${mins}:${secs}`;
                }, 1000);

                // Collect Data
                mediaRecorder.addEventListener("dataavailable", e => audioChunks.push(e.data));
                
                // STOP EVENT
                mediaRecorder.addEventListener("stop", () => {
                    clearInterval(recordTimerInterval);
                    
                    const audioBlob = new Blob(audioChunks, { type: 'audio/wav' });
                    const audioFile = new File([audioBlob], "mic_recording.wav", { type: "audio/wav" });
                    
                    // Reset UI
                    recordBtn.innerHTML = '<i class="fa-solid fa-microphone"></i> Record Now';
                    recordBtn.style.background = "#ff4757";
                    recordStatus.classList.add("hidden");
                    recordTimer.textContent = "00:00";
                    
                    // Process File
                    initPlayer(audioFile);
                    analyzeAudio(audioFile);
                });
            } catch (err) {
                alert("Microphone access denied. Please check browser permissions.");
                console.error(err);
            }
        } else {
            // STOP RECORDING
            mediaRecorder.stop();
        }
    });
}

// --- PLAYER INITIALIZATION ---
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

// --- ANALYSIS FUNCTION (Fixed) ---
async function analyzeAudio(file) {
    loading.classList.remove("hidden");
    result.classList.add("hidden");

    try {
        console.log(`🔄 Sending to API: ${API_URL}`);
        const formData = new FormData();
        formData.append("file", file);

        // ✅ STANDARD FETCH (Solves CORS if backend is correct)
        const response = await fetch(API_URL, {
            method: "POST",
            body: formData
        });

        if (!response.ok) {
            const txt = await response.text();
            throw new Error(`HTTP ${response.status}: ${txt}`);
        }

        const data = await response.json();
        console.log("✅ Success:", data);

        if (data.error) throw new Error(data.error);

        currentAnalysisData = data;
        
        // Update UI
        document.getElementById("locationText").textContent = data.location || "Unknown";
        document.getElementById("situationText").textContent = data.situation || "Unknown";
        
        let conf = data.confidence;
        if (typeof conf === "number") {
             conf = conf <= 1 ? Math.round(conf * 100) : Math.round(conf);
             document.getElementById("confidenceText").textContent = conf + "%";
        }

        document.getElementById("evidenceText").textContent = Array.isArray(data.evidence) ? data.evidence.join(", ") : "None";
        document.getElementById("summaryText").textContent = data.summary || "No summary";
        document.getElementById("transcribeText").textContent = data.transcribed || "No transcription";

        loading.classList.add("hidden");
        result.classList.remove("hidden");

    } catch (error) {
        console.warn(`❌ Failed:`, error);
        loading.classList.add("hidden");
        alert(
            "🚨 Backend Connection Failed!\n\n" +
            "1) Ensure backend is running:\n" +
            "   py -m uvicorn app:app --reload --host 127.0.0.1 --port 8000\n\n" +
            "2) Ensure you are on: http://127.0.0.1:5500\n\n" +
            "Error: " + error.message
        );
    }
}

// --- TIME DISPLAY & PLAY BTN ---
audio.addEventListener("timeupdate", () => {
    const fmt = s => {
        if(isNaN(s)) return "00:00";
        let m = Math.floor(s/60).toString().padStart(2,'0');
        let sc = Math.floor(s%60).toString().padStart(2,'0');
        return `${m}:${sc}`;
    };
    timeDisplay.textContent = `${fmt(audio.currentTime)} / ${fmt(audio.duration)}`;
});

playBtn.addEventListener("click", async () => {
    if (!currentFile) return alert("Upload first");
    
    if (!alreadyAnalyzed) {
        await analyzeAudio(currentFile);
        alreadyAnalyzed = true;
    }

    if (audio.paused) {
        audio.play();
        playBtn.innerHTML = '<i class="fa-solid fa-pause"></i>';
        waveform.classList.add("active");
    } else {
        audio.pause();
        playBtn.innerHTML = '<i class="fa-solid fa-play"></i>';
        waveform.classList.remove("active");
    }
});

// --- SAVE TO DASHBOARD ---
saveBtn.addEventListener("click", function() {
    if (!currentAnalysisData) return;

    const item = {
        timestamp: new Date().toLocaleString(),
        location: currentAnalysisData.location,
        situation: currentAnalysisData.situation,
        confidence: document.getElementById("confidenceText").textContent,
        soundType: Array.isArray(currentAnalysisData.evidence) ? currentAnalysisData.evidence[0] : "Audio",
        fileName: currentFile.name,
        transcription: currentAnalysisData.transcribed || ""
    };

    let history = JSON.parse(localStorage.getItem("auralisHistory")) || [];
    history.unshift(item);
    localStorage.setItem("auralisHistory", JSON.stringify(history.slice(0,50)));

    // Cloud Save (Try/Catch wrapper so it doesn't alert on failure)
    fetch("http://127.0.0.1:8000/save_history", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify(item)
    }).catch(e => console.log("Cloud save skipped"));

    saveBtn.innerHTML = '<i class="fa-solid fa-check"></i> Saved!';
    saveBtn.style.background = "#28a745";
    setTimeout(() => {
        saveBtn.innerHTML = '<i class="fa-solid fa-floppy-disk"></i> Save Analysis to Dashboard';
        saveBtn.style.background = "";
    }, 2000);
});

// --- DRAG & DROP ---
const dropZone = document.querySelector('.upload-container');
if (dropZone) {
    dropZone.addEventListener('dragover', e => {
        e.preventDefault();
        dropZone.style.borderColor = '#7f3cff';
        dropZone.style.background = 'rgba(127, 60, 255, 0.1)';
    });
    dropZone.addEventListener('dragleave', e => {
        e.preventDefault();
        dropZone.style.borderColor = '#333';
        dropZone.style.background = 'rgba(255,255,255,0.01)';
    });
    dropZone.addEventListener('drop', e => {
        e.preventDefault();
        dropZone.style.borderColor = '#333';
        dropZone.style.background = 'rgba(255,255,255,0.01)';
        const files = Array.from(e.dataTransfer.files).filter(f => f.type.startsWith('audio/'));
        if (files.length > 0) initPlayer(files[0]);
    });
}