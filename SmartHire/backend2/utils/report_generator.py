"""
Report generator.

Aggregates per-frame data stored in a Session into a structured
InterviewReport that the interviewer UI can display.
"""
from __future__ import annotations

import logging
from collections import Counter
from datetime import datetime, timezone
from typing import Any, Dict, List

import numpy as np

from models.schemas import (
    AttentionZone,
    EmotionScores,
    EmotionSummary,
    FaceSummary,
    GazeSummary,
    InterviewReport,
)
from utils.session_store import Session

logger = logging.getLogger(__name__)


def generate_report(session: Session) -> InterviewReport:
    frames = session.frames
    config = session.config

    ended_at = session.ended_at or datetime.utcnow()
    duration = (ended_at - session.started_at).total_seconds()
    total = len(frames)

    if total == 0:
        report = InterviewReport.empty()
        report.session_id = session.session_id
        report.candidate_name = config.candidate_name
        report.job_role = config.job_role
        report.started_at = session.started_at
        report.ended_at = ended_at
        return report

    # ── Face summary ──────────────────────────────────────────────────────────
    frames_with_face = sum(1 for f in frames if f.face.faces_detected)
    frames_multi = sum(1 for f in frames if f.face.multiple_faces)
    person_changes = sum(1 for f in frames if f.face.person_changed)

    face_summary = FaceSummary(
        total_frames=total,
        frames_with_face=frames_with_face,
        frames_multiple_faces=frames_multi,
        face_presence_pct=round(frames_with_face / total * 100, 1),
        person_change_events=person_changes,
    )

    # ── Gaze summary ──────────────────────────────────────────────────────────
    zone_counter: Counter = Counter()
    yaws, pitches = [], []
    for f in frames:
        zone_counter[f.gaze.attention_zone] += 1
        yaws.append(f.gaze.yaw)
        pitches.append(f.gaze.pitch)

    def pct(zone) -> float:
        return round(zone_counter.get(zone, 0) / total * 100, 1)

    gaze_summary = GazeSummary(
        pct_on_screen=pct(AttentionZone.ON_SCREEN),
        pct_looking_away=pct(AttentionZone.LOOKING_AWAY),
        pct_looking_down=pct(AttentionZone.LOOKING_DOWN),
        pct_looking_up=pct(AttentionZone.LOOKING_UP),
        avg_yaw=round(float(np.mean(yaws)) if yaws else 0.0, 2),
        avg_pitch=round(float(np.mean(pitches)) if pitches else 0.0, 2),
    )

    # ── Emotion summary ───────────────────────────────────────────────────────
    emotion_frames = [f for f in frames if f.emotion is not None]
    confidence_values = [f.confidence_score for f in frames if f.confidence_score is not None]

    if emotion_frames:
        avg_e = EmotionScores(
            angry=round(float(np.mean([e.emotion.angry for e in emotion_frames])), 4),
            disgust=round(float(np.mean([e.emotion.disgust for e in emotion_frames])), 4),
            fear=round(float(np.mean([e.emotion.fear for e in emotion_frames])), 4),
            happy=round(float(np.mean([e.emotion.happy for e in emotion_frames])), 4),
            sad=round(float(np.mean([e.emotion.sad for e in emotion_frames])), 4),
            surprise=round(float(np.mean([e.emotion.surprise for e in emotion_frames])), 4),
            neutral=round(float(np.mean([e.emotion.neutral for e in emotion_frames])), 4),
        )
        avg_confidence = round(float(np.mean(confidence_values)), 3) if confidence_values else 0.0

        # Confidence trend: sample every ~5% of frames (max 40 points)
        step = max(1, total // 40)
        trend = [
            round(frames[i].confidence_score or 0.0, 3)
            for i in range(0, total, step)
            if frames[i].confidence_score is not None
        ]

        emotion_summary = EmotionSummary(
            avg_scores=avg_e,
            avg_confidence_score=avg_confidence,
            dominant_emotion=avg_e.dominant,
            confidence_trend=trend,
        )
    else:
        emotion_summary = EmotionSummary(
            avg_scores=EmotionScores(),
            avg_confidence_score=0.0,
            dominant_emotion="neutral",
            confidence_trend=[],
        )

    # ── Integrity score ───────────────────────────────────────────────────────
    # Penalise: person changes (heavy), face absences, multiple faces
    person_change_penalty = min(0.5, person_changes * 0.15)
    face_absence_penalty = max(0.0, (1 - face_summary.face_presence_pct / 100) * 0.3)
    multi_face_penalty = min(0.2, frames_multi / total * 0.4)

    integrity_score = round(
        max(0.0, 1.0 - person_change_penalty - face_absence_penalty - multi_face_penalty),
        3,
    )

    # ── Overall confidence ────────────────────────────────────────────────────
    overall_confidence = round(
        emotion_summary.avg_confidence_score * 0.7 + gaze_summary.pct_on_screen / 100 * 0.3,
        3,
    )

    # ── Lightweight frame timeline ────────────────────────────────────────────
    step = max(1, total // 200)  # max 200 points in timeline
    timeline: List[Dict[str, Any]] = [
        {
            "t": frames[i].timestamp,
            "fi": frames[i].frame_index,
            "fc": frames[i].face.face_count,
            "gz": frames[i].gaze.attention_zone.value,
            "cs": frames[i].confidence_score,
            "alerts": len(frames[i].alerts),
        }
        for i in range(0, total, step)
    ]

    # ── Verdict ───────────────────────────────────────────────────────────────
    verdict = _make_verdict(
        overall_confidence, integrity_score, gaze_summary.pct_on_screen
    )

    return InterviewReport(
        session_id=session.session_id,
        candidate_name=config.candidate_name,
        job_role=config.job_role,
        started_at=session.started_at,
        ended_at=ended_at,
        duration_seconds=round(duration, 1),
        total_frames=total,
        face_summary=face_summary,
        gaze_summary=gaze_summary,
        emotion_summary=emotion_summary,
        alerts=session.alerts,
        overall_confidence_score=overall_confidence,
        integrity_score=integrity_score,
        frame_timeline=timeline,
        verdict=verdict,
    )


def _make_verdict(confidence: float, integrity: float, pct_on_screen: float) -> str:
    if integrity < 0.5:
        return "Integrity concerns detected – manual review required"
    if confidence >= 0.72 and pct_on_screen >= 75:
        return "Strong candidate – confident and engaged throughout"
    if confidence >= 0.55 and pct_on_screen >= 60:
        return "Good candidate – generally composed with minor distractions"
    if confidence >= 0.40:
        return "Average candidate – some signs of nervousness or distraction"
    return "Candidate appeared nervous or disengaged – further evaluation recommended"
