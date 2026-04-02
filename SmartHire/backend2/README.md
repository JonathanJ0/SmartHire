# Interview Video Monitor — FastAPI Module

Real-time video monitoring for interview evaluation platforms.  
Detects faces, gaze direction, mid-interview person changes, and emotion-based confidence scores.

---

## Features

| Capability | Detail |
|---|---|
| **Face Detection** | MediaPipe — count, bounding box, presence |
| **Person-Change Detection** | Cosine distance on face-crop embeddings vs. first-frame reference |
| **Gaze / Head-Pose** | solvePnP via MediaPipe FaceMesh → yaw / pitch / roll + attention zone |
| **Emotion Recognition** | DeepFace (7 classes) — happy, neutral, surprise, sad, fear, angry, disgust |
| **Confidence Score** | Weighted emotion formula + gaze on-screen ratio → 0–1 |
| **Integrity Score** | Penalises person changes, face absences, multiple faces |
| **Report** | JSON + self-contained HTML with Chart.js trend graph |

---

## Project Structure

```
interview_monitor/
├── main.py                        # FastAPI app entry point
├── video_monitor.py               # Orchestrator (VideoMonitor singleton)
├── requirements.txt
│
├── models/
│   └── schemas.py                 # All Pydantic models
│
├── utils/
│   ├── face_detector.py           # MediaPipe face detection + person-change
│   ├── gaze_detector.py           # MediaPipe FaceMesh → head pose
│   ├── emotion_analyzer.py        # DeepFace emotion + confidence score
│   ├── session_store.py           # Async in-memory session store
│   └── report_generator.py        # Aggregates frames → InterviewReport
│
├── routers/
│   ├── sessions.py                # /sessions/* endpoints
│   ├── monitor.py                 # /monitor/analyze-frame
│   └── reports.py                 # /reports/* endpoints (JSON + HTML)
│
└── client/
    └── interview_monitor_client.js  # Frontend JS helper
```

---

## Installation

```bash
cd interview_monitor
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

> **Note**: `mediapipe` requires Python 3.8–3.11. `deepface` will download model
> weights (~100 MB) on first use.

---

## Running the Server

```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

Interactive API docs: http://localhost:8000/docs

---

## API Reference

### Sessions

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/sessions/start` | Create session |
| `POST` | `/sessions/{id}/end` | End session |
| `GET`  | `/sessions/{id}/status` | Live status |
| `GET`  | `/sessions/` | List active sessions |
| `DELETE` | `/sessions/{id}` | Delete session |

**Start session body:**
```json
{
  "session_id": "uuid-here",
  "config": {
    "candidate_name": "Jane Doe",
    "job_role": "Senior Engineer",
    "gaze_threshold_degrees": 25.0,
    "person_change_distance_threshold": 0.6,
    "emotion_analysis_every_n_frames": 3
  }
}
```

---

### Frame Analysis

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/monitor/analyze-frame` | Submit a frame |

**Request body:**
```json
{
  "session_id": "uuid-here",
  "frame_index": 42,
  "timestamp": 12.5,
  "image_b64": "<base64-encoded JPEG or PNG>"
}
```

**Response (`FrameAnalysis`):**
```json
{
  "session_id": "uuid-here",
  "frame_index": 42,
  "timestamp": 12.5,
  "face": {
    "face_count": 1,
    "faces_detected": true,
    "multiple_faces": false,
    "person_changed": false,
    "face_embedding_distance": 0.12,
    "bbox": [120, 80, 200, 220]
  },
  "gaze": {
    "yaw": -8.3,
    "pitch": 4.1,
    "roll": 1.2,
    "attention_zone": "on_screen",
    "is_looking_at_screen": true
  },
  "emotion": {
    "angry": 0.02,
    "disgust": 0.01,
    "fear": 0.08,
    "happy": 0.35,
    "sad": 0.04,
    "surprise": 0.12,
    "neutral": 0.38
  },
  "confidence_score": 0.713,
  "alerts": []
}
```

---

### Reports

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/reports/{id}` | Full JSON report |
| `GET` | `/reports/{id}/html` | Self-contained HTML report |

The HTML report can be embedded in an `<iframe>` or opened as a new tab directly from your interviewer interface.

---

## Frontend Integration

```javascript
import { InterviewMonitorClient, createOverlayRenderer } from './client/interview_monitor_client.js';

const client = new InterviewMonitorClient({ baseUrl: 'http://localhost:8000' });

// 1. Start session
await client.startSession({
  session_id: crypto.randomUUID(),
  config: { candidate_name: 'Jane Doe', job_role: 'Engineer' }
});

// 2. Stream from webcam <video> element
const overlayCanvas = document.getElementById('overlay');
const updateOverlay = createOverlayRenderer(overlayCanvas);

client.startStreaming(document.getElementById('webcam'), {
  fps: 5,
  onFrame: (analysis) => {
    updateOverlay(analysis);          // draw bbox + confidence badge
    updateDashboard(analysis);        // your own UI update
  },
  onAlert: (msg) => showToast(msg),
});

// 3. End interview and get report
const report = await client.endSessionAndGetReport();
console.log('Verdict:', report.verdict);
console.log('Confidence:', report.overall_confidence_score);

// Open HTML report in a new tab
window.open(client.getReportHtmlUrl(), '_blank');
```

---

## Confidence Score Formula

```
positive = happy×0.40 + neutral×0.35 + surprise×0.10
negative = angry×0.50 + fear×0.40 + sad×0.30 + disgust×0.20

raw_emotion_confidence = 0.5 + positive − (negative × 0.6)   # clamped [0,1]

overall_confidence = emotion_confidence×0.70 + pct_on_screen×0.30
```

---

## Integrity Score

Starts at **1.0**, penalties applied:

| Event | Penalty |
|---|---|
| Each person-change event | −0.15 (max −0.50) |
| Face absence ratio | up to −0.30 |
| Multiple-face ratio | up to −0.20 |

---

## Tuning Parameters

| Config key | Default | Effect |
|---|---|---|
| `gaze_threshold_degrees` | `25.0` | Wider = more lenient on head movement |
| `person_change_distance_threshold` | `0.6` | Higher = harder to trigger person-change |
| `emotion_analysis_every_n_frames` | `3` | Higher = faster, less frequent emotion updates |

---

## Performance Notes

- **Face detection + gaze**: ~15–25 ms/frame on CPU
- **Emotion (DeepFace)**: ~80–200 ms/frame on CPU — throttled by `emotion_analysis_every_n_frames`
- Recommended capture rate: **3–5 fps** for a good balance of responsiveness and CPU load
- For GPU acceleration, install `tensorflow-gpu` and the appropriate CUDA drivers

---

## Extending

The architecture is modular — you can add new detectors by:

1. Creating a new utility class in `utils/`
2. Adding its output fields to `FrameAnalysis` in `models/schemas.py`
3. Calling it in `VideoMonitor.process_frame()` in `video_monitor.py`
4. Including its aggregated stats in `report_generator.py`

Planned modules: audio tone analysis, speech rate, background change detection.
