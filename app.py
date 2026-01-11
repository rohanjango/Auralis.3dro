# ==============================
# 📦 IMPORTS
# ==============================
from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse, JSONResponse, Response
import tensorflow as tf
import tensorflow_hub as hub
import numpy as np
import csv
import requests
from transformers import pipeline
import librosa  # ✅ This handles ALL audio formats (no FFmpeg needed)
import os
import shutil
import subprocess
import os

# ==============================
# 🎬 FFMPEG DETECTION + PATH FIX
# ==============================

FFMPEG_BIN_DIR = r"D:\photo\ffmpeg\ffmpeg-2026-01-07-git-af6a1dd0b2-full_build\bin"

def ensure_ffmpeg_available():
    """
    Ensures FFmpeg is available for Whisper/Librosa.
    - If ffmpeg is already in PATH: ok
    - Else: add FFMPEG_BIN_DIR to PATH
    - Prints clear debug output
    """

    # Check if ffmpeg is already available
    existing = shutil.which("ffmpeg")
    if existing:
        print(f"✅ FFmpeg already available: {existing}")
        return True

    # Add your FFmpeg folder to PATH if it exists
    if os.path.isdir(FFMPEG_BIN_DIR):
        os.environ["PATH"] = FFMPEG_BIN_DIR + os.pathsep + os.environ.get("PATH", "")
        found = shutil.which("ffmpeg")

        if found:
            print(f"✅ FFmpeg enabled (added to PATH): {found}")

            # Optional: print version to confirm everything works
            try:
                ver = subprocess.check_output(["ffmpeg", "-version"], text=True).splitlines()[0]
                print("✅", ver)
            except Exception as e:
                print("⚠️ FFmpeg detected but version check failed:", e)

            return True

        print("❌ FFmpeg folder exists but ffmpeg still not detected.")
        print("   Make sure ffmpeg.exe is inside:")
        print(f"   {FFMPEG_BIN_DIR}")
        return False

    print("❌ FFmpeg bin folder not found:", FFMPEG_BIN_DIR)
    return False


# Run FFmpeg detection ON SERVER STARTUP
ensure_ffmpeg_available()

# ==============================
# 🚀 FASTAPI APP CREATE
# ==============================
app = FastAPI(title="Auralis API")

# ✅ CRITICAL FIX: Proper CORS for Edge/Chrome
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins
    allow_credentials=False,  # Must be False when using "*"
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"]  # ✅ Added: Exposes all headers to frontend
)

# Root redirect to docs
@app.get("/")
def root():
    return RedirectResponse(url="/docs")

# ✅ FIX: Favicon handler (stops 404 errors)
@app.get("/favicon.ico")
async def favicon():
    return Response(content=b"", media_type="image/x-icon", status_code=200)

# ==============================
# 🤖 LOAD MODELS
# ==============================
print("\n" + "="*50)
print("🔄 Loading AI Models...")
print("="*50)

try:
    whisper = pipeline("automatic-speech-recognition", model="openai/whisper-small")
    print("✅ Whisper loaded!")
except Exception as e:
    print(f"⚠️ Whisper Warning: {e}")
    whisper = None

yamnet = hub.load("https://tfhub.dev/google/yamnet/1")
print("✅ YAMNet loaded!")

# ==============================
# 🏷️ YAMNet LABELS
# ==============================
labels_url = "https://raw.githubusercontent.com/tensorflow/models/master/research/audioset/yamnet/yamnet_class_map.csv"
response = requests.get(labels_url)
labels = []
reader = csv.reader(response.text.splitlines())
next(reader)
for row in reader:
    labels.append(row[2])

print(f"✅ Loaded {len(labels)} sound labels")
print("="*50)
print("🚀 SERVER READY - Waiting for requests...")
print("="*50 + "\n")

