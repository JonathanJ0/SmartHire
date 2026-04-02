"""
Emotion analyzer using DeepFace.

Returns 7-class emotion scores and a derived confidence score that
estimates how composed / confident the interviewee appears.

The confidence score formula weights:
  +  happy    (0.40) – smiling, engaged
  +  neutral  (0.35) – calm, controlled
  +  surprise (0.10) – mild positivity allowed
  −  angry    (0.50) – strong negative
  −  fear     (0.40) – nervous / anxious
  −  sad      (0.30) – low energy
  −  disgust  (0.20)

Result is clamped to [0, 1], centred at 0.5.
"""
from __future__ import annotations

import logging
from typing import Optional

import numpy as np

from models.schemas import EmotionScores

logger = logging.getLogger(__name__)

# Lazy-load DeepFace so the rest of the app starts quickly
_deepface = None


def _get_deepface():
    global _deepface
    if _deepface is None:
        from deepface import DeepFace
        _deepface = DeepFace
        logger.info("DeepFace loaded")
    return _deepface


class EmotionAnalyzer:
    """
    Stateless emotion analyzer.

    analyze() accepts an RGB numpy array and an optional bounding-box
    so DeepFace can focus on the primary face rather than the whole frame.

    Usage
    -----
    analyzer = EmotionAnalyzer()
    scores = analyzer.analyze(frame_rgb, bbox=[x, y, w, h])
    print(scores.confidence_score)  # 0.0 – 1.0
    """

    def __init__(self):
        # Trigger import at init time so the first frame isn't slow
        try:
            _get_deepface()
        except Exception as e:
            logger.warning("DeepFace pre-load failed (will retry at first call): %s", e)

    def analyze(
        self,
        frame_rgb: np.ndarray,
        bbox: Optional[list[int]] = None,
    ) -> Optional[EmotionScores]:
        """
        Parameters
        ----------
        frame_rgb : RGB numpy array (H×W×3)
        bbox      : [x, y, w, h] of the primary face (optional).
                    If given, crops the face region before analysis.

        Returns
        -------
        EmotionScores or None if analysis fails.
        """
        try:
            DeepFace = _get_deepface()
            import cv2

            img = frame_rgb
            if bbox:
                x, y, w, h = bbox
                margin = 20
                H, W = img.shape[:2]
                x1 = max(0, x - margin)
                y1 = max(0, y - margin)
                x2 = min(W, x + w + margin)
                y2 = min(H, y + h + margin)
                img = img[y1:y2, x1:x2]

            if img.size == 0:
                return None

            # DeepFace expects BGR
            img_bgr = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)

            result = DeepFace.analyze(
                img_bgr,
                actions=["emotion"],
                enforce_detection=False,
                silent=True,
            )

            # result may be a list (multiple faces detected)
            if isinstance(result, list):
                result = result[0]

            raw: dict = result.get("emotion", {})

            # Normalise to sum = 1
            total = sum(raw.values()) or 1.0
            norm = {k: v / total for k, v in raw.items()}

            scores = EmotionScores(
                angry=round(norm.get("angry", 0.0), 4),
                disgust=round(norm.get("disgust", 0.0), 4),
                fear=round(norm.get("fear", 0.0), 4),
                happy=round(norm.get("happy", 0.0), 4),
                sad=round(norm.get("sad", 0.0), 4),
                surprise=round(norm.get("surprise", 0.0), 4),
                neutral=round(norm.get("neutral", 0.0), 4),
            )
            return scores

        except Exception as e:
            logger.debug("Emotion analysis failed for frame: %s", e)
            return None
