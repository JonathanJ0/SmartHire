"""
Backend API for the Interview Evaluation application.

This wraps the existing `backend/venv/interview_monitor.py` logic and exposes it
over HTTP so the Next.js frontend can stream webcam frames for monitoring.
"""

from __future__ import annotations

import base64
import json
import uuid
import threading
from dataclasses import asdict
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from typing import Any, Dict, Optional

import cv2  # type: ignore
import numpy as np
import requests
from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from starlette.responses import Response


def _load_interview_monitor_module():
    here = Path(__file__).resolve().parent
    mod_path = here / "venv" / "interview_monitor.py"
    if not mod_path.exists():
        raise RuntimeError(f"Cannot find interview_monitor.py at {mod_path}")

    spec = spec_from_file_location("interview_monitor", str(mod_path))
    if spec is None or spec.loader is None:
        raise RuntimeError("Failed to create module spec for interview_monitor.py")
    mod = module_from_spec(spec)
    spec.loader.exec_module(mod)  # type: ignore[attr-defined]
    return mod


interview_monitor = _load_interview_monitor_module()


def _load_speech_monitor_module():
    here = Path(__file__).resolve().parent
    mod_path = here / "venv" / "speech_monitor2.py"
    if not mod_path.exists():
        raise RuntimeError(f"Cannot find speech_monitor2.py at {mod_path}")

    spec = spec_from_file_location("speech_monitor2", str(mod_path))
    if spec is None or spec.loader is None:
        raise RuntimeError("Failed to create module spec for speech_monitor2.py")
    mod = module_from_spec(spec)
    spec.loader.exec_module(mod)  # type: ignore[attr-defined]
    return mod


speech_monitor = _load_speech_monitor_module()


def _load_resume_to_json_module():
    here = Path(__file__).resolve().parent
    mod_path = here / "venv" / "resume_to_json.py"
    if not mod_path.exists():
        raise RuntimeError(f"Cannot find resume_to_json.py at {mod_path}")

    spec = spec_from_file_location("resume_to_json", str(mod_path))
    if spec is None or spec.loader is None:
        raise RuntimeError("Failed to create module spec for resume_to_json.py")
    mod = module_from_spec(spec)
    spec.loader.exec_module(mod)  # type: ignore[attr-defined]
    return mod


resume_to_json = _load_resume_to_json_module()


def _load_interview_module():
    here = Path(__file__).resolve().parent
    mod_path = here / "venv" / "interview.py"
    if not mod_path.exists():
        raise RuntimeError(f"Cannot find interview.py at {mod_path}")

    spec = spec_from_file_location("interview", str(mod_path))
    if spec is None or spec.loader is None:
        raise RuntimeError("Failed to create module spec for interview.py")
    mod = module_from_spec(spec)
    spec.loader.exec_module(mod)  # type: ignore[attr-defined]
    return mod


interview = _load_interview_module()


def _load_tts_module():
    here = Path(__file__).resolve().parent
    mod_path = here / "venv" / "tts.py"
    if not mod_path.exists():
        raise RuntimeError(f"Cannot find tts.py at {mod_path}")

    spec = spec_from_file_location("tts", str(mod_path))
    if spec is None or spec.loader is None:
        raise RuntimeError("Failed to create module spec for tts.py")
    mod = module_from_spec(spec)
    spec.loader.exec_module(mod)  # type: ignore[attr-defined]
    return mod


tts = _load_tts_module()


def _load_interview_evaluator_module():
    here = Path(__file__).resolve().parent
    mod_path = here / "venv" / "interview_evaluator2.py"
    if not mod_path.exists():
        raise RuntimeError(f"Cannot find interview_evaluator2.py at {mod_path}")

    spec = spec_from_file_location("interview_evaluator", str(mod_path))
    if spec is None or spec.loader is None:
        raise RuntimeError("Failed to create module spec for interview_evaluator2.py")
    mod = module_from_spec(spec)
    spec.loader.exec_module(mod)  # type: ignore[attr-defined]
    return mod


interview_evaluator = _load_interview_evaluator_module()


class StartSessionRequest(BaseModel):
    candidate_name: str = Field(default="Candidate")


class StartSessionResponse(BaseModel):
    session_id: str