# ==============================
# 🧠 INFERENCE ENGINE
# ==============================
def analyze_audio(text, sounds):
    text = text.lower()
    sound_labels = [s.lower() for s in sounds.keys()]

    airport_words = ["flight", "boarding", "gate", "airport"]
    rail_words = ["train", "platform", "coach"]
    emergency_words = ["help", "fire", "emergency", "police", "accident"]
    emergency_sounds = ["siren", "scream", "alarm", "glass", "shouting"]
    public_sounds = ["crowd", "conversation"]
    vehicle_sounds = ["vehicle", "engine", "traffic", "horn"]

    location = "Unknown"
    situation = "Unknown"
    evidence = []
    confidence = 0.3

    is_emergency_text = any(w in text for w in emergency_words)
    is_emergency_sound = any(any(es in s for es in emergency_sounds) for s in sound_labels)

    if any(w in text for w in airport_words) and any(s in sound_labels for s in public_sounds):
        location = "Airport"
        situation = "Boarding"
        evidence += ["Flight-related speech", "Public crowd sounds"]
        confidence = 0.85
    elif any(w in text for w in rail_words) and any(s in sound_labels for s in public_sounds):
        location = "Railway Station"
        situation = "Waiting / Boarding"
        evidence += ["Train-related speech", "Crowd sounds"]
        confidence = 0.8
    elif any(s in sound_labels for s in vehicle_sounds):
        location = "Road"
        situation = "Traffic"
        evidence += ["Vehicle sounds detected"]
        confidence = 0.7

    if any(w in text for w in emergency_words):
        situation = "Emergency"
        evidence.append("Emergency keywords detected")
        confidence = max(confidence, 0.9)

    if is_emergency_text or is_emergency_sound:
        return {
            "location": location,
            "situation": "Emergency",
            "confidence": 0.95,
            "evidence": sound_labels[:3],
            "summary": "Emergency situation detected based on distress signals in the audio.",
            "transcribed": text
        }
    
    summary = f"This audio likely comes from a {location.lower()} during {situation.lower()}, inferred from {' '.join(evidence)} with a confidence of {confidence}."
    return {
        "location": location,
        "situation": situation,
        "confidence": round(confidence, 2),
        "evidence": evidence[:3] if evidence else ["General audio"],
        "summary": summary,
        "transcribed": text
    }

# ==============================
# 🌐 API ENDPOINT
# ==============================
@app.post("/analyze")
async def analyze(file: UploadFile = File(...)):
    print("\n" + "="*60)
    print(f"📥 RECEIVED: {file.filename}")
    print("="*60)

    temp_filename = f"temp_{file.filename}"

    try:
        # Save uploaded file
        contents = await file.read()
        with open(temp_filename, "wb") as f:
            f.write(contents)
        print(f"💾 Saved: {temp_filename}")

        # ✅ TRANSCRIBE (Whisper handles all formats internally)
        print("🎤 Transcribing...")
        text = "Speech unclear"
        if whisper:
            try:
                result = whisper(temp_filename)
                text = result["text"]
                print(f"📝 TEXT: '{text}'")
            except Exception as e:
                print(f"⚠️ Whisper error: {e}")

        # ✅ LOAD AUDIO (Librosa handles MP3, M4A, WAV, MP4 automatically)
        print("🔊 Loading audio...")
        try:
            # sr=16000 forces 16kHz, mono=True forces mono
            audio, sr = librosa.load(temp_filename, sr=16000, mono=True)
            duration = len(audio) / sr
            print(f"⏱️ Duration: {duration:.2f}s")
            print(f"🎵 Audio shape: {audio.shape}, Sample rate: {sr}Hz")
        except Exception as e:
            print(f"❌ Load failed: {e}")
            return JSONResponse(
                status_code=500,
                content={"error": f"Could not load audio: {str(e)}"}
            )

        # ✅ ANALYZE WITH YAMNET
        print("🤖 Running YAMNet...")
        try:
            scores, _, _ = yamnet(audio)
            mean_scores = tf.reduce_mean(scores, axis=0).numpy()
            top_indices = np.argsort(mean_scores)[-10:][::-1]

            raw_sounds = {}
            for i in top_indices:
                raw_sounds[labels[i]] = float(mean_scores[i])

            print(f"🔊 TOP SOUNDS: {list(raw_sounds.keys())[:3]}")

        except Exception as e:
            print(f"❌ YAMNet failed: {e}")
            return JSONResponse(
                status_code=500,
                content={"error": f"Analysis failed: {str(e)}"}
            )

        # Filter sounds
        keywords = ["speech", "conversation", "crowd", "vehicle", "engine", "traffic", "aircraft", "siren", "alarm"]
        sounds = {k: v for k, v in raw_sounds.items() if any(x in k.lower() for x in keywords)}
        
        if not sounds:
            sounds = raw_sounds

        # Final analysis
        print("🧠 Running inference...")
        result = analyze_audio(text, sounds)
        
        print(f"✅ RESULT:")
        print(f"   📍 Location: {result['location']}")
        print(f"   🎯 Situation: {result['situation']}")
        print(f"   📊 Confidence: {result['confidence']*100:.0f}%")
        print("="*60 + "\n")
        
        return JSONResponse(content=result)

    except Exception as e:
        print(f"💥 CRITICAL ERROR: {e}")
        import traceback
        traceback.print_exc()
        return JSONResponse(
            status_code=500,
            content={"error": f"Server error: {str(e)}"}
        )

    finally:
        # Cleanup
        if os.path.exists(temp_filename):
            try:
                os.remove(temp_filename)
                print(f"🗑️ Cleaned: {temp_filename}")
            except:
                pass

# ✅ NEW CODE BLOCK: This runs the server when you execute 'python app.py'
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)