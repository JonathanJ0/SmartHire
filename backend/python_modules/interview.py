#!/usr/bin/env python3
"""
AI Interview Conductor
Uses Ollama's llama3 model to conduct a conversational interview
based on the candidate's resume.json and target role.
"""

import json
import sys
import os
from datetime import datetime
from pathlib import Path

try:
    import requests
except ImportError:
    print("Installing requests...")
    os.system("pip install requests --break-system-packages -q")
    import requests


OLLAMA_URL = "http://localhost:11434/api/chat"
MODEL = "llama3"

COLORS = {
    "reset":   "\033[0m",
    "bold":    "\033[1m",
    "cyan":    "\033[96m",
    "green":   "\033[92m",
    "yellow":  "\033[93m",
    "red":     "\033[91m",
    "magenta": "\033[95m",
    "dim":     "\033[2m",
}

def c(text, *styles):
    return "".join(COLORS[s] for s in styles) + str(text) + COLORS["reset"]


def check_ollama():
    try:
        r = requests.get("http://localhost:11434/api/tags", timeout=5)
        models = [m["name"] for m in r.json().get("models", [])]
        has_llama3 = any("llama3" in m for m in models)
        if not has_llama3:
            print(c("⚠  llama3 model not found. Pulling it now...", "yellow"))
            os.system("ollama pull llama3")
        return True
    except Exception:
        print(c("✗  Cannot connect to Ollama. Make sure it's running: `ollama serve`", "red"))
        sys.exit(1)


def chat(messages: list[dict]) -> str:
    """Send messages and stream the response token by token."""
    payload = {"model": MODEL, "messages": messages, "stream": True}
    response_text = ""
    try:
        with requests.post(OLLAMA_URL, json=payload, stream=True, timeout=180) as r:
            r.raise_for_status()
            for line in r.iter_lines():
                if line:
                    chunk = json.loads(line)
                    token = chunk.get("message", {}).get("content", "")
                    print(token, end="", flush=True)
                    response_text += token
                    if chunk.get("done"):
                        break
    except requests.exceptions.RequestException as e:
        print(c(f"\n✗  Request failed: {e}", "red"))
        sys.exit(1)
    print()
    return response_text.strip()


