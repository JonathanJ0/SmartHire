"""
interview_evaluator.py
----------------------
Evaluates interview transcripts using Ollama's llama3 model.

Usage:
    python interview_evaluator.py transcript.txt
    python interview_evaluator.py transcript.txt --role "Software Engineer" --output report.json
    python interview_evaluator.py --text "Interviewer: Tell me about yourself.\nCandidate: ..."

Requirements:
    pip install ollama
    Ollama running locally with llama3 pulled:
        ollama pull llama3
"""

import argparse
import json
import sys
import textwrap
import re
from dataclasses import dataclass, field, asdict
import ollama

# ---------------------------------------------------------------------------
# Evaluation metrics
# ---------------------------------------------------------------------------

METRICS: dict[str, str] = {
    "technical_knowledge": (
        "How well does the candidate demonstrate relevant technical knowledge "
        "or domain expertise? Evaluate depth and accuracy of answers."
    ),
    "problem_solving": (
        "How does the candidate approach problems or hypothetical scenarios? "
        "Look for structured thinking, creativity, and adaptability."
    ),
    "communication_clarity": (
        "How clearly and concisely does the candidate express their ideas? "
        "Consider vocabulary, sentence structure, and avoidance of filler words."
    ),
    "cultural_and_teamwork_fit": (
        "Does the candidate demonstrate collaborative values, empathy, "
        "and the ability to work well in a team environment?"
    ),
    "motivation_and_enthusiasm": (
        "How motivated and genuinely enthusiastic does the candidate appear "
        "about the role and the organisation?"
    ),
    "structured_thinking": (
        "Does the candidate structure answers logically (e.g. STAR method, "
        "clear intro/body/conclusion)? Are responses easy to follow?"
    ),
    
}

# Behavioral anchor rubric — concrete examples prevent score inflation in small LLMs.
# Each band describes *observable evidence*, not vague quality labels.
SCORE_RUBRIC = """
SCORING SCALE (0–10). Match the candidate's ACTUAL evidence to the band below.
If evidence is partial or ambiguous, give the score as 0.

  0   (No Data): The session ended prematurely, the transcript is extremely short, or the candidate provided zero information.
 1–2  (Failing): No evidence of the skill. Answers are absent, incoherent, or
       actively harmful (e.g. blames others, makes up facts, cannot answer at all).
 3–4  (Weak): Minimal evidence. Candidate attempts the topic but responses are
       vague, generic, or unsupported by any concrete example or detail.
 5–6  (Adequate): Some real evidence exists but it is incomplete. One concrete
       example or partial structure present; noticeable gaps remain.
 7–8  (Strong): Clear, specific evidence with at least one concrete example.
       Minor gaps only — the candidate mostly satisfies the metric.
 9–10 (Exceptional): Multiple strong, specific examples. Answers are complete,
       insightful, and go beyond what is expected for the role.

ANTI-INFLATION RULES — you MUST follow these:
- If the transcript is extremely short or the candidate barely spoke, the score MUST be 0.
- If no concrete example is given, the score CANNOT exceed 5.
- If the answer is vague or a single sentence, the score CANNOT exceed 4.
- A score of 7+ requires you to quote or paraphrase a specific line as evidence.
- A score of 9+ requires at least two distinct pieces of strong evidence.
- When in doubt, score LOWER. Generous scoring helps no one.
"""

# System-level instruction injected via the system role for stronger model adherence
SYSTEM_INSTRUCTION = (
    "You are a strict, calibrated interview assessor. "
    "Your job is to score candidates accurately — not kindly. "
    "Inflated scores are a failure of your duty. "
    "You output only valid JSON. No prose, no markdown, no preamble."
)

# Hard safety rails applied in code (not just prompt text) so sparse interviews
# cannot receive inflated scores when the model is over-generous.
MIN_CANDIDATE_WORDS_FOR_SCORING = 35
MIN_CANDIDATE_TURNS_FOR_SCORING = 2

# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