class FrameRequest(BaseModel):
    session_id: str
    image_data_url: str = Field(
        description="A data URL like 'data:image/jpeg;base64,...' (preferred) or raw base64."
    )
    return_overlay: bool = False


class FrameResponse(BaseModel):
    session_id: str
    frame_count: int
    alerts_count: int
    last_alert: Optional[Dict[str, Any]] = None
    gaze: Optional[Dict[str, str]] = None
    stats: Dict[str, Any]
    overlay_data_url: Optional[str] = None


class EndSessionRequest(BaseModel):
    session_id: str


class EndSessionResponse(BaseModel):
    report: Dict[str, Any]


class SpeechAnalyseRequest(BaseModel):
    text: str = Field(description="Transcript text from the interviewee microphone.")
    duration_seconds: Optional[float] = Field(
        default=None,
        description="Approximate speaking duration for this text. If omitted, will be estimated from word count.",
    )
    interview_session_id: Optional[str] = Field(
        default=None,
        description="Optional interview_session_id to attach speech stats to an interview.",
    )


class SpeechAnalyseResponse(BaseModel):
    score: int
    grade: str
    breakdown: Dict[str, Any]
    stats: Dict[str, Any]


class ResumeUploadResponse(BaseModel):
    resume_id: str
    stored_json_path: str
    extracted_keys: list[str]
    contact_name: str = ""
    parsed: Dict[str, Any]


class InterviewStartRequest(BaseModel):
    resume_id: str
    role: str = Field(default="Software Engineer")


class InterviewStartResponse(BaseModel):
    interview_session_id: str
    opening_message: str


class InterviewMessageRequest(BaseModel):
    interview_session_id: str
    user_text: str


class InterviewMessageResponse(BaseModel):
    assistant_message: str
    is_concluded: bool


class TtsRequest(BaseModel):
    text: str
    rate: int = 175
    volume: float = 1.0
    voice_index: int = 0


class InterviewEndRequest(BaseModel):
    interview_session_id: str


app = FastAPI(title="UmaMaj Backend", version="0.1.0")

# Dev-friendly CORS (tighten for production)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


_lock = threading.Lock()
_monitors: Dict[str, Any] = {}
_interviews: Dict[str, Dict[str, Any]] = {}


def _data_dir() -> Path:
    d = Path(__file__).resolve().parent / "data"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _safe_read_json(path: Path) -> Optional[dict]:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _extract_header_value(transcript_text: str, key: str) -> str:
    # Looks for lines like "  Role: X" or "  Resume ID: Y"
    for line in transcript_text.splitlines()[:30]:
        if line.strip().lower().startswith(key.lower() + ":"):
            return line.split(":", 1)[1].strip()
    return ""


def _ollama_chat(messages: list[dict], model: str = "mistral") -> str:
    """
    Call Ollama's /api/chat and return the assistant message content.
    `interview.py` streams tokens to stdout; for the web we use stream=False.
    """
    try:
        r = requests.post(
            "http://localhost:11434/api/chat",
            json={"model": model, "messages": messages, "stream": False},
            timeout=180,
        )
        r.raise_for_status()
        body = r.json()
        content = (body.get("message") or {}).get("content") or ""
        return str(content).strip()
    except requests.RequestException as e:
        raise HTTPException(
            status_code=503,
            detail=f"Could not reach Ollama at localhost:11434 ({e}). Start it with `ollama serve`.",
        ) from e


def _decode_image_data_url(image_data_url: str) -> np.ndarray:
    if "," in image_data_url and image_data_url.strip().startswith("data:"):
        b64 = image_data_url.split(",", 1)[1]
    else:
        b64 = image_data_url
    try:
        data = base64.b64decode(b64, validate=False)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid base64 image: {e}") from e

    arr = np.frombuffer(data, dtype=np.uint8)
    frame = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if frame is None:
        raise HTTPException(status_code=400, detail="Could not decode image.")
    return frame


def _encode_jpeg_data_url(frame_bgr: np.ndarray, quality: int = 70) -> str:
    ok, buf = cv2.imencode(".jpg", frame_bgr, [int(cv2.IMWRITE_JPEG_QUALITY), quality])
    if not ok:
        raise HTTPException(status_code=500, detail="Could not encode overlay JPEG.")
    b64 = base64.b64encode(buf.tobytes()).decode("ascii")
    return f"data:image/jpeg;base64,{b64}"


