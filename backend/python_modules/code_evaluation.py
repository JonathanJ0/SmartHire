"""
evaluator.py
============
Step 1: Generates a random DSA question using llama3.
Step 2: You answer in a JSON file with code and/or explanation.
Step 3: llama3 evaluates your submission and prints a score.

Usage:
    python evaluator.py            <- generates a question
    python evaluator.py ans.json   <- evaluates your answer

Answer JSON format:
    {
      "language": "Python",
      "code": "def solve(...):",
      "explanation": "I used ... because ..."
    }

Requirements:
    pip install httpx
    ollama pull llama3
    ollama serve
"""

import sys
import json
import re
import asyncio
import httpx

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL      = "llama3"
TIMEOUT    = 120.0
CACHE_FILE = "question_cache.json"

# ── Prompts ───────────────────────────────────────────────────────────────────

QUESTION_PROMPT = """\
You are a coding interviewer. Give the candidate ONE random Easy-level DSA problem.

Write it in this exact format and nothing else:

TITLE: <title>
DESCRIPTION: <problem statement>
EXAMPLE 1: Input: <x> | Output: <y>
EXAMPLE 2: Input: <x> | Output: <y>
CONSTRAINT 1: <constraint>
CONSTRAINT 2: <constraint>
"""

EVAL_PROMPT = """\
You are a coding interviewer evaluating a candidate's submission.

=== PROBLEM ===
{problem}

=== SUBMISSION ===
Language: {language}
Code:
{code}

Explanation:
{explanation}

=== INSTRUCTIONS ===
{weighting}

Score the submission from 0 to 10 and give clear feedback.
Reply in this exact format and nothing else:

SCORE: <number 0-10>
VERDICT: <Pass | Partial | Fail>
CORRECTNESS: <one sentence>
COMPLEXITY: <one sentence about time and space>
EDGE CASES: <one sentence>
CODE QUALITY: <one sentence>
EXPLANATION: <one sentence>
FEEDBACK: <2-3 sentences of actionable advice>
"""

# ── Ollama ────────────────────────────────────────────────────────────────────

async def call_ollama(prompt: str, temperature: float = 0.8) -> str:
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            resp = await client.post(
                OLLAMA_URL,
                json={
                    "model": MODEL,
                    "prompt": prompt,
                    "stream": False,
                    "options": {"temperature": temperature},
                },
            )
            resp.raise_for_status()
            return resp.json()["response"].strip()
    except httpx.ConnectError:
        print("\nERROR: Cannot reach Ollama. Run:  ollama serve")
        sys.exit(1)

# ── Parsers ───────────────────────────────────────────────────────────────────

def parse_question(raw: str) -> dict:
    q = {"title": "", "description": "", "examples": [], "constraints": []}
    for line in raw.splitlines():
        line = line.strip()
        if not line:
            continue
        low = line.lower()
        if low.startswith("title:"):
            q["title"] = line.split(":", 1)[1].strip()
        elif low.startswith("description:"):
            q["description"] = line.split(":", 1)[1].strip()
        elif re.match(r"example\s*\d+:", line, re.I):
            q["examples"].append(line.split(":", 1)[1].strip())
        elif re.match(r"constraint\s*\d+:", line, re.I):
            q["constraints"].append(line.split(":", 1)[1].strip())
    if not q["title"]:
        for line in raw.splitlines():
            if line.strip():
                q["title"] = line.strip()
                break
    return q


def parse_result(raw: str) -> dict:
    r = {k: "" for k in
         ["score", "verdict", "correctness", "complexity",
          "edge_cases", "code_quality", "explanation", "feedback"]}
    mapping = {
        "score": "score",
        "verdict": "verdict",
        "correctness": "correctness",
        "complexity": "complexity",
        "edge cases": "edge_cases",
        "code quality": "code_quality",
        "explanation": "explanation",
        "feedback": "feedback",
    }
    for line in raw.splitlines():
        line = line.strip()
        for prefix, key in mapping.items():
            if line.lower().startswith(prefix + ":"):
                r[key] = line.split(":", 1)[1].strip()
                break
    return r

# ── Display ───────────────────────────────────────────────────────────────────

def print_question(q: dict):
    w = 58
    print("\n" + "─" * w)
    print(f"  {q['title']}")
    print("─" * w)
    print(f"\n{q['description']}\n")
    for ex in q["examples"]:
        print(f"  {ex}")
    if q["constraints"]:
        print("\nConstraints:")
        for c in q["constraints"]:
            print(f"  • {c}")
    print("\n" + "─" * w)
    print("  Fill in ans.json then run:  python evaluator.py ans.json")
    print("─" * w + "\n")


def print_result(r: dict):
    try:
        score = float(r["score"])
    except (ValueError, TypeError):
        score = 0.0
    bar  = "█" * int(round(score)) + "░" * (10 - int(round(score)))
    icon = {"pass": "✅", "partial": "⚠️", "fail": "❌"}.get(r["verdict"].lower(), "•")
    w = 58
    print("\n" + "=" * w)
    print(f"  Score   : {score:.1f}/10  [{bar}]")
    print(f"  Verdict : {icon}  {r['verdict']}")
    print("─" * w)
    print(f"  Correctness  : {r['correctness']}")
    print(f"  Complexity   : {r['complexity']}")
    print(f"  Edge cases   : {r['edge_cases']}")
    print(f"  Code quality : {r['code_quality']}")
    print(f"  Explanation  : {r['explanation']}")
    print("─" * w)
    print(f"  Feedback:\n  {r['feedback']}")
    print("=" * w + "\n")

# ── Steps ─────────────────────────────────────────────────────────────────────

async def generate_question():
    print(f"\nModel  : {MODEL}")
    print("Status : Generating question...\n")
    raw = await call_ollama(QUESTION_PROMPT, temperature=0.9)
    question = parse_question(raw)
    with open(CACHE_FILE, "w") as f:
        json.dump(question, f, indent=2)
    print_question(question)


async def evaluate_answer(json_path: str):
    try:
        with open(CACHE_FILE) as f:
            question = json.load(f)
    except FileNotFoundError:
        print("\nERROR: No question found. Run  python evaluator.py  first.\n")
        sys.exit(1)

    try:
        with open(json_path) as f:
            sub = json.load(f)
    except FileNotFoundError:
        print(f"\nERROR: File not found — {json_path}\n")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"\nERROR: Invalid JSON — {e}\n")
        sys.exit(1)

    language    = sub.get("language", "Python")
    code        = sub.get("code", "").strip()
    explanation = sub.get("explanation", "").strip()

    if code and not explanation:
        weighting = "No explanation provided. Focus on code correctness and quality."
    elif explanation and not code:
        weighting = "No code submitted. Evaluate conceptual understanding only. Maximum score is 6."
    else:
        weighting = "Both code and explanation provided. Evaluate both equally."

    problem_text = (
        f"Title: {question['title']}\n"
        f"{question['description']}\n" +
        "\n".join(question.get("examples", []))
    )

    prompt = EVAL_PROMPT.format(
        problem=problem_text,
        language=language,
        code=code or "(none)",
        explanation=explanation or "(none)",
        weighting=weighting,
    )

    print(f"\nModel  : {MODEL}")
    print("Status : Evaluating your submission...\n")
    raw = await call_ollama(prompt, temperature=0.2)
    result = parse_result(raw)
    print_result(result)

# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    asyncio.run(generate_question())

    print("When you are ready, fill in ans.json and press Enter to submit...")
    input()

    asyncio.run(evaluate_answer("ans.json"))