"""
Interview Monitoring System — MediaPipe edition
================================================
Replaces:
  - cv2 Haar cascade face detector  →  mediapipe FaceDetection
  - dlib / Haar eye tracker         →  mediapipe FaceMesh iris landmarks
"""

import cv2
import numpy as np
import time
import json
from datetime import datetime
from dataclasses import dataclass, field, asdict
from typing import Optional
import os

import mediapipe as mp
from mediapipe.tasks import python as mp_python
from mediapipe.tasks.python import vision as mp_vision
from mediapipe.tasks.python.components.containers import landmark as mp_landmark


# ─────────────────────────────────────────────
# Data Structures  (unchanged)
# ─────────────────────────────────────────────

@dataclass
class GazeDirection:
    horizontal: str = "center"   # left | center | right
    vertical:   str = "center"   # up   | center | down

@dataclass
class AlertEvent:
    timestamp:  str
    event_type: str
    details:    str

@dataclass
class SessionReport:
    session_id:       str
    start_time:       str
    end_time:         str
    duration_seconds: float
    total_frames:     int
    alerts: list      = field(default_factory=list)
    stats:  dict      = field(default_factory=dict)


# ─────────────────────────────────────────────
# Iris / Gaze Tracker  — MediaPipe FaceMesh
# ─────────────────────────────────────────────

# MediaPipe FaceMesh iris landmark indices
# Left iris  (from subject's POV): 468 469 470 471 472
# Right iris (from subject's POV): 473 474 475 476 477
_LEFT_IRIS  = [468, 469, 470, 471, 472]
_RIGHT_IRIS = [473, 474, 475, 476, 477]

# Left eye contour landmarks (used to define the eye bounding box)
_LEFT_EYE_CONTOUR  = [33, 7, 163, 144, 145, 153, 154, 155,
                       133, 173, 157, 158, 159, 160, 161, 246]
_RIGHT_EYE_CONTOUR = [362, 382, 381, 380, 374, 373, 390, 249,
                       263, 466, 388, 387, 386, 385, 384, 398]
_MODEL_PATH = "face_landmarker.task"

class IrisTracker:
    H_RATIO_LEFT  = 0.40
    H_RATIO_RIGHT = 0.60
    V_RATIO_TOP   = 0.40
    V_RATIO_BOT   = 0.60

    def __init__(self):
        if not os.path.exists(_MODEL_PATH):
            self._download_model()

        base_options = mp_python.BaseOptions(model_asset_path=_MODEL_PATH)
        options = mp_vision.FaceLandmarkerOptions(
            base_options=base_options,
            output_face_blendshapes=False,
            output_facial_transformation_matrixes=False,
            num_faces=4,                 # detect up to 4 faces (catches intruders)
            min_face_detection_confidence=0.5,
            min_face_presence_confidence=0.5,
            min_tracking_confidence=0.5,
        )
        self._landmarker = mp_vision.FaceLandmarker.create_from_options(options)
        print("[IrisTracker] Using MediaPipe FaceLandmarker (Tasks API).")

    @staticmethod
    def _download_model():
        import urllib.request
        url = (
            "https://storage.googleapis.com/mediapipe-models/"
            "face_landmarker/face_landmarker/float16/1/face_landmarker.task"
        )
        print(f"[IrisTracker] Downloading model from {url} ...")
        urllib.request.urlretrieve(url, _MODEL_PATH)
        print("[IrisTracker] Model downloaded.")

    def _iris_ratio(self, landmarks, iris_indices, contour_indices, w, h):
        iris_pts    = np.array([[landmarks[i].x * w, landmarks[i].y * h] for i in iris_indices])
        contour_pts = np.array([[landmarks[i].x * w, landmarks[i].y * h] for i in contour_indices])

        iris_cx, iris_cy = iris_pts.mean(axis=0)
        x_min, x_max = contour_pts[:, 0].min(), contour_pts[:, 0].max()
        y_min, y_max = contour_pts[:, 1].min(), contour_pts[:, 1].max()

        rx = (iris_cx - x_min) / ((x_max - x_min) or 1.0)
        ry = (iris_cy - y_min) / ((y_max - y_min) or 1.0)
        return rx, ry

    def _ratio_to_gaze(self, rx, ry) -> GazeDirection:
        h_dir = "left" if rx < self.H_RATIO_LEFT else ("right" if rx > self.H_RATIO_RIGHT else "center")
        v_dir = "up"   if ry < self.V_RATIO_TOP  else ("down"  if ry > self.V_RATIO_BOT   else "center")
        return GazeDirection(h_dir, v_dir)

    def track(self, frame_bgr: np.ndarray) -> tuple[int, list[GazeDirection]]:
        h, w = frame_bgr.shape[:2]
        # Tasks API expects RGB
        rgb_frame = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        mp_image  = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)

        result = self._landmarker.detect(mp_image)

        if not result.face_landmarks:
            return 0, []

        gazes = []
        for face_lm in result.face_landmarks:
            lrx, lry = self._iris_ratio(face_lm, _LEFT_IRIS,  _LEFT_EYE_CONTOUR,  w, h)
            rrx, rry = self._iris_ratio(face_lm, _RIGHT_IRIS, _RIGHT_EYE_CONTOUR, w, h)
            left_g  = self._ratio_to_gaze(lrx, lry)
            right_g = self._ratio_to_gaze(rrx, rry)
            h_dir = left_g.horizontal if left_g.horizontal == right_g.horizontal else "center"
            v_dir = left_g.vertical   if left_g.vertical   == right_g.vertical   else "center"
            gazes.append(GazeDirection(h_dir, v_dir))

        return len(result.face_landmarks), gazes

    def get_face_boxes(self, frame_bgr: np.ndarray) -> list[tuple[int,int,int,int]]:
        """Derive bounding boxes from FaceLandmarker results (no second model needed)."""
        h, w = frame_bgr.shape[:2]
        rgb_frame = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        mp_image  = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)
        result    = self._landmarker.detect(mp_image)

        boxes = []
        for face_lm in result.face_landmarks:
            xs = [lm.x * w for lm in face_lm]
            ys = [lm.y * h for lm in face_lm]
            x0, y0 = int(min(xs)), int(min(ys))
            x1, y1 = int(max(xs)), int(max(ys))
            boxes.append((x0, y0, x1 - x0, y1 - y0))
        return boxes