@dataclass
class MetricResult:
    score: float          # 1–10
    justification: str    # evidence-based explanation
    strengths: list[str] = field(default_factory=list)
    improvements: list[str] = field(default_factory=list)


@dataclass
class EvaluationReport:
    role: str
    overall_score: float
    recommendation: str   # "Strong Hire" | "Hire" | "Consider" | "No Hire"
    summary: str
    metrics: dict[str, MetricResult] = field(default_factory=dict)
    red_flags: list[str] = field(default_factory=list)
    notable_positives: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Prompts
# ---------------------------------------------------------------------------

def build_metric_prompt(transcript: str, metric_name: str, description: str, role: str) -> str:
    """
    User-turn prompt kept focused: transcript + metric + output schema.
    Heavy calibration lives in the system role and rubric.
    """
    label = metric_name.replace("_", " ").title()
    return (
        f"ROLE: {role}\n"
        f"METRIC: {label}\n"
        f"DEFINITION: {description}\n\n"
        f"{SCORE_RUBRIC}\n"
        f"TRANSCRIPT:\n{transcript}\n\n"
        f"Return ONLY this JSON (no markdown, no extra text):\n"
        f'{{"score":<0-10>,"justification":"<quote evidence or state NONE>","strengths":["..."],"improvements":["..."]}}'
    )


def build_summary_prompt(transcript: str, role: str, metric_scores: dict) -> str:
    scores_text = "\n".join(
        f"  {k.replace('_', ' ').title()}: {v['score']}/10"
        for k, v in metric_scores.items()
    )
    avg = sum(v["score"] for v in metric_scores.values()) / len(metric_scores)
    return (
        f"ROLE: {role}\n"
        f"METRIC SCORES:\n{scores_text}\n"
        f"ARITHMETIC AVERAGE: {avg:.1f}\n\n"
        f"RECOMMENDATION GUIDE (use average as anchor):\n"
        f"  8.5–10 → Strong Hire\n"
        f"  7.0–8.4 → Hire\n"
        f"  5.0–6.9 → Consider\n"
        f"  below 5 → No Hire\n\n"
        f"TRANSCRIPT:\n{transcript}\n\n"
        f"Return ONLY this JSON (no markdown, no extra text):\n"
        f'{{"overall_score":<1-10 one decimal>,"recommendation":"<Strong Hire|Hire|Consider|No Hire>",'
        f'"summary":"<2-3 sentences>","red_flags":["..."],"notable_positives":["..."]}}'
    )


# ---------------------------------------------------------------------------
# LLM interaction
# ---------------------------------------------------------------------------

def query_llama(prompt: str, model: str = "llama3") -> str:
    """Send a prompt to Ollama using system+user roles for stronger instruction adherence."""
    response = ollama.chat(
        model=model,
        format="json",
        messages=[
            {"role": "system", "content": SYSTEM_INSTRUCTION},
            {"role": "user",   "content": prompt},
        ],
        options={"temperature": 0.1},   # near-zero temp → deterministic, calibrated scoring
    )
    return response["message"]["content"].strip()


def safe_parse_json(raw: str) -> dict:
    """
    Extract and parse JSON. Since we now use Ollama's native JSON format (`format="json"`), 
    the output is guaranteed to be valid JSON. 
    """
    try:
        return json.loads(raw)
    except json.JSONDecodeError as e:
        raise ValueError(
            f"Could not parse JSON. Error: {e}\nRaw response:\n{raw}"
        )


def _extract_candidate_text(transcript: str) -> str:
    """
    Extract candidate utterances from transcript blocks like:
      [CANDIDATE]
      ...text...
    """
    parts = re.findall(r"\[CANDIDATE\]\s*(.*?)(?=\n\[[A-Z_]+\]|\Z)", transcript, flags=re.S)
    cleaned = [p.strip() for p in parts if p.strip()]
    return "\n".join(cleaned)


