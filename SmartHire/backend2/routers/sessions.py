"""Session management endpoints."""
from fastapi import APIRouter, HTTPException

from models.schemas import SessionStatus, StartSessionRequest
from utils.session_store import store

router = APIRouter(prefix="/sessions", tags=["Sessions"])


@router.post("/start", response_model=SessionStatus, status_code=201)
async def start_session(body: StartSessionRequest):
    """
    Create a new monitoring session.

    Call this before sending any frames.  Pass a unique session_id
    (e.g. UUID) and optional configuration.
    """
    try:
        session = await store.create(body.session_id, body.config)
        return session.to_status()
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc))


@router.post("/{session_id}/end", response_model=SessionStatus)
async def end_session(session_id: str):
    """
    Mark a session as ended and freeze its data for report generation.
    """
    try:
        session = await store.end(session_id)
        return session.to_status()
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.get("/{session_id}/status", response_model=SessionStatus)
async def get_session_status(session_id: str):
    session = await store.get(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found")
    return session.to_status()


@router.get("/", response_model=list[SessionStatus])
async def list_active_sessions():
    return await store.list_active()


@router.delete("/{session_id}", status_code=204)
async def delete_session(session_id: str):
    await store.delete(session_id)
