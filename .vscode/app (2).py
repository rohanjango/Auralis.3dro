# ==============================
# 🛠️ SYSTEM SETUP (MUST BE FIRST)
# ==============================
import os
import shutil
import sys

# 1. HARDCODE THE FFMPEG PATH
FFMPEG_DIR = r"D:\photo\ffmpeg\ffmpeg-2026-01-07-git-af6a1dd0b2-full_build\bin"

# 2. Add to system PATH immediately
os.environ["PATH"] = FFMPEG_DIR + os.pathsep + os.environ.get("PATH", "")

# 3. Verify FFmpeg
if shutil.which("ffmpeg"):
    print(f"✅ FFmpeg found at: {shutil.which('ffmpeg')}")
else:
    print(f"❌ FFmpeg NOT found. Please check the path: {FFMPEG_DIR}")


# ==============================
# 📦 IMPORTS
# ==============================
from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
import librosa
import tensorflow as tf
import tensorflow_hub as hub
import numpy as np
import csv
import requests
from transformers import pipeline
from fastapi.responses import RedirectResponse
import sqlite3
from pydantic import BaseModel
import uuid

# ==============================
# 🚀 FASTAPI APP CREATE
# ==============================
app = FastAPI(title="Auralis API")

# ✅ FIX: Explicitly allow the exact URL you are using in the browser
origins = [
    "http://127.0.0.1:5500",
    "http://localhost:5500",
    "http://127.0.0.1:8000",
    "http://localhost:8000"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,       # TRUST THESE ADDRESSES
    allow_credentials=True,      
    allow_methods=["*"],         
    allow_headers=["*"],         
)

@app.get("/")
def root():
    return RedirectResponse(url= "/docs")

# ==============================
# 🤖 LOAD MODELS
# ==============================
print("⏳ Loading Whisper Model...")
whisper = pipeline("automatic-speech-recognition", model="openai/whisper-small")

print("⏳ Loading YAMNet Model...")
yamnet = hub.load("https://tfhub.dev/google/yamnet/1")

# Load YAMNet Labels
labels_url = "https://raw.githubusercontent.com/tensorflow/models/master/research/audioset/yamnet/yamnet_class_map.csv"
response = requests.get(labels_url)
labels = [] 
reader = csv.reader(response.text.splitlines())
next(reader) 
for row in reader:
    labels.append(row[2])

print("✅ Models Loaded Successfully")

# ==============================
# 🧠 HELPER FUNCTION
# ==============================
def analyze_logic(text, sounds):
    text = text.lower()
    sound_labels = [s.lower() for s in sounds.keys()]

    # Keywords
    airport_words = ["flight", "boarding", "gate", "airport"]
    rail_words = ["train", "platform", "coach"]
    emergency_words = ["help", "fire", "emergency","police","accident"]
    
    location = "Unknown"
    situation = "Unknown"
    evidence = []
    confidence = 0.3

    if any(w in text for w in airport_words):
        location = "Airport"
        situation = "Boarding"
        confidence = 0.85
    elif any(w in text for w in rail_words):
        location = "Railway Station"
        situation = "Transit"
        confidence = 0.8
    
    if any(w in text for w in emergency_words):
        situation = "Emergency"
        confidence = 0.95

    return {
        "location": location,
        "situation": situation,
        "confidence": confidence,
        "evidence": list(sounds.keys())[:3],
        "summary": f"Detected {situation} at {location}",
        "transcribed": text
    }

# ==============================
# 🌐 API ENDPOINT
# ==============================
@app.post("/analyze")
async def analyze(file: UploadFile = File(...)):
    print(f"\n📨 FILE RECEIVED: {file.filename}")
    
    # 1. SAVE TEMP FILE
    audio_bytes = await file.read()
    os.makedirs("uploads", exist_ok=True)
    temp_filename = f"uploads/{uuid.uuid4().hex}.wav"

    with open(temp_filename, "wb") as f:
        f.write(audio_bytes)
        f.flush()
        os.fsync(f.fileno())

    try:
        # 2. WHISPER
        try:
            whisper_result = whisper(temp_filename)
            text = whisper_result["text"]
        except:
            text = ""

        # 3. YAMNET
        wav_data, sr = librosa.load(temp_filename, sr=16000)
        wav_data = wav_data[:15*16000] # Trim
        scores, _, _ = yamnet(wav_data)
        mean_scores = np.mean(scores, axis=0)
        top_n = np.argsort(mean_scores)[::-1][:5]
        
        sounds = {}
        for i in top_n:
            sounds[labels[i]] = float(mean_scores[i]) # ✅ Float conversion fix

        # 4. INFERENCE
        result = analyze_logic(text, sounds)
        
        print(f"✅ RESULT: {result['location']} | {result['situation']}")
        return result

    except Exception as e:
        print(f"❌ ERROR: {e}")
        return {"error": str(e)}

    finally:
        if os.path.exists(temp_filename):
            os.remove(temp_filename)

# ==============================
# 🔐 DATABASE (Feature 5)
# ==============================
DB_NAME = "auralis_users.db"
def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS history (id INTEGER PRIMARY KEY, location TEXT, situation TEXT, transcription TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS users (email TEXT PRIMARY KEY, password TEXT)''')
    conn.commit()
    conn.close()
init_db()

class HistoryItem(BaseModel):
    timestamp: str
    location: str
    situation: str
    confidence: str
    soundType: str
    fileName: str
    transcription: str

class UserLogin(BaseModel):
    email: str
    password: str

@app.post("/save_history")
def save_history(item: HistoryItem):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("INSERT INTO history (location, situation, transcription) VALUES (?, ?, ?)", 
              (item.location, item.situation, item.transcription))
    conn.commit()
    conn.close()
    return {"status": "Saved"}

@app.post("/login")
def login(user: UserLogin):
    return {"token": "demo_token", "email": user.email}