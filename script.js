const audio = document.getElementById("audio");
const playBtn = document.getElementById("playBtn");
const bars = document.querySelectorAll(".waveform span");
const waveform = document.getElementById("waveform");
const fileNameDisplay = document.getElementById("fileNameDisplay");

// Containers
const uploadContainer = document.getElementById("uploadContainer");
const playerContainer = document.getElementById("playerContainer");
const loading = document.getElementById("loading");
const result = document.getElementById("result");

// Data Elements
const locationText = document.getElementById("locationText");
const situationText = document.getElementById("situationText");
const confidenceText = document.getElementById("confidenceText"); 
const evidenceText = document.getElementById("evidenceText");
const summaryText = document.getElementById("summaryText");
const transcribeText = document.getElementById("transcribeText");

// File Inputs
const audioUpload = document.getElementById("audioUpload");

let currentFile = null;

// --- 1. HANDLE FILE UPLOAD ---
audioUpload.addEventListener("change", function() {
    if (this.files.length > 0) {
        initPlayer(this.files[0]);
    }
});

function initPlayer(file) {
    console.log("File loaded:", file.name); // Debug
    currentFile = file;
    fileNameDisplay.textContent = file.name;
    const fileURL = URL.createObjectURL(file);
    audio.src = fileURL;

    uploadContainer.classList.add("hidden");
    playerContainer.classList.remove("hidden");
    result.classList.add("hidden");
    playBtn.innerHTML = '<i class="fa-solid fa-play"></i>';
}

// --- 2. PLAYER LOGIC & API TRIGGER ---
playBtn.addEventListener("click", () => {
    // 1. Trigger analysis immediately
    if (result.classList.contains("hidden")) {
        if (!currentFile) {
            alert("Error: No file selected. Please reload page and upload again.");
            return;
        }
        analyzeAudio(currentFile);
    }

    // 2. Handle Audio Playback
    if (audio.paused) {
        audio.play().then(() => {
            playBtn.innerHTML = '<i class="fa-solid fa-pause"></i>';
            waveform.classList.add("active");
            bars.forEach(bar => bar.style.animationPlayState = "running");
        }).catch(err => console.log("Audio play error:", err));
    } else {
        audio.pause();
        playBtn.innerHTML = '<i class="fa-solid fa-play"></i>';
        waveform.classList.remove("active");
        bars.forEach(bar => bar.style.animationPlayState = "paused");
    }
});

audio.addEventListener("ended", () => {
    playBtn.innerHTML = '<i class="fa-solid fa-play"></i>';
    waveform.classList.remove("active");
    bars.forEach(bar => bar.style.animationPlayState = "paused");
});

// --- 3. REAL API INTEGRATION ---
async function analyzeAudio(file) {
    // Show spinner
    loading.classList.remove("hidden");
    result.classList.add("hidden");
    
    const formData = new FormData();
    formData.append("file", file);

    try {
        // ALERT USER: STARTING
        console.log("Sending request to server...");

        const response = await fetch("http://127.0.0.1:8001/analyze", {
            method: "POST",
            body: formData
        });

        if (!response.ok) {
            throw new Error(`Server Error: ${response.status}`);
        }

        const data = await response.json();
        console.log("Success:", data);

        // Update UI
        locationText.textContent = data.location || "Unknown";
        situationText.textContent = data.situation || "Analyzing...";
        
        let conf = data.confidence;
        if (conf && conf < 1) conf = Math.round(conf * 100);
        confidenceText.textContent = conf ? conf + "%" : "--%";

        if (Array.isArray(data.evidence)) {
            evidenceText.textContent = data.evidence.join(", ");
        } else {
            evidenceText.textContent = data.evidence || "None";
        }

        summaryText.textContent = data.summary || "No summary";
        transcribeText.textContent = data.transcribe || "No transcription";

        loading.classList.add("hidden");
        result.classList.remove("hidden");

    } catch (error) {
        console.error(error);
        alert(`Connection Failed: ${error.message}\n\nMake sure terminal is running on Port 8001.`);
        loading.classList.add("hidden");
    }
}