def _candidate_evidence_stats(transcript: str) -> tuple[int, int]:
    candidate_text = _extract_candidate_text(transcript)
    if not candidate_text:
        return 0, 0
    words = len(re.findall(r"\b\w+\b", candidate_text))
    turns = len(re.findall(r"\[CANDIDATE\]\s*\S", transcript))
    return words, turns


# ---------------------------------------------------------------------------
# Core evaluator
# ---------------------------------------------------------------------------

def evaluate_transcript(
    transcript: str,
    role: str = "Unspecified Role",
    model: str = "llama3",
    verbose: bool = False,
    job_description: str = "",
    requirements: list = None,
) -> EvaluationReport:
    """
    Evaluate a transcript across all metrics and return an EvaluationReport.

    Each metric is assessed in an independent prompt to reduce anchoring bias.
    """
    eval_metrics = dict(METRICS)
    if requirements:
        reqs_str = "\n".join(f"- {r}" for r in requirements)
        eval_metrics["role_requirements_fit"] = (
            f"How well did the candidate demonstrate the specific requirements: {reqs_str}? "
            f"Did their technical answers satisfy the needs of the {job_description}?"
        )

    candidate_words, candidate_turns = _candidate_evidence_stats(transcript)
    sparse_evidence = (
        candidate_words < MIN_CANDIDATE_WORDS_FOR_SCORING
        or candidate_turns < MIN_CANDIDATE_TURNS_FOR_SCORING
    )

    # If there is too little candidate evidence, bypass LLM scoring entirely.
    if sparse_evidence:
        metrics = {
            metric_name: MetricResult(
                score=0.0,
                justification=(
                    "Insufficient candidate evidence in transcript to score this metric "
                    f"({candidate_words} words across {candidate_turns} candidate turn(s))."
                ),
                strengths=[],
                improvements=[
                    "Provide fuller responses with concrete examples.",
                    "Answer more interview questions before ending the session.",
                ],
            )
            for metric_name in eval_metrics.keys()
        }
        summary = (
            "The interview transcript contains too little candidate evidence to evaluate fairly. "
            "Scores are set to 0 to avoid inflated results from sparse responses."
        )
        return EvaluationReport(
            role=role,
            overall_score=0.0,
            recommendation="No Hire",
            summary=summary,
            metrics=metrics,
            red_flags=["Insufficient candidate participation."],
            notable_positives=[],
        )

    metric_results: dict[str, MetricResult] = {}
    raw_scores: dict[str, dict] = {}

    print(f"\n📋 Evaluating transcript for: {role}")
    print(f"   Model : {model}")
    print(f"   Metrics: {len(eval_metrics)}\n")

    for i, (metric_name, description) in enumerate(eval_metrics.items(), 1):
        label = metric_name.replace("_", " ").title()
        print(f"  [{i}/{len(eval_metrics)}] Scoring '{label}' ...", end=" ", flush=True)

        prompt = build_metric_prompt(transcript, metric_name, description, role)
        raw = query_llama(prompt, model)

        if verbose:
            print(f"\n--- RAW RESPONSE for {metric_name} ---\n{raw}\n")

        parsed = safe_parse_json(raw)
        result = MetricResult(
            score=float(parsed["score"]),
            justification=parsed.get("justification", ""),
            strengths=parsed.get("strengths", []),
            improvements=parsed.get("improvements", []),
        )
        metric_results[metric_name] = result
        raw_scores[metric_name] = {"score": result.score}
        print(f"✓  ({result.score}/10)")

    # Summary pass
    print("\n  [Final] Generating holistic summary ...", end=" ", flush=True)
    summary_prompt = build_summary_prompt(transcript, role, raw_scores)
    raw_summary = query_llama(summary_prompt, model)

    if verbose:
        print(f"\n--- RAW SUMMARY RESPONSE ---\n{raw_summary}\n")

    parsed_summary = safe_parse_json(raw_summary)
    print("✓\n")

    return EvaluationReport(
        role=role,
        overall_score=float(parsed_summary.get("overall_score", 0)),
        recommendation=parsed_summary.get("recommendation", "Consider"),
        summary=parsed_summary.get("summary", ""),
        metrics=metric_results,
        red_flags=parsed_summary.get("red_flags", []),
        notable_positives=parsed_summary.get("notable_positives", []),
    )