@app.get("/health")
def health():
    return {"ok": True}


@app.post("/api/session/start", response_model=StartSessionResponse)
def start_session(req: StartSessionRequest):
    monitor = interview_monitor.InterviewMonitor(
        candidate_name=req.candidate_name, save_report=False
    )
    with _lock:
        _monitors[monitor.session_id] = monitor
    return StartSessionResponse(session_id=monitor.session_id)


@app.post("/api/session/frame", response_model=FrameResponse)
def process_frame(req: FrameRequest):
    with _lock:
        monitor = _monitors.get(req.session_id)
    if monitor is None:
        raise HTTPException(status_code=404, detail="Unknown session_id")

    frame = _decode_image_data_url(req.image_data_url)
    overlay = monitor.process_frame(frame)

    last_alert = None
    if getattr(monitor, "alerts", None):
        last_alert = asdict(monitor.alerts[-1])

    gaze = None
    if getattr(monitor, "last_gaze", None):
        gaze = asdict(monitor.last_gaze)

    stats = {
        "no_face_frames": getattr(monitor, "no_face_frames", 0),
        "multi_face_frames": getattr(monitor, "multi_face_frames", 0),
        "gaze_away_events": getattr(monitor, "gaze_away_events", 0),
        "suspicion_score": monitor._suspicion_score()
        if hasattr(monitor, "_suspicion_score")
        else None,
    }

    overlay_data_url = _encode_jpeg_data_url(overlay) if req.return_overlay else None

    return FrameResponse(
        session_id=req.session_id,
        frame_count=getattr(monitor, "frame_count", 0),
        alerts_count=len(getattr(monitor, "alerts", [])),
        last_alert=last_alert,
        gaze=gaze,
        stats=stats,
        overlay_data_url=overlay_data_url,
    )


@app.post("/api/session/end", response_model=EndSessionResponse)
def end_session(req: EndSessionRequest):
    with _lock:
        monitor = _monitors.pop(req.session_id, None)
    if monitor is None:
        raise HTTPException(status_code=404, detail="Unknown session_id")

    report = monitor.generate_report()

    # Persist monitoring results into data folder as well.
    backend_root = Path(__file__).resolve().parent
    data_dir = backend_root / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    out_path = data_dir / f"monitor_report_{req.session_id}.json"
    out_path.write_text(json.dumps(asdict(report), indent=2), encoding="utf-8")

    return EndSessionResponse(report=asdict(report))


@app.post("/api/speech/analyse-text", response_model=SpeechAnalyseResponse)
def analyse_speech(req: SpeechAnalyseRequest):
    """
    Lightweight integration with `speech_monitor2.py` for text-only analysis.

    The browser already performs speech-to-text so this endpoint focuses on
    filler-word detection and scoring using the monitor's scoring logic.
    """
    text = req.text.strip()
    if not text:
        raise HTTPException(status_code=400, detail="Text must not be empty.")

    # Build a minimal SessionStats from the provided text.
    SessionStats = getattr(speech_monitor, "SessionStats", None)
    detect_fillers = getattr(speech_monitor, "detect_fillers", None)
    calculate_score = getattr(speech_monitor, "calculate_score", None)

    if SessionStats is None or detect_fillers is None or calculate_score is None:
        raise HTTPException(
            status_code=500,
            detail="speech_monitor2 module missing required symbols.",
        )

    words = text.split()
    total_words = len(words)

    # Estimate durations if not provided (assume ~130 WPM when not specified).
    if req.duration_seconds is not None and req.duration_seconds > 0:
        session_duration = float(req.duration_seconds)
        speaking_time = session_duration
    else:
        speaking_time = max(total_words / 130 * 60.0, 1.0)
        session_duration = speaking_time

    stats = SessionStats()
    stats.total_words = total_words
    stats.speaking_time = speaking_time
    stats.session_duration = session_duration
    stats.avg_confidence = 0.85
    stats.confidence_samples = 1

    # Filler detection.
    fillers = detect_fillers(text)
    for word, _ in fillers:
        stats.total_fillers += 1
        stats.filler_breakdown[word] = stats.filler_breakdown.get(word, 0) + 1

    score, grade, breakdown = calculate_score(stats)

    stats_dict = {
        "total_words": stats.total_words,
        "total_fillers": stats.total_fillers,
        "filler_breakdown": stats.filler_breakdown,
        "session_duration": stats.session_duration,
        "speaking_time": stats.speaking_time,
        "avg_confidence": stats.avg_confidence,
    }

    if req.interview_session_id:
        with _lock:
            sess = _interviews.get(req.interview_session_id)
            if sess is not None:
                speech_events = sess.setdefault("speech_events", [])
                speech_events.append(
                    {
                        "text": text,
                        "score": score,
                        "grade": grade,
                        "breakdown": breakdown,
                        "stats": stats_dict,
                    }
                )

    return SpeechAnalyseResponse(
        score=score,
        grade=grade,
        breakdown=breakdown,
        stats=stats_dict,
    )


