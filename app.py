# ==============================
# 📦 IMPORTS — Tools uthaa raha hu
# ==============================
import os
import shutil
import subprocess

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
# 📡 FASTAPI + ML IMPORTS
# FastAPI → backend banane ka framework
# UploadFile, File → frontend se audio file lene ke liye
from fastapi import FastAPI, UploadFile, File

# librosa → audio ko numbers (waveform) me convert karta hai
import librosa

# TensorFlow + Hub → YAMNet model chalane ke liye
import tensorflow as tf
import tensorflow_hub as hub

# numpy → numbers ke saath kaam (sorting, arrays)
import numpy as np

# csv + requests → YAMNet ke sound labels internet se laane ke liye
import csv
import requests

# transformers pipeline → Whisper speech-to-text ke liye
from transformers import pipeline

#for directing port output url "/docs"
from fastapi.responses import RedirectResponse

# ==============================
# 🚀 FASTAPI APP CREATE
# ==============================

# Ye hamara backend app hai
# Iska naam Auralis
app = FastAPI(title="Auralis API")

#cors

from fastapi.middleware.cors import CORSMiddleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

#redirecting port url for which imported at ln27
@app.get("/")
def root():
    return RedirectResponse(url= "/docs")

#CORS ==== added on 9th jan ,2026 ; 7:40 p.m. ====
#from fastapi.middleware.cors import CORSMiddleware

#app.add_middleware(
#    CORSMiddleware,
 #   allow_origins=["*"],
 #   allow_credentials=True,
 #   allow_methods=["*"],
 #   allow_headers=["*"],
#)


# Whisper model load ho raha hai
# Ye audio sunke bataata hai "kya bola gaya"
# NOTE: Isko function ke andar nahi rakhte
# Kyunki har request pe load hua → slow ho jayega
whisper = pipeline(
    "automatic-speech-recognition",
    model="openai/whisper-small"
)

# YAMNet model load ho raha hai
# Ye audio sunke batata hai "kaunsi awaaz hai"
yamnet = hub.load("https://tfhub.dev/google/yamnet/1")


# ==============================
# 🏷️ YAMNet KE LABELS LOAD
# ==============================

# YAMNet sirf numbers deta hai
# Un numbers ka matlab (Conversation, Crowd, etc.)
# is CSV file me hota hai

labels_url = "https://raw.githubusercontent.com/tensorflow/models/master/research/audioset/yamnet/yamnet_class_map.csv"
response = requests.get(labels_url)

labels = []  # isme saare sound labels store honge

reader = csv.reader(response.text.splitlines())
next(reader)  # first row header hoti hai, isliye skip

# Har row me ek sound label hota hai
for row in reader:
    labels.append(row[2])  # actual label name


# ==============================
# 🧠 INFERENCE ENGINE (DIMAG)
# ==============================

# Ye function sabse important hai
# Isme "intelligence" hai
# ML yahan nahi, logic yahan hai

def analyze_audio(text, sounds):

    # Text ko lower-case me convert
    # Taaki Flight / flight ka issue na aaye
    text = text.lower()

    # Sound dictionary ke keys ko bhi lower-case me le aate hain
    sound_labels = [s.lower() for s in sounds.keys()]

    # ---------- KEYWORDS (COMMON SENSE) ----------

    # Agar text me yeh words aaye → airport related
    airport_words = ["flight", "boarding", "gate", "airport"]

    # Railway ke liye
    rail_words = ["train", "platform", "coach"]

    # Emergency ke liye
    emergency_words = ["help", "fire", "emergency","police","accident",]
    emergency_sounds = ["siren","scream","alarm","glass","shouting"]

    # Public jagah ki awaazein
    public_sounds = ["crowd", "conversation"]

    # Road / traffic ki awaazein
    vehicle_sounds = ["vehicle", "engine", "traffic", "horn"]

    # ---------- DEFAULT OUTPUT ----------
    # Agar kuch samajh na aaye to bhi system tootega nahi

    location = "Unknown"
    situation = "Unknown"
    evidence = []          
    confidence = 0.3       # default low confidence
    summary = "none"
    
    # ---------- AIRPORT RULE ----------
    # Agar text me flight related baat
    # aur sound me crowd / conversation
    # to most probably airport

    # -------EMERGENCY SOUNDS--------
    is_emergency_text = any(w in text for w in emergency_words)
    is_emergency_sound = any(
        any(es in s for es in emergency_sounds) for s in sound_labels
    )

    if any(w in text for w in airport_words) and any(s in sound_labels for s in public_sounds):
        location = "Airport"
        situation = "Boarding"
        evidence += ["Flight-related speech", "Public crowd sounds"]
        confidence = 0.85

    # ---------- RAILWAY RULE ----------
    elif any(w in text for w in rail_words) and any(s in sound_labels for s in public_sounds):
        location = "Railway Station"
        situation = "Waiting / Boarding"
        evidence += ["Train-related speech", "Crowd sounds"]
        confidence = 0.8

    # ---------- ROAD / TRAFFIC RULE ----------
    elif any(s in sound_labels for s in vehicle_sounds):
        location = "Road"
        situation = "Traffic"
        evidence += ["Vehicle sounds detected"]
        confidence = 0.7

    # ---------- EMERGENCY OVERRIDE ----------
    # Emergency hamesha upar priority pe
    # Chahe location kuch bhi ho

    if any(w in text for w in emergency_words):
        situation = "Emergency"
        evidence.append("Emergency keywords detected")
        confidence = max(confidence, 0.9)

    # ---------- FINAL RESULT ----------
    # Backend se frontend ko yahi JSON milega
    if is_emergency_text or is_emergency_sound:
        return {
            
            "location": location,
            "situation": "Emergency",
            "confidence": 0.95,
            "confidence_reason": "High confidence due to presence of emergency keywords or sounds.",
            "evidence": sound_labels,
            "summary": "Emergency situation detected based on distress signals in the audio.",
            "transcribed": text
        }
    summary = f"This audio likely comes from a {location.lower()} during {situation.lower()}, inferred from {' '.join(evidence)} with a confidence of {confidence}."
    return {
        "location": location,
        "situation": situation,
        "confidence": round(confidence, 2),
        "evidence": evidence,
        "summary": summary,
        "transcribed": text
    }