# ---------------------------------------------------------------------------
# Report rendering
# ---------------------------------------------------------------------------

RECOMMENDATION_EMOJI = {
    "Strong Hire": "🟢",
    "Hire": "🟡",
    "Consider": "🟠",
    "No Hire": "🔴",
}

def render_report(report: EvaluationReport) -> str:
    """Render a human-readable evaluation report."""
    emoji = RECOMMENDATION_EMOJI.get(report.recommendation, "⚪")
    lines = [
        "=" * 64,
        f"  INTERVIEW EVALUATION REPORT",
        f"  Role : {report.role}",
        f"  Overall Score : {report.overall_score:.1f} / 10",
        f"  Recommendation: {emoji} {report.recommendation}",
        "=" * 64,
        "",
        "SUMMARY",
        "-" * 40,
        textwrap.fill(report.summary, width=64),
        "",
    ]

    if report.notable_positives:
        lines += ["✅ NOTABLE POSITIVES", "-" * 40]
        for pos in report.notable_positives:
            lines.append(f"  • {pos}")
        lines.append("")

    if report.red_flags:
        lines += ["⚠️  RED FLAGS", "-" * 40]
        for flag in report.red_flags:
            lines.append(f"  • {flag}")
        lines.append("")

    lines += ["METRIC BREAKDOWN", "-" * 40]
    for metric_name, result in report.metrics.items():
        label = metric_name.replace("_", " ").title()
        bar = "█" * int(result.score) + "░" * (10 - int(result.score))
        lines.append(f"\n  {label}")
        lines.append(f"  Score : {result.score:.1f}/10  [{bar}]")
        lines.append(f"  {textwrap.fill(result.justification, width=60, subsequent_indent='  ')}")
        if result.strengths:
            lines.append(f"  Strengths    : {', '.join(result.strengths)}")
        if result.improvements:
            lines.append(f"  Improvements : {', '.join(result.improvements)}")

    lines += ["", "=" * 64]
    return "\n".join(lines)


def report_to_dict(report: EvaluationReport) -> dict:
    """Convert EvaluationReport to a JSON-serialisable dict."""
    d = asdict(report)
    return d


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Evaluate an interview transcript with llama3 via Ollama."
    )
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("transcript_file", nargs="?", help="Path to transcript .txt file")
    source.add_argument("--text", help="Transcript text passed directly as a string")

    parser.add_argument("--role", default="Unspecified Role",
                        help="Job role being interviewed for (default: 'Unspecified Role')")
    parser.add_argument("--model", default="llama3",
                        help="Ollama model to use (default: llama3)")
    parser.add_argument("--output", help="Save JSON report to this file path")
    parser.add_argument("--verbose", action="store_true",
                        help="Print raw LLM responses for debugging")
    args = parser.parse_args()

    # Load transcript
    if args.text:
        transcript = args.text
    else:
        try:
            with open(args.transcript_file, "r", encoding="utf-8") as f:
                transcript = f.read()
        except FileNotFoundError:
            print(f"Error: File '{args.transcript_file}' not found.", file=sys.stderr)
            sys.exit(1)

    if not transcript.strip():
        print("Error: Transcript is empty.", file=sys.stderr)
        sys.exit(1)

    # Run evaluation
    try:
        report = evaluate_transcript(
            transcript=transcript,
            role=args.role,
            model=args.model,
            verbose=args.verbose,
        )
    except Exception as e:
        print(f"\n❌ Evaluation failed: {e}", file=sys.stderr)
        sys.exit(1)

    # Print human-readable report
    print(render_report(report))

    # Optionally save JSON
    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(report_to_dict(report), f, indent=2)
        print(f"\n💾 JSON report saved to: {args.output}")


if __name__ == "__main__":
    main()