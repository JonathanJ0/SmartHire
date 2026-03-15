#!/usr/bin/env python3
"""
resume_to_json.py
-----------------
Parses a resume (PDF, DOCX, or plain TXT) and extracts key sections
into a structured JSON file.

Usage:
    python resume_to_json.py <resume_file> [output.json]

Dependencies:
    pip install pypdf python-docx
    (Ollama with phi3 must be running locally – no extra Python packages needed)
"""

import sys
import json
import re
import argparse
from pathlib import Path


# ── helpers ──────────────────────────────────────────────────────────────────

def extract_text_from_pdf(path: str) -> str:
    try:
        from pypdf import PdfReader
    except ImportError:
        sys.exit("pypdf not installed.  Run: pip install pypdf")
    reader = PdfReader(path)
    return "\n".join(page.extract_text() or "" for page in reader.pages)


def extract_text_from_docx(path: str) -> str:
    try:
        import docx
    except ImportError:
        sys.exit("python-docx not installed.  Run: pip install python-docx")
    doc = docx.Document(path)
    return "\n".join(p.text for p in doc.paragraphs)


def extract_text_from_txt(path: str) -> str:
    return Path(path).read_text(encoding="utf-8", errors="replace")


def load_resume_text(path: str) -> str:
    ext = Path(path).suffix.lower()
    if ext == ".pdf":
        return extract_text_from_pdf(path)
    elif ext in (".docx", ".doc"):
        return extract_text_from_docx(path)
    elif ext in (".txt", ".md", ""):
        return extract_text_from_txt(path)
    else:
        sys.exit(f"Unsupported file type: {ext}  (supported: .pdf, .docx, .txt)")


# ── rule-based fallback parser ────────────────────────────────────────────────

SECTION_PATTERNS = {
    "contact": re.compile(
        r"(contact|personal\s+info|personal\s+details)", re.I
    ),
    "summary": re.compile(
        r"(summary|objective|profile|about\s+me|professional\s+summary)", re.I
    ),
    "experience": re.compile(
        r"(experience|work\s+history|employment|career)", re.I
    ),
    "education": re.compile(
        r"(education|academic|qualifications|degrees?)", re.I
    ),
    "skills": re.compile(
        r"(skills?|technical\s+skills?|competencies|expertise|technologies)", re.I
    ),
    "certifications": re.compile(
        r"(certif|licenses?|accreditation)", re.I
    ),
    "projects": re.compile(
        r"(projects?|portfolio|work\s+samples?)", re.I
    ),
    "awards": re.compile(
        r"(awards?|honors?|achievements?|recognition)", re.I
    ),
    "languages": re.compile(
        r"(languages?|spoken\s+languages?)", re.I
    ),
    "volunteer": re.compile(
        r"(volunteer|community|extracurricular)", re.I
    ),
    "publications": re.compile(
        r"(publications?|papers?|research|patents?)", re.I
    ),
    "references": re.compile(
        r"(references?)", re.I
    ),
}

EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}")
PHONE_RE = re.compile(r"(\+?\d[\d\s\-().]{7,}\d)")
URL_RE   = re.compile(r"(https?://[^\s]+|linkedin\.com/[^\s]+|github\.com/[^\s]+)", re.I)


def parse_with_rules(text: str) -> dict:
    """
    Simple rule-based parser.  Splits text into sections by detecting
    heading-like lines that match known patterns.
    """
    lines = text.splitlines()
    sections: dict = {k: [] for k in SECTION_PATTERNS}
    current_section = None

    # Try to capture the name from the very first non-empty line
    name = ""
    for line in lines:
        stripped = line.strip()
        if stripped:
            name = stripped
            break

    # Extract contact details globally (they can appear anywhere)
    emails  = EMAIL_RE.findall(text)
    phones  = list({m.strip() for m in PHONE_RE.findall(text)})
    urls    = URL_RE.findall(text)

    contact_info = {
        "name":   name,
        "email":  emails[0] if emails else "",
        "phone":  phones[0] if phones else "",
        "links":  urls,
    }

    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue

        # Detect section headings: short lines that match a known keyword
        matched_section = None
        if len(stripped) < 60:                   # headings are usually short
            for section, pattern in SECTION_PATTERNS.items():
                if pattern.search(stripped):
                    matched_section = section
                    break

        if matched_section:
            current_section = matched_section
        elif current_section:
            sections[current_section].append(stripped)

    # Clean up: remove empty sections
    result = {
        "contact":        contact_info,
        "summary":        " ".join(sections["summary"]),
        "experience":     sections["experience"],
        "education":      sections["education"],
        "skills":         sections["skills"],
        "certifications": sections["certifications"],
        "projects":       sections["projects"],
        "awards":         sections["awards"],
        "languages":      sections["languages"],
        "volunteer":      sections["volunteer"],
        "publications":   sections["publications"],
        "references":     sections["references"],
    }

    # Drop empty sections for a cleaner output
    result = {k: v for k, v in result.items() if v}
    return result


