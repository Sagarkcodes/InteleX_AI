import os
import random
from pathlib import Path

from dotenv import load_dotenv
from groq import Groq


BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR.parent / ".env")
load_dotenv(BASE_DIR / ".env")

API_KEY = os.getenv("GROQ_API_KEY")
client = Groq(api_key=API_KEY) if API_KEY else None

DEFAULT_MAX_TOKENS = 120

# ==============================
# CORE LLM CALL
# ==============================

def llm_generate(prompt: str, max_tokens: int = None) -> str:
    max_tokens = int(max_tokens or DEFAULT_MAX_TOKENS)

    if client is None:
        return "[LLM unavailable: GROQ_API_KEY is not configured]"

    try:
        response = client.chat.completions.create(
            messages=[
                {"role": "system", "content": "You are a friendly human-like interviewer."},
                {"role": "user", "content": prompt}
            ],
            model="llama-3.3-70b-versatile"
        )

        return response.choices[0].message.content.strip()

    except Exception as e:
        print("Groq API Error:", e)
        return f"[LLM error: {e}]"


# ==============================
# BIG-5 DYNAMIC PARAGRAPH
# ==============================

def generate_personality_paragraph(name="Candidate"):

    traits = [
        "Openness to Experience",
        "Conscientiousness",
        "Extraversion",
        "Agreeableness",
        "Emotional Stability"
    ]

    selected_trait = random.choice(traits)

    prompt = f"""
    Generate a short reading phrase (20-35 words) related to the personality trait: {selected_trait}.
    It must:
    - Be natural to read aloud
    - Be one or two short sentences
    - Be simple and clear
    - Not mention personality test
    - Not mention the trait name
    """

    paragraph = llm_generate(prompt, max_tokens=80)

    if not paragraph or paragraph.startswith("[LLM"):
        return "I approach new situations with curiosity and stay focused on achieving meaningful goals."

    return paragraph.strip()


# ==============================
# RESUME SKILL EXTRACTION
# ==============================

def extract_resume_skills(text: str):

    if not text.strip():
        return []

    prompt = f"""
Extract technical skills from the following resume.

Rules:
- Return only technical skills
- Comma separated
- Ignore soft skills
- No explanations

Resume:
{text}

Skills:
"""

    result = llm_generate(prompt, max_tokens=120)

    if not result or result.startswith("[LLM"):
        return []

    result = result.replace("\n", ",")
    skills = [s.strip(" .") for s in result.split(",") if s.strip()]

    final = []
    seen = set()

    for sk in skills:
        low = sk.lower()
        if low not in seen:
            final.append(sk)
            seen.add(low)

    return final


# ==============================
# RESUME PROJECT EXTRACTION
# ==============================

def extract_resume_projects(text: str):

    if not text.strip():
        return []

    prompt = f"""
Extract ONLY project names from the following resume text.

Rules:
- Return only project titles
- Comma separated
- No explanations

Resume:
{text}

Projects:
"""

    result = llm_generate(prompt, max_tokens=120)

    if not result or result.startswith("[LLM"):
        return []

    result = result.replace("\n", ",")
    projects = [p.strip(" .") for p in result.split(",") if p.strip()]

    final = []
    seen = set()

    for pr in projects:
        low = pr.lower()
        if low not in seen:
            final.append(pr)
            seen.add(low)

    return final


# ==============================
# HUMAN FEEDBACK
# ==============================

def generate_human_feedback(answer: str):

    if not answer or len(answer.strip()) < 5:
        return "I couldn't clearly hear your answer. Let's move to the next question."

    prompt = f"""
You are a professional technical interviewer.

Candidate answer:
{answer}

Give a short human-like reaction as an interviewer.

Rules:
- One sentence only
- Under 18 words    
- Sound natural
- React to what the candidate said

Examples:
"That's a clear explanation."
"Good approach, but you could expand more on the implementation."
"Nice answer, I like how you explained your reasoning."
"""

    feedback = llm_generate(prompt, max_tokens=40)

    if not feedback or feedback.startswith("[LLM"):
        feedback = "Good answer. Let's move to the next question."

    return feedback

# ==============================
# RESUME BASED QUESTIONS
# ==============================

def generate_interview_question(
    name: str,
    skills: list,
    projects: list = None,
    question_number: int = 1,
    asked_questions: list | None = None
):

    question_number = max(1, int(question_number or 1))
    asked_questions = asked_questions or []

    if not skills:
        skills = ["programming"]

    projects = projects or []

    use_project = bool(projects) and question_number <= 3
    previous_questions_text = "\n".join(f"- {q}" for q in asked_questions[-5:])
    no_repeat_rule = (
        f"\nAvoid repeating these earlier questions:\n{previous_questions_text}\n"
        if previous_questions_text else ""
    )

    if use_project:
        topic = projects[(question_number - 1) % len(projects)]

        prompt = f"""
You are a professional technical interviewer.

Candidate Name: {name}

Candidate Project:
{topic}

Ask ONE moderate-level interview question about this project.

Rules:
- Sound like a real human interviewer
- Focus on implementation, challenges, or design decisions
- Avoid very basic questions
- Avoid overly advanced theory
- Keep it practical and real-world
- Keep it under 20 words
- Ask only ONE question
{no_repeat_rule}

Example style:
"What challenges did you face while building this project?"
"How did you design the system architecture for this project?"
"What would you improve if you rebuilt this project?"
"""

    else:
        topic = skills[(question_number - 1) % len(skills)]

        prompt = f"""
You are a professional technical interviewer.

Candidate Name: {name}

Candidate Skill:
{topic}

Ask ONE moderate-level question based on real usage.

Rules:
- Sound natural like a human interviewer
- Focus on practical application
- Avoid basic questions like 'What is {topic}'
- Avoid very advanced theoretical questions
- Keep under 20 words
- Ask only ONE question
{no_repeat_rule}

Example style:
"How did you use {topic} in your project?"
"What challenges did you face while working with {topic}?"
"How do you debug issues when using {topic}?"
"""

    question = llm_generate(prompt, max_tokens=60)

    if not question or question.startswith("[LLM"):
        if use_project:
            question = f"What challenges did you face while building your {topic} project?"
        else:
            question = f"How did you practically use {topic} in your work?"

    question = question.strip()

    if not question.endswith("?"):
        question += "?"

    return question

# ==============================
# DETECT IF CANDIDATE IS STRUGGLING
# ==============================

def detect_candidate_struggle(answer: str):

    if not answer:
        return True

    text = answer.lower()

    weak_patterns = [
        "i don't know",
        "dont know",
        "not sure",
        "no idea",
        "maybe",
        "i guess",
        "cannot remember"
    ]

    if any(p in text for p in weak_patterns):
        return True

    if len(text.split()) < 5:
        return True

    return False


# ==============================
# CONTINUE INTERVIEW PROMPT
# ==============================

def ask_continue_question():

    return (
        "Some questions can be challenging. "
        "Would you like to stop the interview here or continue with two more questions?"
    )
    
# ==============================
# FOLLOW UP QUESTION GENERATOR
# ==============================

def generate_followup_question(answer: str):

    if not answer or len(answer.split()) < 6:
        return None

    prompt = f"""
You are a professional technical interviewer.

Candidate answer:
{answer}

Ask ONE natural follow-up question based on the answer.

Rules:
- sound like a real interviewer
- ask about implementation or reasoning
- under 20 words
"""

    question = llm_generate(prompt, max_tokens=60)

    if not question or question.startswith("[LLM"):
        return None

    if not question.endswith("?"):
        question += "?"

    return question
