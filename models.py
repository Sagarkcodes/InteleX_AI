import json
from datetime import datetime

from flask_sqlalchemy import SQLAlchemy


db = SQLAlchemy()


def encode_json(value, default):
    payload = default if value is None else value
    return json.dumps(payload)


class Candidate(db.Model):
    __tablename__ = "candidates"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False, default="Candidate")
    email = db.Column(db.String(255), index=True)
    target_role = db.Column(db.String(120))
    resume_filename = db.Column(db.String(255))
    resume_text = db.Column(db.Text)
    skills_json = db.Column(db.Text, nullable=False, default="[]")
    projects_json = db.Column(db.Text, nullable=False, default="[]")
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )

    interview_sessions = db.relationship(
        "InterviewSession",
        back_populates="candidate",
        cascade="all, delete-orphan"
    )

    def set_skills(self, skills):
        self.skills_json = encode_json(skills, [])

    def set_projects(self, projects):
        self.projects_json = encode_json(projects, [])


class InterviewSession(db.Model):
    __tablename__ = "interview_sessions"

    id = db.Column(db.Integer, primary_key=True)
    candidate_id = db.Column(db.Integer, db.ForeignKey("candidates.id"), nullable=False, index=True)
    status = db.Column(db.String(30), nullable=False, default="in_progress")
    phase = db.Column(db.String(50), nullable=False, default="video_interview")
    answers_received = db.Column(db.Integer, nullable=False, default=0)
    max_questions = db.Column(db.Integer, nullable=False, default=5)
    awaiting_continue_decision = db.Column(db.Boolean, nullable=False, default=False)
    question_history_json = db.Column(db.Text, nullable=False, default="[]")
    analysis_result_json = db.Column(db.Text, nullable=False, default="{}")
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )
    completed_at = db.Column(db.DateTime)

    candidate = db.relationship("Candidate", back_populates="interview_sessions")

    def set_question_history(self, question_history):
        self.question_history_json = encode_json(question_history, [])

    def set_analysis_result(self, analysis_result):
        self.analysis_result_json = encode_json(analysis_result, {})
