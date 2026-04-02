"""
In-memory session store.

Holds per-session state: config, reference face patch, frame history.
Thread-safe for async FastAPI handlers via asyncio.Lock.
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Optional

import numpy as np

from models.schemas import (
    AlertEvent,
    FaceData,
    FrameAnalysis,
    GazeData,
    SessionConfig,
    SessionStatus,
)

logger = logging.getLogger(__name__)


class Session:
    def __init__(self, session_id: str, config: SessionConfig):
        self.session_id = session_id
        self.config = config
        self.started_at = datetime.utcnow()
        self.ended_at: Optional[datetime] = None
        self.is_active = True

        # Frame data
        self.frames: List[FrameAnalysis] = []
        self.alerts: List[AlertEvent] = []

        # Face tracking
        self.reference_patch: Optional[np.ndarray] = None
        self._lock = asyncio.Lock()

    @property
    def frame_count(self) -> int:
        return len(self.frames)

    @property
    def alert_count(self) -> int:
        return len(self.alerts)

    def to_status(self) -> SessionStatus:
        return SessionStatus(
            session_id=self.session_id,
            started_at=self.started_at,
            frame_count=self.frame_count,
            alert_count=self.alert_count,
            is_active=self.is_active,
        )

    def add_frame(self, frame: FrameAnalysis) -> None:
        self.frames.append(frame)
        for alert_text in frame.alerts:
            self.alerts.append(
                AlertEvent(
                    frame_index=frame.frame_index,
                    timestamp=frame.timestamp,
                    alert_type=_infer_alert_type(alert_text),
                    detail=alert_text,
                )
            )

    def end(self) -> None:
        self.ended_at = datetime.utcnow()
        self.is_active = False


def _infer_alert_type(text: str) -> str:
    t = text.lower()
    if "person" in t or "change" in t:
        return "person_change"
    if "multiple" in t or "face" in t:
        return "multiple_faces"
    if "looking" in t or "gaze" in t or "away" in t:
        return "gaze_away"
    if "no face" in t or "absent" in t:
        return "face_absent"
    return "general"


class SessionStore:
    """Global store for all active (and recently ended) sessions."""

    def __init__(self):
        self._sessions: Dict[str, Session] = {}
        self._lock = asyncio.Lock()

    async def create(self, session_id: str, config: SessionConfig) -> Session:
        async with self._lock:
            if session_id in self._sessions:
                raise ValueError(f"Session '{session_id}' already exists")
            session = Session(session_id, config)
            self._sessions[session_id] = session
            logger.info("Session created: %s", session_id)
            return session

    async def get(self, session_id: str) -> Optional[Session]:
        return self._sessions.get(session_id)

    async def get_or_raise(self, session_id: str) -> Session:
        session = self._sessions.get(session_id)
        if session is None:
            raise KeyError(f"Session '{session_id}' not found")
        return session

    async def end(self, session_id: str) -> Session:
        session = await self.get_or_raise(session_id)
        session.end()
        logger.info("Session ended: %s (frames=%d)", session_id, session.frame_count)
        return session

    async def list_active(self) -> List[SessionStatus]:
        return [s.to_status() for s in self._sessions.values() if s.is_active]

    async def delete(self, session_id: str) -> None:
        async with self._lock:
            self._sessions.pop(session_id, None)


# Module-level singleton – imported by routers and the video monitor
store = SessionStore()
