# ai_module/llm_engine.py
import requests
import json
import random

# =============================
# CONFIGURATION
# =============================
OLLAMA_URL = "http://localhost:11434/api/generate"   # Ollama local API endpoint


# =============================
# CORE LLM CALLER
# =============================
def llm_generate(prompt: str, model: str = "llama3", max_tokens: int = 180) -> str:
    """
    Send a prompt to the local Ollama model and return its response as plain text.
    """
    payload = {
        "model": model,
        "prompt": prompt,
        "max_tokens": max_tokens,
        "stream": False
    }
    try:
        response = requests.post(OLLAMA_URL, json=payload, timeout=60)
        response.raise_for_status()
        data = response.json()

        # Handle multiple possible response shapes
        if isinstance(data, dict):
            if "response" in data:
                return data["response"].strip()
            if "text" in data:
                return data["text"].strip()
            if "choices" in data and len(data["choices"]) > 0:
                choice = data["choices"][0]
                if isinstance(choice, dict):
                    return (choice.get("message") or choice.get("text") or "").strip()

        # fallback
        return json.dumps(data)

    except Exception as e:
        return f"[LLM error: {e}]"


# =============================
# PERSONALITY PARAGRAPH GENERATOR
# =============================
def generate_personality_paragraph(name: str = "Candidate"):
    """
    Generate a short, clear, human-readable paragraph (Big Five style)
    for voice-based personality testing. The paragraph should be neutral,
    emotionally balanced, and natural to read aloud.
    """
    # Randomly pick one of the Big Five traits to theme the paragraph
    trait = random.choice([
        "Openness to Experience",
        "Conscientiousness",
        "Extraversion",
        "Agreeableness",
        "Emotional Stability"
    ])

    prompt = f"""
    You are InteleX, an AI psychologist assistant.
    Generate one short, natural-sounding paragraph (about 80-120 words)
    that a person can read aloud for a voice-based personality analysis test.
    The paragraph should be calm, descriptive, and focused on the personality trait: {trait}.
    Avoid asking any questions or listing bullet points.
    Write in a smooth, human tone that sounds good when spoken.
    Start immediately with the content — no greeting or labels.
    """

    text = llm_generate(prompt)

    # If the LLM fails, return a static fallback paragraph
    if text.startswith("[LLM error"):
        text = (
            "Adaptability is one of the most valuable traits in daily life. "
            "It allows individuals to stay composed under pressure, embrace change confidently, "
            "and learn from new experiences without losing focus or motivation."
        )

    # Clean minor formatting
    text = text.replace("\n", " ").strip()
    if len(text) > 600:
        text = text[:600].rsplit('.', 1)[0] + '.'

    return text


# =============================
# LEGACY COMPATIBILITY FUNCTION
# =============================
def generate_interview_question(name: str, skills: list, prev_questions: list, short: bool = True):
    """
    Retained for backward compatibility with app.py.
    Now simply calls the Big-Five paragraph generator.
    """
    return generate_personality_paragraph(name)
