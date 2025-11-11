# ai_module/llm_engine.py
import requests
import json

OLLAMA_URL = "http://localhost:11434/api/generate"

def llm_generate(prompt: str, model: str = "llama3", max_tokens: int = 120) -> str:
    """Send prompt to local Ollama and return response text."""
    payload = {"model": model, "prompt": prompt, "max_tokens": max_tokens, "stream": False}
    try:
        r = requests.post(OLLAMA_URL, json=payload, timeout=60)
        r.raise_for_status()
        res = r.json()
        # Ollama's response shape may vary; try to read response field
        if isinstance(res, dict):
            # primary key used earlier: 'response'
            if "response" in res:
                return res["response"].strip()
            if "text" in res:
                return res["text"].strip()
            if "choices" in res and len(res["choices"]) > 0:
                # some versions use choices -> message/text
                c = res["choices"][0]
                if isinstance(c, dict):
                    return (c.get("message") or c.get("text") or "").strip()
        return json.dumps(res)
    except Exception as e:
        return f"[LLM error: {e}]"

def generate_interview_question(name: str, skills: list, prev_questions: list, short: bool = True):
    """
    Generate one short, HR-style interview question.
    `short=True` will bias the LLM prompt to produce a concise single-sentence question.
    """
    skill_text = ", ".join(skills) if skills else "general skills"
    prev_qs = "\n".join(prev_questions[-5:]) if prev_questions else "No previous questions."

    brevity_instruction = "Keep the question short — one sentence, like a human HR would ask." if short else ""

    prompt = (
        f"You are a professional HR interviewer named InteleX. The candidate's name is {name}. "
        f"Their skills include: {skill_text}.\n"
        f"Previously asked questions (recent):\n{prev_qs}\n\n"
        f"{brevity_instruction}\n"
        "Now produce ONE short, polite interview question appropriate for HR/personality or simple behavioral evaluation. "
        "Do NOT include additional commentary, do not number, and keep it concise."
    )

    return llm_generate(prompt)
