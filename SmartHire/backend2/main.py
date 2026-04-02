"""
Interview Monitor – FastAPI Application
========================================

Endpoints
---------
POST  /sessions/start                 – create a new monitoring session
POST  /sessions/{id}/end              – end a session
GET   /sessions/{id}/status           – live session status
GET   /sessions/                      – list active sessions
DELETE /sessions/{id}                 – delete session data

POST  /monitor/analyze-frame          – submit a frame for analysis

GET   /reports/{id}                   – JSON report
GET   /reports/{id}/html              – self-contained HTML report

Run
---
    uvicorn main:app --host 0.0.0.0 --port 8000 --reload
"""
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routers import monitor, reports, sessions
from video_monitor import monitor as vm

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

app = FastAPI(
    title="Interview Video Monitor",
    description=(
        "Real-time video monitoring for interview evaluation. "
        "Detects faces, gaze direction, person changes, and emotional confidence."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Allow any origin in dev – tighten in production
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(sessions.router)
app.include_router(monitor.router)
app.include_router(reports.router)


@app.on_event("shutdown")
def on_shutdown():
    vm.shutdown()


@app.get("/health", tags=["Health"])
async def health():
    return {"status": "ok", "version": "1.0.0"}
