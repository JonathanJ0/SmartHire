"""
VideoMonitor – main orchestrator.

Receives decoded frames, runs all detectors in sequence, builds alerts,
stores results in the session, and returns a FrameAnalysis.
"""
from __future__ import annotations

import base64
import io
import logging
import time
from typing import Optional

import numpy as np
from PIL import Image

from models.schemas import FrameAnalysis, FrameRequest
from utils.emotion_analyzer import EmotionAnalyzer
from utils.face_detector import FaceDetector
from utils.gaze_detector import GazeDetector
from utils.session_store import Session, store

logger = logging.getLogger(__name__)


def _decode_b64_frame(b64: str) -> np.ndarray:
    """Decode a base64-encoded JPEG/PNG into an RGB numpy array."""
    data = base64.b64decode(b64)
    img = Image.open(io.BytesIO(data)).convert("RGB")
    return np.array(img)


class VideoMonitor:
    """
    Singleton orchestrator – one instance per FastAPI app lifetime.

    Detectors are reused across all sessions to avoid repeated model loading.
    """

    def __init__(self):
        logger.info("Initialising VideoMonitor detectors...")
        self.face_detector = FaceDetector(min_detection_confidence=0.6)
        self.gaze_detector = GazeDetector(refine_landmarks=True)
        self.emotion_analyzer = EmotionAnalyzer()
        logger.info("VideoMonitor ready")

    async def process_frame(self, req: FrameRequest) -> FrameAnalysis:
        """
        Full pipeline for a single frame:
          1. Decode image
          2. Face detection + person-change check
          3. Gaze estimation
          4. Emotion analysis (every N frames, configurable)
          5. Build alerts
          6. Persist in session
          7. Return FrameAnalysis
        """
        session: Session = await store.get_or_raise(req.session_id)
        config = session.config

        t_start = time.perf_counter()
        frame_rgb = _decode_b64_frame(req.image_b64)

        # ── 1. Face detection ─────────────────────────────────────────────────
        face_data, new_ref = self.face_detector.analyze(
            frame_rgb,
            reference_patch=session.reference_patch,
            threshold=config.person_change_distance_threshold,
        )
        if new_ref is not None:
            session.reference_patch = new_ref

        # ── 2. Gaze estimation ────────────────────────────────────────────────
        gaze_data = self.gaze_detector.analyze(
            frame_rgb,
            gaze_threshold_degrees=config.gaze_threshold_degrees,
        )

        # ── 3. Emotion analysis (throttled) ───────────────────────────────────
        emotion_scores = None
        confidence_score = None
        run_emotion = (
            req.frame_index % config.emotion_analysis_every_n_frames == 0
            and face_data.faces_detected
        )
        if run_emotion:
            emotion_scores = self.emotion_analyzer.analyze(frame_rgb, bbox=face_data.bbox)
            if emotion_scores is not None:
                confidence_score = emotion_scores.confidence_score

        # ── 4. Build alerts ───────────────────────────────────────────────────
        alerts: list[str] = []

        if not face_data.faces_detected:
            alerts.append("No face detected in frame")
        elif face_data.multiple_faces:
            alerts.append(f"Multiple faces detected ({face_data.face_count})")
        elif face_data.person_changed:
            dist = face_data.face_embedding_distance or 0.0
            alerts.append(
                f"Person change detected (face similarity distance={dist:.3f})"
            )

        if face_data.faces_detected and not gaze_data.is_looking_at_screen:
            zone = gaze_data.attention_zone.value.replace("_", " ")
            alerts.append(
                f"Candidate is {zone} "
                f"(yaw={gaze_data.yaw:.1f}°, pitch={gaze_data.pitch:.1f}°)"
            )

        # ── 5. Assemble analysis ──────────────────────────────────────────────
        analysis = FrameAnalysis(
            session_id=req.session_id,
            frame_index=req.frame_index,
            timestamp=req.timestamp,
            face=face_data,
            gaze=gaze_data,
            emotion=emotion_scores,
            confidence_score=confidence_score,
            alerts=alerts,
        )

        # ── 6. Persist ────────────────────────────────────────────────────────
        async with session._lock:
            session.add_frame(analysis)

        elapsed_ms = (time.perf_counter() - t_start) * 1000
        logger.debug(
            "Frame %d processed in %.1f ms | faces=%d | zone=%s | alerts=%d",
            req.frame_index,
            elapsed_ms,
            face_data.face_count,
            gaze_data.attention_zone.value,
            len(alerts),
        )

        return analysis

    def shutdown(self):
        self.face_detector.close()
        self.gaze_detector.close()


# Module-level singleton – imported by routers
monitor = VideoMonitor()
