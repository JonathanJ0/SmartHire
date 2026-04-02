from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


class AttentionZone(str, Enum):
    ON_SCREEN = "on_screen"
    LOOKING_AWAY = "looking_away"
    LOOKING_DOWN = "looking_down"
    LOOKING_UP = "looking_up"


class EmotionScores(BaseModel):
    angry: float = 0.0
    disgust: float = 0.0
    fear: float = 0.0
    happy: float = 0.0
    sad: float = 0.0
    surprise: float = 0.0
    neutral: float = 0.0

    @property
    def dominant(self) -> str:
        scores = self.model_dump()
        return max(scores, key=scores.get)

    @property
    def confidence_score(self) -> float:
        """
        Confidence score based on positive/calm emotions.
        Happy + Neutral weighted heavily, Fear + Angry reduce score.
        Returns 0.0–1.0
        """
        positive = self.happy * 0.4 + self.neutral * 0.35 + self.surprise * 0.1
        negative = self.angry * 0.5 + self.fear * 0.4 + self.sad * 0.3 + self.disgust * 0.2
        raw = positive - (negative * 0.6)
        return round(max(0.0, min(1.0, 0.5 + raw)), 3)


class GazeData(BaseModel):
    yaw: float = Field(0.0, description="Horizontal head rotation (degrees)")
    pitch: float = Field(0.0, description="Vertical head rotation (degrees)")
    roll: float = Field(0.0, description="Tilt rotation (degrees)")
    attention_zone: AttentionZone = AttentionZone.ON_SCREEN
    is_looking_at_screen: bool = True


class FaceData(BaseModel):
    face_count: int = 0
    faces_detected: bool = False
    multiple_faces: bool = False
    person_changed: bool = False
    face_embedding_distance: Optional[float] = None
    bbox: Optional[List[int]] = None  # [x, y, w, h] of primary face


class FrameAnalysis(BaseModel):
    session_id: str
    frame_index: int
    timestamp: float
    face: FaceData
    gaze: GazeData
    emotion: Optional[EmotionScores] = None
    confidence_score: Optional[float] = None
    alerts: List[str] = []


class FrameRequest(BaseModel):
    session_id: str
    frame_index: int
    timestamp: float
    image_b64: str  # base64-encoded JPEG/PNG


# ── Session ──────────────────────────────────────────────────────────────────

class SessionConfig(BaseModel):
    candidate_name: str = "Unknown Candidate"
    job_role: str = ""
    gaze_threshold_degrees: float = 25.0
    person_change_distance_threshold: float = 0.6
    emotion_analysis_every_n_frames: int = 3


class StartSessionRequest(BaseModel):
    session_id: str
    config: SessionConfig = SessionConfig()


class SessionStatus(BaseModel):
    session_id: str
    started_at: datetime
    frame_count: int
    alert_count: int
    is_active: bool


# ── Report ────────────────────────────────────────────────────────────────────

class AlertEvent(BaseModel):
    frame_index: int
    timestamp: float
    alert_type: str
    detail: str


class GazeSummary(BaseModel):
    pct_on_screen: float
    pct_looking_away: float
    pct_looking_down: float
    pct_looking_up: float
    avg_yaw: float
    avg_pitch: float


class EmotionSummary(BaseModel):
    avg_scores: EmotionScores
    avg_confidence_score: float
    dominant_emotion: str
    confidence_trend: List[float]  # per-frame sampled confidence values


class FaceSummary(BaseModel):
    total_frames: int
    frames_with_face: int
    frames_multiple_faces: int
    face_presence_pct: float
    person_change_events: int


class InterviewReport(BaseModel):
    session_id: str
    candidate_name: str
    job_role: str
    started_at: datetime
    ended_at: datetime
    duration_seconds: float
    total_frames: int

    face_summary: FaceSummary
    gaze_summary: GazeSummary
    emotion_summary: EmotionSummary

    alerts: List[AlertEvent]
    overall_confidence_score: float
    integrity_score: float  # 0–1, penalised for person changes / face absence

    frame_timeline: List[Dict[str, Any]]  # lightweight per-frame data for chart
    verdict: str  # human-readable short verdict

    @classmethod
    def empty(cls) -> "InterviewReport":
        now = datetime.utcnow()
        return cls(
            session_id="",
            candidate_name="",
            job_role="",
            started_at=now,
            ended_at=now,
            duration_seconds=0,
            total_frames=0,
            face_summary=FaceSummary(
                total_frames=0,
                frames_with_face=0,
                frames_multiple_faces=0,
                face_presence_pct=0,
                person_change_events=0,
            ),
            gaze_summary=GazeSummary(
                pct_on_screen=0,
                pct_looking_away=0,
                pct_looking_down=0,
                pct_looking_up=0,
                avg_yaw=0,
                avg_pitch=0,
            ),
            emotion_summary=EmotionSummary(
                avg_scores=EmotionScores(),
                avg_confidence_score=0,
                dominant_emotion="neutral",
                confidence_trend=[],
            ),
            alerts=[],
            overall_confidence_score=0,
            integrity_score=1.0,
            frame_timeline=[],
            verdict="Insufficient data",
        )
