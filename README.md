# UmaMaj

AI-powered interview practice platform with:
- interviewee and interviewer web apps (`my-app`)
- FastAPI backend services (`backend`)
- AI-driven interview, speech, monitor, and coding evaluation pipelines

## Project Structure

- `my-app/` - Next.js frontend (App Router, React, Tailwind)
- `backend/` - FastAPI server and Python modules for interview workflows
- `backend/python_modules/` - interview generation/evaluation, speech analysis, coding evaluation, and utilities
- `backend/data/` - generated runtime artifacts (transcripts, evaluations, stats, resume/job data)

## Core Features

- Resume upload and parsing
- Role/job-based AI interview sessions
- Webcam monitoring telemetry
- Speech analytics (filler words, confidence metrics)
- Post-interview coding exercise:
  - coding question generation
  - code + spoken explanation submission
  - AI coding evaluation
- Interviewer dashboard:
  - session list
  - transcript/evaluation details
  - coding evaluation visibility

## Prerequisites

- Node.js 18+ (recommended latest LTS)
- Python 3.10+
- Ollama installed and running locally
- Required Ollama models pulled:
  - `mistral` (interview chat flow)
  - `llama3` (evaluation flows, coding evaluation)

## Setup

### 1) Backend

From `backend/`:

```bash
pip install -r requirements.txt
```

Start Ollama and pull models:

```bash
ollama serve
ollama pull mistral
ollama pull llama3
```

Run API server:

```bash
py .\server.py
```

Backend default URL: `http://localhost:8000`

### 2) Frontend

From `my-app/`:

```bash
npm install
npm run dev
```

Frontend default URL: `http://localhost:3000`

If needed, set:

```bash
NEXT_PUBLIC_BACKEND_URL=http://localhost:8000
```

## Typical End-to-End Flow

1. Interviewee uploads resume and chooses a role/job.
2. Interview session starts (AI interviewer + optional monitor telemetry).
3. Interview ends and user is routed to coding page.
4. Coding page requests a generated question from backend.
5. Interviewee submits code + spoken explanation.
6. Backend stores coding evaluation in `backend/data/coding_evaluation_<session_id>.json`.
7. Interviewer dashboard shows session-level details, including coding evaluation.

## Key Backend Endpoints

- `POST /api/interview/start`
- `POST /api/interview/message`
- `POST /api/interview/end`
- `POST /api/coding/question`
- `POST /api/coding/submit`
- `GET /api/dashboard/interviews`
- `GET /api/dashboard/interviews/{session_id}`

## Notes

- Runtime/generated files are stored under `backend/data/`.
- AI-dependent endpoints require local Ollama availability.
- Existing `my-app/README.md` is the default Next.js template; this root README is the project-wide guide.
