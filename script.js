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

let currentFile = null;

// --- 1. HANDLE FILE UPLOAD ---
audioUpload.addEventListener("change", function() {
    if (this.files.length > 0) initPlayer(this.files[0]);
});

function initPlayer(file) {
    currentFile = file;
    fileNameDisplay.textContent = file.name;
    audio.src = URL.createObjectURL(file);
    uploadContainer.classList.add("hidden");
    playerContainer.classList.remove("hidden");
    result.classList.add("hidden");
    playBtn.innerHTML = '<i class="fa-solid fa-play"></i>';
}

// --- 2. PLAY BUTTON LOGIC ---
playBtn.addEventListener("click", () => {
    // A. Trigger Analysis
    if (result.classList.contains("hidden")) {
        if (!currentFile) return alert("Please upload a file first.");
        analyzeAudio(currentFile);
    }
    // B. Toggle Audio
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

// --- 3. ANALYSIS LOGIC (With Safety Checks) ---
async function analyzeAudio(file) {
    loading.classList.remove("hidden");
    result.classList.add("hidden");
    
    const formData = new FormData();
    formData.append("file", file);

    try {
        console.log("Sending to server...");
        // Ensure Port is 8001
        const response = await fetch("http://127.0.0.1:8001/analyze", {
            method: "POST",
            body: formData
        });

        if (!response.ok) throw new Error(`Server Error: ${response.status}`);

        const data = await response.json();
        console.log("Success:", data);

        // --- SAFETY CHECK: Find Elements Just-In-Time ---
        const els = {
            loc: document.getElementById("locationText"),
            sit: document.getElementById("situationText"),
            conf: document.getElementById("confidenceText"),
            evi: document.getElementById("evidenceText"),
            sum: document.getElementById("summaryText"),
            tran: document.getElementById("transcribeText")
        };

        // If elements are missing, alert user to fix HTML
        if (!els.evi || !els.sum || !els.tran) {
            alert("CRITICAL ERROR: HTML Elements are missing!\nPlease SAVE your index.html file and Refresh.");
            loading.classList.add("hidden");
            return;
        }

        // Fill Data
        els.loc.textContent = data.location || "Unknown";
        els.sit.textContent = data.situation || "Analyzing...";
        
        let conf = data.confidence;
        if (conf && conf < 1) conf = Math.round(conf * 100);
        els.conf.textContent = conf ? conf + "%" : "--%";

        els.evi.textContent = Array.isArray(data.evidence) ? data.evidence.join(", ") : (data.evidence || "None");
        els.sum.textContent = data.summary || "No summary";
        els.tran.textContent = data.transcribe || "No transcription";

        loading.classList.add("hidden");
        result.classList.remove("hidden");

    } catch (error) {
        console.error(error);
        alert(`Connection Error: ${error.message}\nCheck Terminal Port (8001).`);
        loading.classList.add("hidden");
    }
}