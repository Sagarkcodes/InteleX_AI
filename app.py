from ai_module.llm_engine import (
    generate_interview_question,
    extract_resume_skills,
    generate_human_feedback,
    generate_personality_paragraph,
    detect_candidate_struggle,
    ask_continue_question,
    generate_followup_question
)
from flask import Flask, render_template, request, jsonify, redirect, url_for, session
import json
import os
from datetime import datetime
from werkzeug.utils import secure_filename
import subprocess
import time
from ai_module.speech_to_text import transcribe_audio
from config import config
from models import db, Candidate, InterviewSession

# ---------------------- AI MODULE IMPORTS ----------------------
from ai_module.voice_analyzer import analyze_voice
from ai_module.tts import say_text_to_file

# ---------------------- CONFIG ----------------------
app = Flask(__name__)
UPLOAD_FOLDER = config.upload_folder
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

ALLOWED_EXT = {"wav", "webm", "mp3", "ogg", "m4a", "flac"}
app.config["SECRET_KEY"] = config.secret_key
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["SQLALCHEMY_DATABASE_URI"] = config.database_uri
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.secret_key = app.config["SECRET_KEY"]

db.init_app(app)
with app.app_context():
    db.create_all()


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
        print(f" Greeting voice cached successfully at {PREGENERATED_GREETING_PATH}")
    except Exception as e:
        print(f" Greeting pre-generation failed: {e}")
else:
    print(f"Cached greeting already exists at {PREGENERATED_GREETING_PATH}")