# ==============================
# 🌐 API ENDPOINT (/analyze)
# ==============================

# Ye endpoint frontend call karega
# Audio file upload karega
# Aur JSON result wapas milega

@app.post("/analyze")
async def analyze(file: UploadFile = File(...)):
    #checking who fails backend or frontend
    print("file received", file.filename)

    # Frontend se aayi audio file bytes me hoti hai
    audio_bytes = await file.read()

    # Usko temporary WAV file bana dete hain
    # Taaki Whisper aur librosa use kar sake
   
    #filename=file.filename
    #with open(filename, "wb") as f:
    #    f.write(audio_bytes)

    import uuid
    import os

    os.makedirs("uploads", exist_ok=True)

    unique_id = uuid.uuid4().hex
    temp_audio_path = f"uploads/{unique_id}.wav"

    with open(temp_audio_path, "wb") as f:
        f.write(audio_bytes)
        f.flush()
        os.fsync(f.fileno())

    # ---------- WHISPER ----------
    # Audio → Text
    try:
        whisper_result = whisper(
            temp_audio_path,
            chunk_length_s=15,
            stride_length_s=5,
            return_timestamps=False,
            language="en" # English me transcription
        )
        text = whisper_result["text"]

        # ---------- LOAD AUDIO ----------
        # WAV file → numbers (waveform)
        audio, _ = librosa.load(temp_audio_path, sr=16000)
        duration = librosa.get_duration(y=audio, sr=16000)
        MAX_SECONDS = 15 # YAMNet ka limit hai 15 seconds here 
        audio = audio[: MAX_SECONDS * 16000]

         # ---------- YAMNet ----------
        # Audio → sound probabilities
        scores, _, _ = yamnet(audio)

        # Har sound ka average confidence
        mean_scores = tf.reduce_mean(scores, axis=0).numpy()

        # Top 10 sabse strong sounds
        top_indices = np.argsort(mean_scores)[-10:][::-1]

        raw_sounds = {}
        for i in top_indices:
            raw_sounds[labels[i]] = float(mean_scores[i])

        # ---------- FILTER IMPORTANT SOUNDS ----------
        # 500+ sounds me se sirf kaam ke sounds rakhte hain
        keywords = [
            "speech", "conversation", "crowd",
            "vehicle", "engine", "traffic",
            "aircraft", "siren"
        ]

        sounds = {
            k: v for k, v in raw_sounds.items()
            if any(x in k.lower() for x in keywords)
        }

        #"/" se /docs me khulne k liye 
        def home():
            return{
                "status": "Auralis API running",
                "docs": "/docs"
            }
    
        # ---------- FINAL INFERENCE ----------
        # Ab text + sounds ko dimag me bhejte hain
        return analyze_audio(text, sounds)
    
    # ---------- ERROR HANDLING ----------
    except Exception as e:
        return {
            "location": "Unknown",
            "situation": "Unknown",
            "confidence": 0.0,
            "evidence": [],
            "summary": "Error processing audio.",
            "transcribed": "",
            "error": str(e)
        }


    finally:
        # Temporary file delete 
        try:
            os.remove(temp_audio_path)
        except Exception as et:
            print(f"Error deleting temporary file: {et}")
    