@app.post("/api/resume/upload", response_model=ResumeUploadResponse)
async def upload_resume(file: UploadFile = File(...)):
    """
    Upload a resume and parse it using the **rule-based** path from `resume_to_json.py`.
    No AI parsing is used.
    """
    filename = (file.filename or "resume").strip()
    ext = Path(filename).suffix.lower()
    if ext not in {".pdf", ".docx", ".doc", ".txt", ".md"}:
        raise HTTPException(
            status_code=400,
            detail="Unsupported file type. Use PDF, DOCX/DOC, or TXT.",
        )

    backend_root = Path(__file__).resolve().parent
    data_dir = backend_root / "data"
    data_dir.mkdir(parents=True, exist_ok=True)

    resume_id = str(uuid.uuid4())
    raw_path = data_dir / f"resume_raw_{resume_id}{ext}"
    json_path = data_dir / f"resume_prep_{resume_id}.json"

    try:
        content = await file.read()
        raw_path.write_bytes(content)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to store file: {e}") from e

    try:
        text = resume_to_json.load_resume_text(str(raw_path))
        if not text.strip():
            raise HTTPException(
                status_code=400,
                detail="Could not extract any text from the resume file.",
            )

        parsed = resume_to_json.parse_with_rules(text)  # rule-based only (no AI)
        json_path.write_text(json.dumps(parsed, indent=2, ensure_ascii=False), encoding="utf-8")
    except SystemExit as e:
        # resume_to_json uses sys.exit() when dependencies are missing
        raise HTTPException(status_code=500, detail=str(e)) from e
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Resume parsing failed: {e}") from e

    contact_name = ""
    if isinstance(parsed, dict):
        contact = parsed.get("contact")
        if isinstance(contact, dict):
            contact_name = str(contact.get("name") or "")

    return ResumeUploadResponse(
        resume_id=resume_id,
        stored_json_path=str(json_path),
        extracted_keys=list(parsed.keys()) if isinstance(parsed, dict) else [],
        contact_name=contact_name,
        parsed=parsed if isinstance(parsed, dict) else {},
    )


@app.get("/api/resume/{resume_id}")
def get_resume(resume_id: str):
    backend_root = Path(__file__).resolve().parent
    json_path = backend_root / "data" / f"resume_prep_{resume_id}.json"
    if not json_path.exists():
        raise HTTPException(status_code=404, detail="Resume not found.")
    try:
        return json.loads(json_path.read_text(encoding="utf-8"))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read resume JSON: {e}") from e


@app.post("/api/interview/start", response_model=InterviewStartResponse)
def start_interview(req: InterviewStartRequest):
    backend_root = Path(__file__).resolve().parent
    json_path = backend_root / "data" / f"resume_prep_{req.resume_id}.json"
    if not json_path.exists():
        raise HTTPException(status_code=404, detail="Resume not found.")

    try:
        resume = json.loads(json_path.read_text(encoding="utf-8"))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read resume JSON: {e}") from e

    system_prompt = interview.build_system_prompt(resume, req.role)
    messages = [{"role": "system", "content": system_prompt}]

    # same seed as `interview.py` to trigger the first interviewer question
    seed = "Hi, I'm ready for the interview."
    messages.append({"role": "user", "content": seed})
    opening = _ollama_chat(messages, model=getattr(interview, "MODEL", "mistral"))
    messages.append({"role": "assistant", "content": opening})

    interview_session_id = str(uuid.uuid4())
    with _lock:
        _interviews[interview_session_id] = {
            "resume_id": req.resume_id,
            "role": req.role,
            "messages": messages,
            "speech_events": [],
        }

    return InterviewStartResponse(
        interview_session_id=interview_session_id, opening_message=opening
    )


