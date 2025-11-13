from flask import Flask, render_template, request, jsonify, redirect, url_for, session
import os
from datetime import datetime
from werkzeug.utils import secure_filename
import subprocess
import time

# ---------------------- AI MODULE IMPORTS ----------------------
from ai_module.voice_analyzer import analyze_voice
from ai_module.tts import say_text_to_file
from ai_module.llm_engine import generate_interview_question

# ---------------------- CONFIG ----------------------
app = Flask(__name__)
UPLOAD_FOLDER = "static/uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

ALLOWED_EXT = {"wav", "webm", "mp3", "ogg", "m4a", "flac"}
app.secret_key = "intelx_secret_key"

# ---------------------- PRE-GENERATE AI GREETING ----------------------
PREGENERATED_GREETING_PATH = os.path.join(UPLOAD_FOLDER, "inteleX_greeting_cached.wav")

if not os.path.exists(PREGENERATED_GREETING_PATH):
    try:
        print("🎙️ Pre-generating InteleX greeting voice...")
        say_text_to_file(
            "Hello Candidate. Please stay calm and follow the AI instructions carefully. "
            "Read the displayed paragraph clearly when instructed.",
            filename="inteleX_greeting_cached.wav"
        )
        print(f"✅ Greeting voice cached successfully at {PREGENERATED_GREETING_PATH}")
    except Exception as e:
        print(f"⚠️ Greeting pre-generation failed: {e}")
else:
    print(f"✅ Cached greeting already exists at {PREGENERATED_GREETING_PATH}")

