"""Frame analysis endpoint."""
from fastapi import APIRouter, HTTPException

from models.schemas import FrameAnalysis, FrameRequest
from video_monitor import monitor

router = APIRouter(prefix="/monitor", tags=["Monitoring"])


@router.post("/analyze-frame", response_model=FrameAnalysis)
async def analyze_frame(body: FrameRequest):
    """
    Submit a single video frame for analysis.

    The client should call this endpoint for every captured frame
    (or at the desired sampling rate).

    **image_b64**: Base64-encoded JPEG or PNG of the video frame.

    Returns a `FrameAnalysis` object with:
    - Face detection results (count, bbox, person-change flag)
    - Gaze estimation (yaw/pitch/roll + attention zone)
    - Emotion scores + confidence score (when scheduled)
    - Any triggered alerts for this frame
    """
    try:
        return await monitor.process_frame(body)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Frame processing error: {exc}")