# ── Ollama phi3 parser ────────────────────────────────────────────────────────

def parse_with_ai(text: str, ollama_url: str = "http://localhost:11434") -> dict:
    """
    Uses a local Ollama phi3 model for accurate extraction.
    Falls back to rule-based parsing if Ollama is unavailable.
    """
    try:
        import urllib.request
        import urllib.error
    except ImportError:
        pass  # stdlib – always available

    prompt = f"""You are a resume parser. Extract every important section from the resume
text below and return ONLY a valid JSON object – no markdown, no commentary.

The JSON should have these keys (omit any that are not present in the resume):
  contact        – object with name, email, phone, location, linkedin, github, website
  summary        – string
  experience     – array of objects: {{title, company, location, start_date, end_date, description[]}}
  education      – array of objects: {{degree, institution, location, start_date, end_date, gpa, details[]}}
  skills         – array of strings or categories: {{category, items[]}}
  certifications – array of objects: {{name, issuer, date}}
  projects       – array of objects: {{name, description, technologies[], url}}
  awards         – array of strings
  languages      – array of objects: {{language, proficiency}}
  volunteer      – array of objects: {{role, organisation, date, description}}
  publications   – array of strings
  references     – array of strings

Resume text:
\"\"\"
{text[:12000]}
\"\"\"
"""

    payload = json.dumps({
        "model": "phi3",
        "prompt": prompt,
        "stream": False,
    }).encode("utf-8")

    req = urllib.request.Request(
        f"{ollama_url}/api/generate",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            body = json.loads(resp.read().decode("utf-8"))
            raw = body.get("response", "").strip()
    except urllib.error.URLError as e:
        print(f"[info] Could not reach Ollama at {ollama_url} ({e}) – using rule-based parser.")
        return parse_with_rules(text)
    except Exception as e:
        print(f"[info] Ollama request failed ({e}) – using rule-based parser.")
        return parse_with_rules(text)

    # Strip accidental markdown fences
    raw = re.sub(r"^```[a-z]*\s*", "", raw)
    raw = re.sub(r"\s*```$",       "", raw)

    try:
        return json.loads(raw)
    except json.JSONDecodeError as e:
        print(f"[warning] phi3 returned invalid JSON ({e}). Falling back to rule-based parser.")
        return parse_with_rules(text)


# ── main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Convert a resume (PDF / DOCX / TXT) to a structured JSON file."
    )
    parser.add_argument("resume",      help="Path to the resume file")
    parser.add_argument("output",      nargs="?", help="Output JSON file (default: <resume>.json)")
    parser.add_argument(
        "--no-ai", action="store_true",
        help="Skip AI parsing and use the rule-based parser only"
    )
    parser.add_argument(
        "--ollama-url", default="http://localhost:11434",
        help="Ollama base URL (default: http://localhost:11434)"
    )
    args = parser.parse_args()

    resume_path = args.resume
    output_path = args.output or (Path(resume_path).stem + ".json")

    print(f"[1/3] Loading resume:  {resume_path}")
    text = load_resume_text(resume_path)

    if not text.strip():
        sys.exit("Could not extract any text from the resume file.")

    print(f"[2/3] Parsing resume …")
    if args.no_ai:
        data = parse_with_rules(text)
        method = "rule-based"
    else:
        print(f"       Using Ollama phi3 at {args.ollama_url}")
        data = parse_with_ai(text, ollama_url=args.ollama_url)
        method = "Ollama phi3"

    print(f"[3/3] Saving JSON ({method}):  {output_path}")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print(f"\n✓ Done!  Extracted sections: {', '.join(data.keys())}")
    print(f"  Output written to: {output_path}")


if __name__ == "__main__":
    main()