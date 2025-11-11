from flask import Flask, render_template, request, jsonify, redirect, url_for
import os
from datetime import datetime
from werkzeug.utils import secure_filename
import subprocess
from ai_module.voice_analyzer import analyze_voice

# ---------------------- CONFIG ----------------------
app = Flask(__name__)
UPLOAD_FOLDER = "static/uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

ALLOWED_EXT = {"wav", "webm", "mp3", "ogg", "m4a", "flac"}

# ---------------------- HELPERS ----------------------
def allowed(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXT

def timestamped_filename(filename):
    name = secure_filename(filename)
    base, ext = os.path.splitext(name)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"{base}_{ts}{ext}"

def convert_to_wav(input_path):
    """
    Converts any audio file to WAV using ffmpeg.
    """
    base = os.path.splitext(os.path.basename(input_path))[0]
    wav_path = os.path.join(UPLOAD_FOLDER, f"{base}.wav")
    try:
        cmd = [
            "ffmpeg", "-y", "-i", input_path,
            "-ar", "22050", "-ac", "1", wav_path
        ]
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if os.path.exists(wav_path):
            print(f"✅ Converted {input_path} -> {wav_path}")
            return wav_path
        else:
            print("⚠️ Conversion failed:", result.stderr)
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
        if not resume_file or resume_file.filename == "":
            return render_template("resume.html", error="Please upload your resume.")
        filename = timestamped_filename(resume_file.filename)
        save_path = os.path.join(UPLOAD_FOLDER, filename)
        resume_file.save(save_path)
        return redirect(url_for("interview"))
    return render_template("resume.html")

@app.route("/interview")
def interview():
    return render_template("interview.html")

# ---------------- LLM Question Generator ----------------
# add/replace this route in app.py (near other routes)
from ai_module.llm_engine import generate_interview_question

@app.route('/next-question', methods=['POST'])
def next_question():
    data = request.get_json() or {}
    name = data.get('name', 'Candidate')
    skills = data.get('skills', [])
    prev = data.get('previous', [])
    # accept optional flag to request short question (default True)
    short_flag = data.get('short', True)

    question = generate_interview_question(name, skills, prev, short=short_flag)
    # If LLM returned error marker, reflect it
    if question.startswith("[LLM error"):
        return jsonify({'success': False, 'error': question}), 500

    return jsonify({'success': True, 'question': question})

# ---------------- AI Voice Route ----------------
from ai_module.tts import say_text_to_file

@app.route('/get-ai-voice', methods=['POST'])
def get_ai_voice():
    data = request.get_json()
    text = data.get('text', '')
    try:
        audio_path = say_text_to_file(text, filename="inteleX_speech.wav")
        return jsonify({'success': True, 'audio': '/' + audio_path.replace('\\', '/')})
    except Exception as e:
        print("TTS Error:", e)
        return jsonify({'success': False, 'error': str(e)})


@app.route("/upload-audio", methods=["POST"])
def upload_audio():
    """
    Handles voice recording uploads from the interview page.
    """
    print("🟡 /upload-audio endpoint hit!")
    print("🔍 Incoming form keys:", request.files.keys())

    # Accept multiple possible keys from frontend
    file = None
    for key in ("audio_data", "audio", "file"):
        if key in request.files:
            file = request.files[key]
            break

    if not file:
        print("❌ No file found in request.")
        return jsonify({"success": False, "error": "No audio file received."}), 400

    if file.filename == "":
        print("⚠️ Empty filename received, using default name.")
        filename = f"audio_{datetime.now().strftime('%Y%m%d_%H%M%S')}.webm"
    else:
        filename = file.filename

    # Force .webm extension if no valid extension found
    if not any(filename.lower().endswith(ext) for ext in [".wav", ".webm", ".mp3", ".ogg", ".m4a", ".flac"]):
        filename = os.path.splitext(filename)[0] + ".webm"

    safe_name = timestamped_filename(filename)
    saved_path = os.path.join(UPLOAD_FOLDER, safe_name)
    file.save(saved_path)
    print("💾 Saved file:", saved_path)

    # Convert to WAV for analysis
    wav_path = convert_to_wav(saved_path)

    # Analyze voice using trained model
    try:
        result = analyze_voice(wav_path)
        print("🎯 Analysis result:", result)
    except Exception as e:
        print("❌ Voice analysis failed:", e)
        return jsonify({"success": False, "error": str(e)}), 500

    # Save results for display
    result_file = os.path.join(UPLOAD_FOLDER, "latest_result.txt")
    with open(result_file, "w", encoding="utf-8") as f:
        for k, v in result.items():
            f.write(f"{k}:{v}\n")

    return jsonify({
        "success": True,
        "redirect": url_for("analysis_result"),
        "result": result
    })

@app.route("/analysis-result")
def analysis_result():
    """
    Displays the final Big Five analysis result.
    """
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

# ---------------- VIDEO INTERVIEW ----------------
@app.route("/video-interview")
def video_interview():
    """
    Renders the video interview page.
    """
    return render_template("video_interview.html")


@app.route("/upload-video", methods=["POST"])
def upload_video():
    """
    Handles video recording uploads from the video interview page.
    Saves the file and returns its path.
    """
    print("🟡 /upload-video endpoint hit!")
    print("🔍 Incoming form keys:", request.files.keys())

    if "video" not in request.files:
        return jsonify({"success": False, "error": "No video file received."}), 400

    file = request.files["video"]
    if file.filename == "":
        filename = f"video_{datetime.now().strftime('%Y%m%d_%H%M%S')}.webm"
    else:
        filename = timestamped_filename(file.filename)

    save_path = os.path.join(UPLOAD_FOLDER, filename)
    file.save(save_path)
    print(f"💾 Saved video to {save_path}")

    rel_path = url_for("static", filename=f"uploads/{filename}")
    return jsonify({"success": True, "path": rel_path})


if __name__ == "__main__":
    app.run(debug=True)