# ---------------------- HELPERS ----------------------
def allowed(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXT


def timestamped_filename(filename):
    name = secure_filename(filename)
    base, ext = os.path.splitext(name)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"{base}_{ts}{ext}"


def convert_to_wav(input_path):
    """Robust conversion for webm (opus) → wav"""
    base = os.path.splitext(os.path.basename(input_path))[0]
    wav_path = os.path.join(UPLOAD_FOLDER, f"{base}.wav")

    try:
        cmd = [
            "ffmpeg",
            "-y",
            "-f", "webm",          
            "-i", input_path,
            "-vn",
            "-acodec", "pcm_s16le",
            "-ar", "16000",
            "-ac", "1",
            wav_path
        ]

        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

        if result.returncode != 0:
            print("FFmpeg error:", result.stderr)
            return input_path

        if os.path.exists(wav_path):
            print(f" Converted {input_path} -> {wav_path}")
            return wav_path

        return input_path

    except Exception as e:
        print(" Conversion exception:", e)
        return input_path

def default_interview_state():
    return {
        "answers_received": 0,
        "max_questions": 5,
        "awaiting_continue_decision": False,
        "question_history": []
    }


def reset_interview_state():
    session["interview_state"] = default_interview_state()
    session.modified = True
    return session["interview_state"]


def get_interview_state():
    state = session.get("interview_state")
    if not isinstance(state, dict):
        return reset_interview_state()

    defaults = default_interview_state()
    for key, value in defaults.items():
        state.setdefault(key, value if not isinstance(value, list) else [])

    session["interview_state"] = state
    session.modified = True
    return state


def save_interview_state(state):
    session["interview_state"] = state
    session.modified = True


def remember_question(question_text):
    state = get_interview_state()
    history = list(state.get("question_history", []))
    history.append(question_text)
    state["question_history"] = history[-10:]
    save_interview_state(state)


def get_candidate_profile():
    return session.get("candidate_profile", {})


def resolve_candidate_name(resume_text=""):
    profile = get_candidate_profile()
    registered_name = (profile.get("name") or "").strip()
    if registered_name:
        return registered_name

    if resume_text:
        first_line = resume_text.strip().split("\n")[0].strip()
        if first_line and len(first_line.split()) <= 4:
            return first_line

    return "Candidate"


def serialize_json(value, default):
    payload = default if value is None else value
    return json.dumps(payload)


def get_candidate_record():
    candidate_id = session.get("candidate_id")
    if candidate_id:
        return db.session.get(Candidate, candidate_id)

    profile = get_candidate_profile()
    email = (profile.get("email") or "").strip().lower()
    if email:
        candidate = Candidate.query.filter_by(email=email).order_by(Candidate.id.desc()).first()
        if candidate:
            session["candidate_id"] = candidate.id
            return candidate

    return None


def upsert_candidate_record(resume_filename=None, resume_text=None, skills=None, projects=None):
    profile = get_candidate_profile()
    candidate = get_candidate_record()

    if candidate is None:
        candidate = Candidate()

    candidate.name = session.get("user_name") or (profile.get("name") or "Candidate").strip() or "Candidate"
    candidate.email = (profile.get("email") or "").strip() or None
    candidate.target_role = (profile.get("target_role") or "").strip() or None

    if resume_filename is not None:
        candidate.resume_filename = resume_filename
    if resume_text is not None:
        candidate.resume_text = resume_text
    if skills is not None:
        candidate.set_skills(skills)
    if projects is not None:
        candidate.set_projects(projects)

    db.session.add(candidate)
    db.session.commit()

    session["candidate_id"] = candidate.id
    session.modified = True
    return candidate


def get_interview_session_record():
    interview_session_id = session.get("interview_session_id")
    if not interview_session_id:
        return None
    return db.session.get(InterviewSession, interview_session_id)


def sync_interview_session_record(state, status=None, completed=False):
    interview_session = get_interview_session_record()
    if interview_session is None:
        return

    interview_session.answers_received = state.get("answers_received", 0)
    interview_session.max_questions = state.get("max_questions", 5)
    interview_session.awaiting_continue_decision = state.get("awaiting_continue_decision", False)
    interview_session.question_history_json = serialize_json(state.get("question_history"), [])
    interview_session.analysis_result_json = serialize_json(session.get("analysis_result"), {})

    if status:
        interview_session.status = status
    if completed:
        interview_session.completed_at = datetime.utcnow()

    db.session.add(interview_session)
    db.session.commit()


def start_interview_session_record(initial_question):
    candidate = upsert_candidate_record(
        resume_filename=session.get("resume_file"),
        skills=session.get("resume_skills"),
        projects=session.get("resume_projects")
    )

    interview_session = InterviewSession(
        candidate_id=candidate.id,
        status="in_progress",
        phase="video_interview"
    )
    interview_session.set_question_history([initial_question])
    interview_session.set_analysis_result(session.get("analysis_result"))

    db.session.add(interview_session)
    db.session.commit()

    session["interview_session_id"] = interview_session.id
    session.modified = True
    return interview_session


# ---------------------- ROUTES ----------------------
@app.route("/")
def home():
    return render_template("index.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        session["candidate_profile"] = {
            "name": (request.form.get("name") or "").strip(),
            "email": (request.form.get("email") or "").strip(),
            "target_role": (request.form.get("role") or "").strip()
        }
        session.pop("analysis_result", None)
        session.pop("interview_session_id", None)
        reset_interview_state()
        return redirect(url_for("resume"))
    return render_template("register.html")


# ---------------------- RESUME UPLOAD + SKILL EXTRACTION ----------------------
@app.route("/resume", methods=["GET", "POST"])
def resume():

    if request.method == "POST":

        resume_file = request.files.get("resume")

        if not resume_file or resume_file.filename == "":
            return render_template(
                "resume.html",
                error="⚠ Please upload your resume (PDF or Word)."
            )

        allowed_resume_ext = {"pdf", "doc", "docx"}
        ext = resume_file.filename.rsplit(".", 1)[-1].lower()

        if ext not in allowed_resume_ext:
            return render_template(
                "resume.html",
                error="⚠ Invalid file type. Upload PDF, DOC, or DOCX only."
            )

        filename = timestamped_filename(resume_file.filename)
        save_path = os.path.join(UPLOAD_FOLDER, filename)
        resume_file.save(save_path)

        session["resume_file"] = filename

        resume_text = ""

        try:
            if ext == "pdf":

                import PyPDF2

                with open(save_path, "rb") as f:
                    reader = PyPDF2.PdfReader(f)

                    for page in reader.pages:
                        resume_text += (page.extract_text() or "") + "\n"

            elif ext in ("doc", "docx"):

                import docx

                doc = docx.Document(save_path)

                for p in doc.paragraphs:
                    resume_text += p.text + "\n"

        except Exception as e:
            print("Resume text extraction error:", e)
            resume_text = ""

        # ---------------- IMPROVED SKILL + PROJECT EXTRACTION ----------------
        try:

            extracted = extract_resume_skills(resume_text) if resume_text else []

            skills = []
            projects = []
            seen = set()

            for item in extracted:

                val = item.strip()

                if not val:
                    continue

                key = val.lower()

                if key in seen:
                    continue

                seen.add(key)

                # simple heuristic: detect project names
                if "project" in key or "system" in key or "application" in key or "app" in key:
                    projects.append(val)
                else:
                    skills.append(val)

            # limit counts
            skills = skills[:8]
            projects = projects[:5]

        except Exception as e:
            print("Skill extraction error:", e)
            skills = []
            projects = []

        session["resume_skills"] = skills
        session["resume_projects"] = projects
        # ---------------------------------------------------------------------

        session["user_name"] = resolve_candidate_name(resume_text)
        upsert_candidate_record(
            resume_filename=filename,
            resume_text=resume_text,
            skills=skills,
            projects=projects
        )
        session.pop("interview_session_id", None)
        reset_interview_state()

        return redirect(url_for("interview"))

    return render_template("resume.html")


# ---------------------- INTERVIEW PAGE ----------------------
@app.route("/interview")
def interview():
    if not session.get("resume_file"):
        return redirect(url_for("resume"))

    name = session.get("user_name", "Candidate")

    return render_template("interview.html", name=name)


# ---------------------- NEXT QUESTION ----------------------
@app.route("/next-question", methods=["POST"])
def next_question():

    name = session.get("user_name", "Candidate")
    skills = session.get("resume_skills", [])
    projects = session.get("resume_projects", [])
    state = get_interview_state()

    if "audio" not in request.files:
        return jsonify({"error": "No audio received"}), 400

    audio_file = request.files["audio"]

    filename = timestamped_filename(audio_file.filename or "answer.webm")
    save_path = os.path.join(UPLOAD_FOLDER, filename)
    audio_file.save(save_path)

    # ---------------- TRANSCRIPTION ----------------
    try:
        transcript = transcribe_audio(save_path)
    except Exception as e:
        print("Transcription error:", e)
        transcript = ""

    print("Transcribed:", transcript)

    state["answers_received"] += 1

    feedback = generate_human_feedback(transcript)
    struggling = detect_candidate_struggle(transcript)
    followup_question = generate_followup_question(transcript)

    # ---------------- FINAL RESULT ----------------
    if state["answers_received"] >= state["max_questions"]:

        score = min(10, len(transcript.split()) / 5)

        final_result = {
            "name": name,
            "skills": skills,
            "score": round(score, 2),
            "feedback": feedback,

            #  ANALYSIS (FOR FINAL PAGE)
            "analysis": {
                "confidence": round(score * 10, 1),
                "clarity": round(score * 8, 1),
                "communication": round(score * 9, 1),
                "summary": "The candidate shows decent communication skills but can improve clarity and confidence."
            }
        }

        session["final_result"] = final_result
        session.modified = True

        sync_interview_session_record(state, status="completed", completed=True)
        session.pop("interview_session_id", None)
        reset_interview_state()

        return jsonify({
            "completed": True,
            "redirect": url_for("final_result_page")
        })

    # ---------------- NORMAL FLOW ----------------
    if followup_question:
        question = followup_question
    else:
        question = generate_interview_question(
            name,
            skills,
            projects,
            question_number=state["answers_received"] + 1,
            asked_questions=state.get("question_history", [])
        )

    save_interview_state(state)
    remember_question(question)
    sync_interview_session_record(get_interview_state(), status="in_progress")

    return jsonify({
        "completed": False,
        "feedback": feedback,
        "question": question
    })


# ---------------------- FINAL RESULT ROUTE ----------------------
@app.route("/final-result")
def final_result_page():

    result = session.get("final_result")

    if not result:
        return redirect(url_for("home"))

    return render_template(
        "final_result.html",
        result=result,
        analysis=result.get("analysis", {})
    )

# ---------------------- TTS ----------------------
@app.route("/tts", methods=["POST"])
def tts_route():
    data = request.get_json() or {}
    text = data.get("text", "").strip()

    if not text:
        return jsonify({"success": False, "error": "No text provided."}), 400

    try:
        audio_path = say_text_to_file(text, filename="intelx_greeting.wav")

        for _ in range(10):
            if os.path.exists(audio_path):
                break
            time.sleep(0.1)

        return jsonify({"success": True, "audio": "/" + audio_path.replace("\\", "/")})

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


# ---------------------- NEXT PARAGRAPH ----------------------
@app.route("/next-paragraph", methods=["GET"])
def next_paragraph():

    name = session.get("user_name", "Candidate")

    try:
        paragraph = generate_personality_paragraph(name)

    except Exception as e:
        print("Paragraph generation error:", e)
        paragraph = "Please read this passage clearly and confidently."

    return jsonify({
        "success": True,
        "paragraph": paragraph
    })


# ---------------------- AUDIO UPLOAD ----------------------
@app.route("/upload-audio", methods=["POST"])
def upload_audio():

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

    wav_path = convert_to_wav(saved_path)

    try:
        result = analyze_voice(wav_path)

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

    session["analysis_result"] = result
    session.modified = True
    upsert_candidate_record(
        resume_filename=session.get("resume_file"),
        skills=session.get("resume_skills"),
        projects=session.get("resume_projects")
    )

    return jsonify({
        "success": True,
        "redirect": url_for("analysis_result"),
        "result": result
    })


# ---------------------- ANALYSIS RESULT ----------------------
@app.route("/analysis-result")
def analysis_result():
    raw_traits = session.get("analysis_result", {})
    traits = {}

    if isinstance(raw_traits, dict):
        for key, value in raw_traits.items():
            try:
                traits[key] = round(float(value), 2)
            except (TypeError, ValueError):
                traits[key] = value

    return render_template("analysis_result.html", traits=traits)


# ---------------------- VIDEO INTERVIEW PAGE ----------------------
@app.route("/video-interview")
def video_interview():
    if not session.get("resume_file"):
        return redirect(url_for("resume"))

    print("Session Name:", session.get("user_name"))
    return render_template("video_interview.html")


# ---------------------- VIDEO INTERVIEW START ----------------------
@app.route("/api/video-interview-start", methods=["GET"])
def video_interview_start():
    state = reset_interview_state()
    name = session.get("user_name", "Candidate")
    skills = session.get("resume_skills", [])
    projects = session.get("resume_projects", [])
    profile = get_candidate_profile()

    greeting_text = f"Hi {name}, I'm InteleX, your AI interviewer today. Let's begin."

    instructions_text = (
        "Please keep your face centered, maintain eye contact, and answer clearly."
    )

    praise_text = (
        f"I noticed you have experience in {skills[0]}. That's impressive."
        if skills else
        f"I'm looking forward to learning more about your experience for the {(profile.get('target_role') or 'selected').strip()} position."
    )

    question_text = generate_interview_question(
        name,
        skills,
        projects,
        question_number=state["answers_received"] + 1,
        asked_questions=state.get("question_history", [])
    )
    remember_question(question_text)
    start_interview_session_record(question_text)

    return jsonify({
        "success": True,
        "greeting_text": greeting_text,
        "instructions_text": instructions_text,
        "praise_text": praise_text,
        "question_text": question_text
    })


# ---------------------- VIDEO UPLOAD ----------------------
@app.route("/upload-video", methods=["POST"])
def upload_video():

    if "video" not in request.files:
        return jsonify({"success": False, "error": "No video file received."}), 400

    file = request.files["video"]

    filename = timestamped_filename(file.filename or "video.webm")

    save_path = os.path.join(UPLOAD_FOLDER, filename)

    file.save(save_path)

    return jsonify({
        "success": True,
        "path": url_for("static", filename=f"uploads/{filename}")
    })


@app.route("/about")
def about_page():
    return render_template("about.html", current_year=datetime.now().year)


@app.route("/dashboard")
def dashboard_page():
    return render_template("dashboard.html")


# ---------------------- MAIN ----------------------
if __name__ == "__main__":
    app.run(debug=config.debug)