# ---------------------- HELPERS ----------------------
def allowed(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXT

def timestamped_filename(filename):
    name = secure_filename(filename)
    base, ext = os.path.splitext(name)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"{base}_{ts}{ext}"

def convert_to_wav(input_path):
    """Converts any audio file to WAV using ffmpeg."""
    base = os.path.splitext(os.path.basename(input_path))[0]
    wav_path = os.path.join(UPLOAD_FOLDER, f"{base}.wav")
    try:
        cmd = ["ffmpeg", "-y", "-i", input_path, "-ar", "22050", "-ac", "1", wav_path]
        subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if os.path.exists(wav_path):
            print(f"✅ Converted {input_path} -> {wav_path}")
            return wav_path
        else:
            print("⚠️ Conversion failed.")
            return input_path
    except Exception as e:
        print("❌ FFmpeg error:", e)
        return input_path

# ---------------------- ROUTES ----------------------

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        return redirect(url_for("resume"))
    return render_template("register.html")

@app.route("/resume", methods=["GET", "POST"])
def resume():
    if request.method == "POST":
        resume_file = request.files.get("resume")
        user_name = request.form.get("name", "Candidate")

        # Store name in session
        session["user_name"] = user_name
        app.logger.info(f"🧍 Candidate Name: {user_name}")

        if not resume_file or resume_file.filename == "":
            return render_template("resume.html", error="Please upload your resume.")

        filename = timestamped_filename(resume_file.filename)
        save_path = os.path.join(UPLOAD_FOLDER, filename)
        resume_file.save(save_path)
        return redirect(url_for("interview"))
    return render_template("resume.html")

# ---------------------- INTERVIEW PAGE ----------------------
@app.route("/interview")
def interview():
    name = session.get("user_name", "Candidate")
    return render_template("interview.html", name=name)

# ---------------------- LLM Paragraph Generator ----------------------
@app.route("/next-question", methods=["GET"])
def next_question():
    """Generate Big Five test paragraph dynamically using LLM."""
    name = session.get("user_name", "Candidate")
    try:
        paragraph = generate_interview_question(name, [], [], short=False)
        app.logger.info(f"🧠 Generated paragraph for {name}")
    except Exception as e:
        app.logger.error(f"LLM generation failed: {e}")
        paragraph = (
            "Artificial Intelligence is transforming industries worldwide. "
            "Its ability to analyze, adapt, and learn has reshaped how humans work, "
            "interact, and innovate across every field."
        )
    return jsonify({"success": True, "name": name, "paragraph": paragraph})

# ---------------------- AI VOICE GREETING ----------------------
# ---------------------- AI VOICE GREETING ----------------------
@app.route("/tts", methods=["POST"])
def tts_route():
    """
    Use the same TTS method and voice as the video interview page.
    This will ensure identical sound and instant playback.
    """
    data = request.get_json() or {}
    text = data.get("text", "").strip()
    if not text:
        return jsonify({"success": False, "error": "No text provided."}), 400

    try:
        # Use same TTS call that works on the video interview page
        audio_path = say_text_to_file(text, filename="intelx_greeting.wav")

        # Wait briefly until the file exists (handles async generation)
        for _ in range(10):
            if os.path.exists(audio_path):
                break
            time.sleep(0.1)

        if not os.path.exists(audio_path):
            raise FileNotFoundError(audio_path)

        # Return URL for playback
        print(f"✅ TTS ready: {audio_path}")
        return jsonify({"success": True, "audio": "/" + audio_path.replace("\\", "/")})

    except Exception as e:
        print("❌ TTS Error:", e)
        return jsonify({"success": False, "error": str(e)}), 500

# ---------------------- VOICE UPLOAD & ANALYSIS ----------------------
@app.route("/upload-audio", methods=["POST"])
def upload_audio():
    """Handles voice recordings from the interview page."""
    print("🟡 /upload-audio endpoint hit!")

    file = None
    for key in ("audio_data", "audio", "file"):
        if key in request.files:
            file = request.files[key]
            break

    if not file:
        return jsonify({"success": False, "error": "No audio file received."}), 400

    filename = file.filename or f"audio_{datetime.now().strftime('%Y%m%d_%H%M%S')}.webm"
    if not any(filename.lower().endswith(ext) for ext in ALLOWED_EXT):
        filename = os.path.splitext(filename)[0] + ".webm"

    safe_name = timestamped_filename(filename)
    saved_path = os.path.join(UPLOAD_FOLDER, safe_name)
    file.save(saved_path)
    print("💾 Saved file:", saved_path)

    wav_path = convert_to_wav(saved_path)
    try:
        result = analyze_voice(wav_path)
        print("🎯 Analysis result:", result)
    except Exception as e:
        print("❌ Voice analysis failed:", e)
        return jsonify({"success": False, "error": str(e)}), 500

    result_file = os.path.join(UPLOAD_FOLDER, "latest_result.txt")
    with open(result_file, "w", encoding="utf-8") as f:
        for k, v in result.items():
            f.write(f"{k}:{v}\n")

    return jsonify({"success": True, "redirect": url_for("analysis_result"), "result": result})

# ---------------------- ANALYSIS RESULT PAGE ----------------------
@app.route("/analysis-result")
def analysis_result():
    """Displays final Big Five personality result."""
    traits = {}
    result_file = os.path.join(UPLOAD_FOLDER, "latest_result.txt")
    if os.path.exists(result_file):
        with open(result_file, "r", encoding="utf-8") as f:
            for line in f:
                if ":" in line:
                    k, v = line.strip().split(":", 1)
                    try:
                        traits[k] = round(float(v), 2)
                    except ValueError:
                        traits[k] = v
    return render_template("analysis_result.html", traits=traits)

# ---------------------- VIDEO INTERVIEW ----------------------
@app.route("/video-interview")
def video_interview():
    return render_template("video_interview.html")

@app.route("/upload-video", methods=["POST"])
def upload_video():
    """Handle video recording uploads."""
    if "video" not in request.files:
        return jsonify({"success": False, "error": "No video file received."}), 400

    file = request.files["video"]
    filename = file.filename or f"video_{datetime.now().strftime('%Y%m%d_%H%M%S')}.webm"
    filename = timestamped_filename(filename)
    save_path = os.path.join(UPLOAD_FOLDER, filename)
    file.save(save_path)
    rel_path = url_for("static", filename=f"uploads/{filename}")
    return jsonify({"success": True, "path": rel_path})

# ---------------------- MAIN ----------------------
if __name__ == "__main__":
    app.run(debug=True)