@app.post("/api/interview/message", response_model=InterviewMessageResponse)
def interview_message(req: InterviewMessageRequest):
    with _lock:
        sess = _interviews.get(req.interview_session_id)
    if sess is None:
        raise HTTPException(status_code=404, detail="Unknown interview_session_id")

    user_text = req.user_text.strip()
    if not user_text:
        raise HTTPException(status_code=400, detail="user_text must not be empty.")

    messages: list[dict] = sess["messages"]
    messages.append({"role": "user", "content": user_text})
    assistant = _ollama_chat(messages, model=getattr(interview, "MODEL", "mistral"))
    messages.append({"role": "assistant", "content": assistant})

    concluded = False
    try:
        concluded = bool(interview.is_closing(assistant))
    except Exception:
        concluded = False

    with _lock:
        _interviews[req.interview_session_id]["messages"] = messages

    # If concluded, persist transcript, evaluation, and speech statistics.
    if concluded:
        _finalise_interview_session(req.interview_session_id)

    return InterviewMessageResponse(
        assistant_message=assistant,
        is_concluded=concluded,
    )


@app.post("/api/tts")
def tts_audio(req: TtsRequest):
    """
    Generate speech audio for the given text and return it as WAV bytes.

    Note: `backend/venv/tts.py` primarily speaks aloud on the server, but for the
    web we generate an audio file using the same underlying engine (pyttsx3).
    """
    text = (req.text or "").strip()
    if not text:
        raise HTTPException(status_code=400, detail="Text must not be empty.")

    try:
        import tempfile
        import os
        import pyttsx3

        engine = pyttsx3.init()
        engine.setProperty("rate", int(req.rate))
        engine.setProperty("volume", float(req.volume))
        voices = engine.getProperty("voices")
        if voices and 0 <= int(req.voice_index) < len(voices):
            engine.setProperty("voice", voices[int(req.voice_index)].id)

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            out_path = f.name

        engine.save_to_file(text, out_path)
        engine.runAndWait()

        data = Path(out_path).read_bytes()
        try:
            os.unlink(out_path)
        except Exception:
            pass

        return Response(content=data, media_type="audio/wav")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"TTS failed: {e}") from e


def _finalise_interview_session(session_id: str):
    with _lock:
        sess = _interviews.get(session_id)
    if not sess:
        return

    backend_root = Path(__file__).resolve().parent
    data_dir = backend_root / "data"
    data_dir.mkdir(parents=True, exist_ok=True)

    role = sess.get("role", "Unspecified Role")
    resume_id = sess.get("resume_id", "")
    messages: list[dict] = sess.get("messages") or []

    # Build transcript text similar to CLI tool.
    lines = [
        "=" * 60,
        "  INTERVIEW TRANSCRIPT",
        f"  Role: {role}",
        f"  Resume ID: {resume_id}",
        f"  Session ID: {session_id}",
        "=" * 60,
        "",
    ]
    for msg in messages:
        if msg.get("role") == "system":
            continue
        speaker = "INTERVIEWER" if msg.get("role") == "assistant" else "CANDIDATE"
        lines.append(f"[{speaker}]")
        lines.append(str(msg.get("content", "")))
        lines.append("")
    lines += ["=" * 60, "  END OF TRANSCRIPT", "=" * 60]
    transcript_text = "\n".join(lines)

    transcript_path = data_dir / f"interview_transcript_{session_id}.txt"
    transcript_path.write_text(transcript_text, encoding="utf-8")

    # Run evaluation via interview_evaluator (if available).
    try:
        evaluate_transcript = getattr(interview_evaluator, "evaluate_transcript", None)
        report_to_dict = getattr(interview_evaluator, "report_to_dict", None)
        if evaluate_transcript and report_to_dict:
            eval_report = evaluate_transcript(
                transcript=transcript_text,
                role=role,
            )
            eval_dict = report_to_dict(eval_report)
            eval_path = data_dir / f"interview_evaluation_{session_id}.json"
            eval_path.write_text(json.dumps(eval_dict, indent=2), encoding="utf-8")
    except Exception:
        # Evaluation is best-effort; do not fail the request.
        pass

    # Persist speech statistics if we collected any.
    speech_events = sess.get("speech_events") or []
    if speech_events:
        agg: Dict[str, Any] = {
            "total_words": 0,
            "total_fillers": 0,
            "filler_breakdown": {},
            "utterance_count": len(speech_events),
        }
        for ev in speech_events:
            st = ev.get("stats") or {}
            agg["total_words"] += st.get("total_words", 0)
            agg["total_fillers"] += st.get("total_fillers", 0)
            fb = st.get("filler_breakdown") or {}
            for word, count in fb.items():
                agg["filler_breakdown"][word] = agg["filler_breakdown"].get(word, 0) + count

        speech_path = data_dir / f"speech_stats_{session_id}.json"
        speech_path.write_text(
            json.dumps(
                {
                    "session_id": session_id,
                    "role": role,
                    "resume_id": resume_id,
                    "aggregate": agg,
                    "events": speech_events,
                },
                indent=2,
            ),
            encoding="utf-8",
        )


