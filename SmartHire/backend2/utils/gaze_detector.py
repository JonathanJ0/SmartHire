"""
Gaze / head-pose estimator using MediaPipe Face Mesh.

Computes yaw, pitch, roll via solvePnP with canonical facial landmarks,
then classifies attention into four zones.
"""
from __future__ import annotations

import logging
import math
from typing import Optional

import cv2
import mediapipe as mp
import numpy as np

from models.schemas import AttentionZone, GazeData

logger = logging.getLogger(__name__)

# Canonical 3-D facial model points (nose tip, chin, corners of eyes/mouth)
_MODEL_POINTS_3D = np.array([
    [0.0,   0.0,   0.0],    # Nose tip           #1
    [0.0,  -63.6, -12.5],   # Chin               #152
    [-43.3,  32.7, -26.0],  # Left eye corner    #263
    [43.3,  32.7, -26.0],   # Right eye corner   #33
    [-28.9, -28.9, -24.1],  # Left mouth corner  #287
    [28.9,  -28.9, -24.1],  # Right mouth corner #57
], dtype=np.float64)

# Corresponding MediaPipe landmark indices
_LANDMARK_INDICES = [1, 152, 263, 33, 287, 57]


def _rotation_matrix_to_euler(mat: np.ndarray) -> tuple[float, float, float]:
    """Convert 3×3 rotation matrix → (yaw, pitch, roll) in degrees."""
    sy = math.sqrt(mat[0, 0] ** 2 + mat[1, 0] ** 2)
    singular = sy < 1e-6
    if not singular:
        roll = math.atan2(mat[2, 1], mat[2, 2])
        pitch = math.atan2(-mat[2, 0], sy)
        yaw = math.atan2(mat[1, 0], mat[0, 0])
    else:
        roll = math.atan2(-mat[1, 2], mat[1, 1])
        pitch = math.atan2(-mat[2, 0], sy)
        yaw = 0.0
    return (
        math.degrees(yaw),
        math.degrees(pitch),
        math.degrees(roll),
    )


def _classify_zone(yaw: float, pitch: float, threshold: float) -> AttentionZone:
    if abs(yaw) <= threshold and abs(pitch) <= threshold:
        return AttentionZone.ON_SCREEN
    if abs(yaw) > threshold:
        return AttentionZone.LOOKING_AWAY
    if pitch > threshold:
        return AttentionZone.LOOKING_UP
    return AttentionZone.LOOKING_DOWN


class GazeDetector:
    """
    Per-frame gaze / head-pose estimation.

    Usage
    -----
    detector = GazeDetector()
    gaze_data = detector.analyze(frame_rgb, gaze_threshold_degrees=25.0)
    """

    def __init__(self, refine_landmarks: bool = True):
        self._mp_mesh = mp.solutions.face_mesh
        self._mesh = self._mp_mesh.FaceMesh(
            static_image_mode=False,
            max_num_faces=1,
            refine_landmarks=refine_landmarks,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5,
        )
        logger.info("GazeDetector initialised (MediaPipe FaceMesh)")

    def analyze(
        self,
        frame_rgb: np.ndarray,
        gaze_threshold_degrees: float = 25.0,
    ) -> GazeData:
        h, w = frame_rgb.shape[:2]
        results = self._mesh.process(frame_rgb)

        gaze = GazeData()
        if not results.multi_face_landmarks:
            return gaze

        landmarks = results.multi_face_landmarks[0].landmark

        # Extract 2-D image points for selected landmarks
        image_points = np.array(
            [[landmarks[i].x * w, landmarks[i].y * h] for i in _LANDMARK_INDICES],
            dtype=np.float64,
        )

        # Camera matrix (approximation)
        focal_length = w
        center = (w / 2, h / 2)
        cam_matrix = np.array(
            [[focal_length, 0, center[0]],
             [0, focal_length, center[1]],
             [0, 0, 1]],
            dtype=np.float64,
        )
        dist_coeffs = np.zeros((4, 1), dtype=np.float64)

        success, rotation_vec, _ = cv2.solvePnP(
            _MODEL_POINTS_3D,
            image_points,
            cam_matrix,
            dist_coeffs,
            flags=cv2.SOLVEPNP_ITERATIVE,
        )
        if not success:
            return gaze

        rot_mat, _ = cv2.Rodrigues(rotation_vec)
        yaw, pitch, roll = _rotation_matrix_to_euler(rot_mat)

        gaze.yaw = round(yaw, 2)
        gaze.pitch = round(pitch, 2)
        gaze.roll = round(roll, 2)
        gaze.attention_zone = _classify_zone(yaw, pitch, gaze_threshold_degrees)
        gaze.is_looking_at_screen = gaze.attention_zone == AttentionZone.ON_SCREEN

        return gaze

    def close(self):
        self._mesh.close()
