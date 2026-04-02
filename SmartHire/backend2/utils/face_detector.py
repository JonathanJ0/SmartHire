"""
Face detector – uses MediaPipe Face Detection for fast, reliable results.
Also tracks a reference face embedding (from the first frame) to detect
mid-interview person changes using cosine distance on simple face-crop features.
"""
from __future__ import annotations

import logging
from typing import Optional, Tuple

import cv2
import mediapipe as mp
import numpy as np

from models.schemas import FaceData

logger = logging.getLogger(__name__)

_COSINE_CHANGE_THRESHOLD = 0.55  # configurable at session level


def _crop_face(image: np.ndarray, bbox: list[int], margin: float = 0.2) -> np.ndarray:
    """Return a cropped + resized face patch (64×64 gray) for lightweight comparison."""
    h, w = image.shape[:2]
    x, y, fw, fh = bbox
    mx = int(fw * margin)
    my = int(fh * margin)
    x1 = max(0, x - mx)
    y1 = max(0, y - my)
    x2 = min(w, x + fw + mx)
    y2 = min(h, y + fh + my)
    patch = image[y1:y2, x1:x2]
    if patch.size == 0:
        return np.zeros((64, 64), dtype=np.float32)
    gray = cv2.cvtColor(patch, cv2.COLOR_RGB2GRAY) if len(patch.shape) == 3 else patch
    return cv2.resize(gray, (64, 64)).astype(np.float32)


def _flat_norm(patch: np.ndarray) -> np.ndarray:
    flat = patch.flatten()
    norm = np.linalg.norm(flat)
    return flat / (norm + 1e-8)


def _cosine_distance(a: np.ndarray, b: np.ndarray) -> float:
    return float(1.0 - np.dot(_flat_norm(a), _flat_norm(b)))


class FaceDetector:
    """
    Stateless per-call face detection with optional reference embedding tracking.

    Usage
    -----
    detector = FaceDetector()
    face_data = detector.analyze(frame_rgb, reference_patch=session.ref_patch,
                                  threshold=0.55)
    # On first frame, call detector.extract_reference_patch(frame_rgb, bbox)
    # and store in the session.
    """

    def __init__(self, min_detection_confidence: float = 0.6):
        self._mp_face = mp.solutions.face_detection
        self._detector = self._mp_face.FaceDetection(
            model_selection=1,
            min_detection_confidence=min_detection_confidence,
        )
        logger.info("FaceDetector initialised (MediaPipe)")

    def analyze(
        self,
        frame_rgb: np.ndarray,
        reference_patch: Optional[np.ndarray] = None,
        threshold: float = _COSINE_CHANGE_THRESHOLD,
    ) -> Tuple[FaceData, Optional[np.ndarray]]:
        """
        Parameters
        ----------
        frame_rgb       : RGB numpy array
        reference_patch : 64×64 float32 patch from the first accepted frame
        threshold       : cosine distance above which a person-change is flagged

        Returns
        -------
        (FaceData, new_reference_patch)
        new_reference_patch is non-None only when reference_patch is None
        (i.e. first frame) – callers should store it in the session.
        """
        h, w = frame_rgb.shape[:2]
        results = self._detector.process(frame_rgb)

        face_data = FaceData()
        new_ref: Optional[np.ndarray] = None

        if not results.detections:
            return face_data, new_ref

        detections = results.detections
        face_data.face_count = len(detections)
        face_data.faces_detected = True
        face_data.multiple_faces = len(detections) > 1

        # Primary face = highest confidence detection
        primary = max(detections, key=lambda d: d.score[0])
        bbox_rel = primary.location_data.relative_bounding_box
        x = int(bbox_rel.xmin * w)
        y = int(bbox_rel.ymin * h)
        fw = int(bbox_rel.width * w)
        fh = int(bbox_rel.height * h)
        face_data.bbox = [x, y, fw, fh]

        # Person-change detection
        current_patch = _crop_face(frame_rgb, face_data.bbox)
        if reference_patch is None:
            # First frame – establish baseline
            new_ref = current_patch
            face_data.person_changed = False
            face_data.face_embedding_distance = 0.0
        else:
            dist = _cosine_distance(reference_patch, current_patch)
            face_data.face_embedding_distance = round(dist, 4)
            face_data.person_changed = dist > threshold

        return face_data, new_ref

    def close(self):
        self._detector.close()