def load_resume(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def build_system_prompt(resume: dict, role: str) -> str:
    resume_str = json.dumps(resume, indent=2)
    return f"""You are a senior technical interviewer conducting a LIVE, real-time interview for the role of {role}.

IDENTITY & TONE:
- You are professional, attentive, and conversational — not robotic or overly formal.
- Adapt your tone based on the candidate's energy: if they're nervous, be warm; if they're confident, be more challenging.
- You have already reviewed the candidate's resume before this interview.

STRICT CONVERSATIONAL RULES:
- Send ONLY ONE message per turn. Ask ONE question, then stop completely.
- NEVER write meta-commentary like "(wait for response)" or "(candidate answers)".
- NEVER simulate or anticipate what the candidate might say.
- NEVER ask multiple questions in one message — even as an aside.
- Keep each message to 2–4 sentences. Be direct and natural.
- Always acknowledge what the candidate just said before moving on.
- If an answer is vague, incomplete, or interesting — ask ONE targeted follow-up instead of moving on.

INTERVIEW FLOW (track internally — never announce phases):

Phase 1 — Warm Welcome (1 exchange):
Greet the candidate by name if available. Briefly introduce yourself. Ask them to walk you through their background.

Phase 2 — Resume Exploration (3 questions):
Ask about a specific project, role, or achievement from their resume. Go beyond surface level — ask about their personal contribution, a challenge they faced, or a decision they made. Spread across 3 exchanges.

Phase 3 — Technical Assessment (3 questions):
Ask basic technical questions on the skills in the resume. 

Phase 4 — Behavioral (1 question):
Ask one behavioral question using a real-world framing (e.g., "Tell me about a time…"). Probe for specifics if the answer stays high-level.

Phase 5 — Candidate Questions (1 exchange):
Ask if the candidate has any questions for you. Answer naturally and briefly.

Phase 6 — Close (1 message):
Thank them sincerely. Tell them the interview is complete and that they'll hear back via email within a few business days. Do not ask any more questions after this.

FLOW RULES:
- Never skip or merge phases.
- Only advance after the candidate has responded.
- Total interview = 10–11 exchanges across all phases.
- Never announce which phase you are in or that you are "moving on."

RESUME:
{resume_str}

Role: {role}

You are mid-conversation. React only to what the candidate just said. Send ONE message. Then stop."""


def save_transcript(messages: list[dict], role: str, resume_path: str) -> str:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"interview_transcript_{timestamp}.txt"

    lines = [
        "=" * 60,
        "  INTERVIEW TRANSCRIPT",
        f"  Role: {role}",
        f"  Resume: {resume_path}",
        f"  Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "=" * 60,
        "",
    ]

    for msg in messages:
        if msg["role"] == "system":
            continue
        speaker = "INTERVIEWER" if msg["role"] == "assistant" else "CANDIDATE"
        lines.append(f"[{speaker}]")
        lines.append(msg["content"])
        lines.append("")

    lines += ["=" * 60, "  END OF TRANSCRIPT", "=" * 60]

    with open(filename, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    return filename


def print_header():
    print()
    print(c("╔══════════════════════════════════════════╗", "cyan", "bold"))
    print(c("║        AI INTERVIEW CONDUCTOR  🎙         ║", "cyan", "bold"))
    print(c("║       Powered by Ollama · llama3         ║", "cyan"))
    print(c("╚══════════════════════════════════════════╝", "cyan", "bold"))
    print()


def print_divider():
    print(c("─" * 50, "dim"))


def is_closing(text: str) -> bool:
    signals = [
        "thank you for your time", "good luck", "we'll be in touch",
        "that concludes", "end of our interview", "pleasure speaking",
        "best of luck", "wish you all the best", "hope to hear from you",
        "we will get back to you", "great chatting with you",
    ]
    lower = text.lower()
    return any(sig in lower for sig in signals)


def main():
    print_header()

    # --- Load resume ---
    resume_path = input(c("📄 Path to resume.json: ", "yellow")).strip()
    if not resume_path:
        resume_path = "resume.json"

    if not Path(resume_path).exists():
        print(c(f"✗  File not found: {resume_path}", "red"))
        sys.exit(1)

    try:
        resume = load_resume(resume_path)
        print(c("✓  Resume loaded successfully.", "green"))
    except json.JSONDecodeError as e:
        print(c(f"✗  Invalid JSON in resume: {e}", "red"))
        sys.exit(1)

    # --- Get target role ---
    role = input(c("💼 Role to interview for: ", "yellow")).strip()
    if not role:
        role = "Software Engineer"

    print()
    check_ollama()
    print(c(f"✓  Connected to Ollama · Model: {MODEL}", "green"))
    print()
    print(c("  Tips: type your answers and press Enter  ·  'quit' to exit early", "dim"))
    print()
    print_divider()
    print()

    # Build system prompt
    system_prompt = build_system_prompt(resume, role)

    # Full message history for context
    messages = [{"role": "system", "content": system_prompt}]

    # --- Opening turn ---
    # We use a brief hidden user seed to trigger the first message only.
    # The seed is included in messages so the model sees it as context.
    seed = "Hi, I'm ready for the interview."
    messages.append({"role": "user", "content": seed})

    print(c("INTERVIEWER  ", "magenta", "bold"), end="", flush=True)
    opening = chat(messages)
    messages.append({"role": "assistant", "content": opening})

    # --- Conversation loop ---
    while True:
        print()
        print_divider()
        print()
        try:
            user_input = input(c("YOU  ▶  ", "green", "bold")).strip()
        except (KeyboardInterrupt, EOFError):
            print()
            user_input = "quit"

        if not user_input:
            continue

        if user_input.lower() in ("quit", "exit", "done", "bye"):
            print()
            print(c("Ending interview early...", "yellow"))
            break

        messages.append({"role": "user", "content": user_input})

        print()
        print(c("INTERVIEWER  ", "magenta", "bold"), end="", flush=True)
        response = chat(messages)
        messages.append({"role": "assistant", "content": response})

        if is_closing(response):
            print()
            print(c("✓  Interview concluded.", "green"))
            break

    # --- Save transcript ---
    print()
    transcript_file = save_transcript(messages, role, resume_path)
    print(c(f"📝 Transcript saved → {transcript_file}", "cyan", "bold"))
    print()


if __name__ == "__main__":
    main()