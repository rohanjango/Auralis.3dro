# ==============================
# 🎬 Auralis Backend (FastAPI)
# ✅ Fixes:
#   1) Stable /analyze endpoint
#   2) Correct temp file extension
#   3) Optional FFmpeg conversion to WAV for whisper/YAMNet consistency
#   4) Better error messages for frontend
# ==============================

from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import os
import uuid
import shutil
import subprocess
import traceback

import numpy as np

# ==============================
# ✅ Optional FFmpeg helper
# ==============================
def ffmpeg_available() -> bool:
    return shutil.which("ffmpeg") is not None

def convert_to_wav_ffmpeg(input_path: str, output_path: str) -> None:
    """
    Convert audio to mono 16k WAV for stable Whisper + YAMNet.
    Requires ffmpeg installed and available in PATH.
    """
    subprocess.run(
        ["ffmpeg", "-y", "-i", input_path, "-ac", "1", "-ar", "16000", output_path],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )

# ==============================
# ✅ FastAPI setup
# ==============================
app = FastAPI(title="Auralis API", version="1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],       # Dev mode
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==============================
# ✅ Model loading (YAMNet)
# ==============================
import tensorflow as tf
import tensorflow_hub as hub
import librosa

# YAMNet model
yamnet_model = hub.load("https://tfhub.dev/google/yamnet/1")
class_map_path = yamnet_model.class_map_path().numpy().decode("utf-8")

# Load class names
class_names = []
with open(class_map_path, "r", encoding="utf-8") as f:
    next(f)
    for line in f:
        class_names.append(line.strip().split(",")[2].strip('"'))

# Whisper (transformers pipeline)
from transformers import pipeline
whisper = pipeline("automatic-speech-recognition", model="openai/whisper-base")

# ==============================
# ✅ Sound logic
# ==============================
vehicle_sounds = {"Car", "Vehicle", "Bus", "Truck", "Motorcycle", "Train", "Traffic", "Engine", "Siren"}
public_sounds  = {"Crowd", "Conversation", "Speech", "Narration", "Monologue", "Walk", "Footsteps", "Airport", "Station"}

def analyze_logic(sound_labels):
    """
    Decide location & situation based on top detected sounds.
    Uses partial matching to be more flexible.
    """
    lower = [s.lower() for s in sound_labels]

    def has_any(words):
        return any(any(w.lower() in s for w in words) for s in lower)

    if has_any(vehicle_sounds):
        return "Road / Vehicle Area", "Possible traffic / vehicle movement detected."
    elif has_any(public_sounds):
        return "Public Place", "People/crowd voices detected. Likely a public environment."
    else:
        return "Unknown", "No strong environmental sounds detected."

# ==============================
# ✅ Main Analyze API
# ==============================
@app.post("/analyze")
async def analyze(file: UploadFile = File(...)):
    if not file or not file.filename:
        return JSONResponse(status_code=400, content={"error": "No file uploaded."})

    unique_id = str(uuid.uuid4())

    # ✅ preserve extension (important)
    ext = os.path.splitext(file.filename)[1].lower()
    if not ext:
        ext = ".wav"  # fallback

    temp_path = f"temp_{unique_id}{ext}"
    converted_path = f"temp_{unique_id}_converted.wav"

    try:
        # Save upload
        with open(temp_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        print(f"📥 FILE RECEIVED: {file.filename}")
        print(f"💾 Saved temporary file: {temp_path}")

        # ✅ convert to stable wav if ffmpeg exists
        audio_path_for_models = temp_path
        if ext != ".wav" and ffmpeg_available():
            try:
                convert_to_wav_ffmpeg(temp_path, converted_path)
                audio_path_for_models = converted_path
                print("✅ Converted to WAV using FFmpeg.")
            except Exception:
                print("⚠️ FFmpeg conversion failed. Continuing with original file.")

        # ==============================
        # 🎧 Load audio
        # ==============================
        waveform, sr = librosa.load(audio_path_for_models, sr=16000, mono=True)
        duration = float(len(waveform) / sr)
        print(f"⏱️ DURATION: {duration:.2f} seconds")

        # ==============================
        # 🔊 YAMNet inference
        # ==============================
        scores, embeddings, spectrogram = yamnet_model(waveform)
        mean_scores = tf.reduce_mean(scores, axis=0).numpy()
        top_indices = np.argsort(mean_scores)[::-1][:3]

        top_sounds = [class_names[i] for i in top_indices]
        top_scores = [float(mean_scores[i]) for i in top_indices]

        evidence = top_sounds
        confidence = min(0.95, 0.35 + top_scores[0])  # simple stable confidence mapping

        print("🏷️ TOP 3 SOUNDS:", top_sounds)

        # ==============================
        # 🧠 Logic decision
        # ==============================
        location, situation = analyze_logic(top_sounds)

        # ==============================
        # 🗣️ Transcription (Whisper)
        # ==============================
        transcription = ""
        summary = ""

        try:
            transcript = whisper(audio_path_for_models)
            transcription = transcript.get("text", "").strip()
            summary = transcription[:180] + ("..." if len(transcription) > 180 else "")
            print("📝 TRANSCRIBED:", transcription[:120])
        except Exception as e:
            print("⚠️ Whisper failed:", e)
            transcription = ""
            summary = "Transcription unavailable (Whisper failed)."

        return {
            "location": location,
            "situation": situation,
            "confidence": float(confidence),
            "evidence": evidence,
            "summary": summary,
            "transcribed": transcription
        }

    except Exception as e:
        print("❌ Analyze error:", e)
        traceback.print_exc()
        return JSONResponse(
            status_code=500,
            content={"error": f"Server error while analyzing audio: {str(e)}"}
        )

    finally:
        # cleanup
        for p in [temp_path, converted_path]:
            try:
                if os.path.exists(p):
                    os.remove(p)
                    print(f"🧹 Cleaned up: {p}")
            except Exception:
                pass

# ==============================
# ✅ Health check
# ==============================
@app.get("/")
def root():
    return {"status": "ok", "message": "Auralis backend running"}

# ==============================
# ✅ Run: python app.py
# ==============================
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="127.0.0.1", port=8000, reload=True)