@app.post("/api/interview/end")
def end_interview(req: InterviewEndRequest):
    """
    Explicitly finalise an interview session when the user clicks 'End session'.
    This ensures transcript, evaluation, and speech statistics are saved even if
    the AI interviewer did not send a closing message.
    """
    _finalise_interview_session(req.interview_session_id)
    return {"ok": True}


@app.get("/api/dashboard/interviews")
def list_interviews():
    """
    List completed interview sessions from files in backend/data.
    Returns lightweight rows for the interviewer dashboard.
    """
    d = _data_dir()
    rows = []
    for transcript_path in sorted(d.glob("interview_transcript_*.txt"), reverse=True):
        session_id = transcript_path.stem.replace("interview_transcript_", "")
        transcript_text = transcript_path.read_text(encoding="utf-8", errors="replace")
        resume_id = _extract_header_value(transcript_text, "Resume ID")
        role = _extract_header_value(transcript_text, "Role") or "Unspecified Role"

        candidate_name = ""
        if resume_id:
            resume_json = _safe_read_json(d / f"resume_prep_{resume_id}.json")
            if isinstance(resume_json, dict):
                contact = resume_json.get("contact")
                if isinstance(contact, dict):
                    candidate_name = str(contact.get("name") or "")

        evaluation = _safe_read_json(d / f"interview_evaluation_{session_id}.json") or {}
        overall_score = evaluation.get("overall_score")  # typically 1-10
        recommendation = evaluation.get("recommendation")

        speech_stats = _safe_read_json(d / f"speech_stats_{session_id}.json") or {}

        rows.append(
            {
                "id": session_id,
                "candidateName": candidate_name or "Candidate",
                "role": role,
                "date": transcript_path.stat().st_mtime,  # epoch seconds
                "overallScore": overall_score,
                "recommendation": recommendation,
                "hasEvaluation": bool(evaluation),
                "hasSpeechStats": bool(speech_stats),
            }
        )

    return {"items": rows}


@app.get("/api/dashboard/interviews/{session_id}")
def get_interview(session_id: str):
    """
    Fetch a full interview bundle (transcript + evaluation + speech stats) by session_id.
    """
    d = _data_dir()
    transcript_path = d / f"interview_transcript_{session_id}.txt"
    if not transcript_path.exists():
        raise HTTPException(status_code=404, detail="Interview transcript not found.")

    transcript_text = transcript_path.read_text(encoding="utf-8", errors="replace")
    resume_id = _extract_header_value(transcript_text, "Resume ID")
    role = _extract_header_value(transcript_text, "Role") or "Unspecified Role"

    resume_json = _safe_read_json(d / f"resume_prep_{resume_id}.json") if resume_id else None
    evaluation = _safe_read_json(d / f"interview_evaluation_{session_id}.json")
    speech_stats = _safe_read_json(d / f"speech_stats_{session_id}.json")

    return {
        "id": session_id,
        "role": role,
        "resumeId": resume_id,
        "resume": resume_json,
        "transcriptText": transcript_text,
        "evaluation": evaluation,
        "speechStats": speech_stats,
        "updatedAt": transcript_path.stat().st_mtime,
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("server:app", host="0.0.0.0", port=8000, reload=True)

