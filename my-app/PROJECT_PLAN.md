# Interview Evaluation Application – Project Plan

## Overview
A dual-interface app: **Interviewer** (evaluator dashboard) and **Interviewee** (live interview with video + AI chat).

---

## 1. Interfaces

### 1.1 Interviewee Interface
- **Video**: Live camera capture (getUserMedia) for the session.
- **Chat**: Real-time chat with an AI interviewer (messages, send input).
- **Flow**: Join session → video on → converse via chat → session ends → optional feedback.

### 1.2 Interviewer Interface
- **Dashboard**: List/table of interviewees and their sessions.
- **Performance view**: Per-session or per-candidate metrics (e.g. scores, duration, summary).
- **Detail view**: Drill into a single candidate/session (transcript, scores, notes).

---

## 2. Tech Stack (Current)

| Layer      | Choice                |
|-----------|------------------------|
| Frontend  | Next.js 16, React 19, Tailwind CSS 4 |
| Routing   | App Router             |
| Backend   | TBD (API routes + DB later) |
| AI Chat   | TBD (e.g. OpenAI, local LLM) |
| Video     | Browser MediaDevices API |

---

## 3. Frontend Structure (Phase 1)

```
app/
  layout.tsx          # Root layout, fonts, nav
  page.tsx            # Landing / role picker (Interviewer | Interviewee)
  globals.css         # Tailwind + theme
  interviewee/
    page.tsx          # Interviewee UI: video + chat
    layout.tsx        # (optional) interviewee layout
  interviewer/
    page.tsx          # Dashboard: list of candidates/sessions
    [id]/page.tsx     # Single candidate/session performance detail
components/
  interviewee/        # VideoCapture, ChatBox, SessionControls
  interviewer/        # CandidateTable, PerformanceCard, ScoreBreakdown
  shared/             # Button, Card, LayoutShell
```

---

## 4. Implementation Phases

### Phase 1 – Frontend (current)
- [x] Plan and routing
- [ ] Landing page with role selection
- [ ] Interviewee: video capture + chat UI (mock AI)
- [ ] Interviewer: dashboard with mock candidate/session data
- [ ] Interviewer: detail page for one session

### Phase 2 – Backend & persistence
- API routes for sessions, candidates, messages
- Database (e.g. SQLite/Postgres) for sessions and evaluations
- WebSocket or polling for live chat (if needed)

### Phase 3 – AI integration
- Connect chat to LLM (e.g. OpenAI API)
- Optional: speech-to-text for interviewee, or voice for AI

### Phase 4 – Evaluation logic
- Define evaluation criteria and scoring
- Store and display scores on interviewer dashboard
- Optional: automated scoring from transcript/sentiment

---

## 5. Next Steps
1. Implement frontend layout and navigation.
2. Build interviewee page (video + chat).
3. Build interviewer dashboard and detail page.
4. Add backend and AI in later phases.