# ─────────────────────────────────────────────
# Interview Monitor
# ─────────────────────────────────────────────

class InterviewMonitor:
    FACE_ALERT_COUNT  = 2
    GAZE_AWAY_SECONDS = 2.5
    ALERT_COOLDOWN    = 5.0

    def __init__(self, candidate_name: str = "Candidate", save_report: bool = True):
        self.candidate_name = candidate_name
        self.save_report    = save_report
        self.session_id     = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Single MediaPipe tracker handles both face-count AND gaze
        self.iris_tracker = IrisTracker()

        # State
        self.alerts: list[AlertEvent] = []
        self.start_time  = time.time()
        self.frame_count = 0

        self.gaze_away_start: Optional[float] = None
        self.last_gaze: Optional[GazeDirection] = None
        self.last_alert_time: dict[str, float] = {}

        self.multi_face_frames = 0
        self.no_face_frames    = 0
        self.gaze_away_events  = 0

        print(f"[InterviewMonitor] Session {self.session_id} started for '{candidate_name}'.")

    # ── Alert helpers (unchanged) ──────────────────────────────────────────────

    def _can_alert(self, event_type: str) -> bool:
        return (time.time() - self.last_alert_time.get(event_type, 0)) >= self.ALERT_COOLDOWN

    def _log_alert(self, event_type: str, details: str):
        if not self._can_alert(event_type):
            return
        evt = AlertEvent(
            timestamp  = datetime.now().strftime("%H:%M:%S"),
            event_type = event_type,
            details    = details,
        )
        self.alerts.append(evt)
        self.last_alert_time[event_type] = time.time()
        print(f"  ⚠  ALERT [{evt.timestamp}] {event_type}: {details}")

    # ── Per-frame processing ───────────────────────────────────────────────────

    def process_frame(self, frame: np.ndarray) -> np.ndarray:
        self.frame_count += 1
        overlay = frame.copy()

        # One call → face count + per-face gaze directions
        face_count, gazes = self.iris_tracker.track(frame)

        # ── Face-count checks ──────────────────────────────────────────────────
        if face_count == 0:
            self.no_face_frames += 1
            self._log_alert("NO_FACE", "No face detected in frame.")
            self._draw_status(overlay, "WARNING: NO FACE DETECTED", (0, 0, 255))

        elif face_count >= self.FACE_ALERT_COUNT:
            self.multi_face_frames += 1
            self._log_alert("MULTIPLE_FACES", f"{face_count} faces detected.")
            self._draw_status(overlay, f"WARNING: {face_count} FACES DETECTED!", (0, 0, 255))

        else:
            self._draw_status(overlay, "Face OK", (0, 200, 0))

        # ── Draw face boxes (lightweight second pass for visualisation) ────────
        try:
            boxes = self.iris_tracker.get_face_boxes(frame)
            for i, (x, y, w, h) in enumerate(boxes):
                color = (0, 255, 0) if i == 0 else (0, 0, 255)
                label = "Candidate" if i == 0 else f"Intruder {i}"
                cv2.rectangle(overlay, (x, y), (x+w, y+h), color, 2)
                cv2.putText(overlay, label, (x, y - 8),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
        except Exception:
            pass

        # ── Gaze check (use first / candidate face only) ───────────────────────
        if gazes:
            gaze = gazes[0]
            self.last_gaze  = gaze
            looking_away    = gaze.horizontal != "center" or gaze.vertical != "center"

            if looking_away:
                if self.gaze_away_start is None:
                    self.gaze_away_start = time.time()
                elapsed = time.time() - self.gaze_away_start
                if elapsed >= self.GAZE_AWAY_SECONDS:
                    self.gaze_away_events += 1
                    self._log_alert(
                        "GAZE_AWAY",
                        f"Looking {gaze.horizontal}/{gaze.vertical} for {elapsed:.1f}s."
                    )
            else:
                self.gaze_away_start = None

            gaze_color = (0, 255, 255) if not looking_away else (0, 140, 255)
            cv2.putText(
                overlay,
                f"Gaze: {gaze.horizontal} / {gaze.vertical}",
                (10, overlay.shape[0] - 15),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, gaze_color, 2,
            )

        # ── HUD ───────────────────────────────────────────────────────────────
        elapsed_total = int(time.time() - self.start_time)
        cv2.putText(overlay,
            f"Session: {self.session_id}  |  Candidate: {self.candidate_name}  |  Elapsed: {elapsed_total}s",
            (10, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (220, 220, 220), 1)
        cv2.putText(overlay,
            f"Alerts: {len(self.alerts)}  |  Frame: {self.frame_count}",
            (10, 44), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (220, 220, 220), 1)

        return overlay

    # ── Drawing helpers (unchanged) ────────────────────────────────────────────

    def _draw_status(self, frame, text, color):
        cv2.putText(frame, text, (10, frame.shape[0] - 45),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.75, color, 2)

    # ── Report (unchanged) ────────────────────────────────────────────────────

    def generate_report(self) -> SessionReport:
        end_time = time.time()
        duration = end_time - self.start_time
        report = SessionReport(
            session_id       = self.session_id,
            start_time       = datetime.fromtimestamp(self.start_time).strftime("%Y-%m-%d %H:%M:%S"),
            end_time         = datetime.fromtimestamp(end_time).strftime("%Y-%m-%d %H:%M:%S"),
            duration_seconds = round(duration, 2),
            total_frames     = self.frame_count,
            alerts           = [asdict(a) for a in self.alerts],
            stats            = {
                "total_alerts"        : len(self.alerts),
                "multiple_face_frames": self.multi_face_frames,
                "no_face_frames"      : self.no_face_frames,
                "gaze_away_events"    : self.gaze_away_events,
                "suspicious_score"    : self._suspicion_score(),
            },
        )
        if self.save_report:
            fname = f"interview_report_{self.session_id}.json"
            with open(fname, "w") as f:
                json.dump(asdict(report), f, indent=2)
            print(f"[InterviewMonitor] Report saved → {fname}")
        return report

    def _suspicion_score(self) -> str:
        score = (
            len(self.alerts)       * 10
            + self.multi_face_frames * 2
            + self.gaze_away_events  * 5
        )
        if score == 0:   return "Clean (0)"
        if score < 30:   return f"Low ({score})"
        if score < 70:   return f"Medium ({score})"
        return               f"High ({score})"

    def print_report_summary(self, report: SessionReport):
        print("\n" + "="*55)
        print("          INTERVIEW SESSION REPORT")
        print("="*55)
        print(f"  Session ID      : {report.session_id}")
        print(f"  Candidate       : {self.candidate_name}")
        print(f"  Duration        : {report.duration_seconds}s")
        print(f"  Frames analysed : {report.total_frames}")
        print("-"*55)
        s = report.stats
        print(f"  Total alerts    : {s['total_alerts']}")
        print(f"  Multi-face frames: {s['multiple_face_frames']}")
        print(f"  No-face frames  : {s['no_face_frames']}")
        print(f"  Gaze-away events: {s['gaze_away_events']}")
        print(f"  Suspicion score : {s['suspicious_score']}")
        if report.alerts:
            print("  Recent alerts (last 5):")
            for a in report.alerts[-5:]:
                print(f"    [{a['timestamp']}] {a['event_type']}: {a['details']}")
        print("="*55 + "\n")


# ─────────────────────────────────────────────
# Main entry point (unchanged)
# ─────────────────────────────────────────────

def run(candidate_name="John Doe", camera_index=0, save_report=True):
    monitor = InterviewMonitor(candidate_name=candidate_name, save_report=save_report)
    cap = cv2.VideoCapture(camera_index)
    if not cap.isOpened():
        print(f"[ERROR] Cannot open camera {camera_index}.")
        return
    cap.set(cv2.CAP_PROP_FRAME_WIDTH,  1280)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
    print("Press Q or ESC to end the session.")
    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            cv2.imshow("Interview Monitor", monitor.process_frame(frame))
            if cv2.waitKey(1) & 0xFF in (ord("q"), ord("Q"), 27):
                break
    finally:
        cap.release()
        cv2.destroyAllWindows()
        monitor.print_report_summary(monitor.generate_report())


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--name",      default="Candidate")
    p.add_argument("--camera",    type=int, default=0)
    p.add_argument("--no-report", action="store_true")
    args = p.parse_args()
    run(args.name, args.camera, not args.no_report)