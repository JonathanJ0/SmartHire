"""Report generation endpoints."""
from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse

from models.schemas import InterviewReport
from utils.report_generator import generate_report
from utils.session_store import store

router = APIRouter(prefix="/reports", tags=["Reports"])


@router.get("/{session_id}", response_model=InterviewReport)
async def get_report(session_id: str):
    """
    Generate and return the full interview report for a session.

    Can be called while the session is still active (live report)
    or after it has been ended.
    """
    session = await store.get(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found")
    return generate_report(session)


@router.get("/{session_id}/html", response_class=HTMLResponse)
async def get_report_html(session_id: str):
    """
    Returns a self-contained HTML report page suitable for embedding
    in an iframe or opening in a new tab.
    """
    session = await store.get(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found")

    report = generate_report(session)
    return _render_html(report)


def _render_html(r: InterviewReport) -> str:
    trend_js = str([round(v, 3) for v in r.emotion_summary.confidence_trend])

    face_rows = f"""
        <tr><td>Frames with face</td><td>{r.face_summary.frames_with_face} / {r.face_summary.total_frames} ({r.face_summary.face_presence_pct}%)</td></tr>
        <tr><td>Multiple-face frames</td><td>{r.face_summary.frames_multiple_faces}</td></tr>
        <tr><td>Person-change events</td><td class="{'warn' if r.face_summary.person_change_events > 0 else ''}">{r.face_summary.person_change_events}</td></tr>
    """

    gaze_rows = f"""
        <tr><td>On screen</td><td>{r.gaze_summary.pct_on_screen}%</td></tr>
        <tr><td>Looking away</td><td class="{'warn' if r.gaze_summary.pct_looking_away > 20 else ''}">{r.gaze_summary.pct_looking_away}%</td></tr>
        <tr><td>Looking down</td><td>{r.gaze_summary.pct_looking_down}%</td></tr>
        <tr><td>Looking up</td><td>{r.gaze_summary.pct_looking_up}%</td></tr>
    """

    e = r.emotion_summary.avg_scores
    emotion_bars = "".join(
        f'<div class="ebar"><span>{label}</span>'
        f'<div class="bar-bg"><div class="bar-fill" style="width:{val*100:.1f}%"></div></div>'
        f'<span>{val*100:.1f}%</span></div>'
        for label, val in [
            ("Happy", e.happy), ("Neutral", e.neutral), ("Surprise", e.surprise),
            ("Sad", e.sad), ("Fear", e.fear), ("Angry", e.angry), ("Disgust", e.disgust),
        ]
    )

    alerts_html = "".join(
        f'<div class="alert-row"><span class="badge {a.alert_type}">{a.alert_type}</span>'
        f'<span class="ts">{a.timestamp:.1f}s</span> {a.detail}</div>'
        for a in r.alerts[:50]
    ) or "<p style='color:#6b7280'>No alerts recorded.</p>"

    integrity_color = "#22c55e" if r.integrity_score >= 0.8 else "#f59e0b" if r.integrity_score >= 0.5 else "#ef4444"
    conf_color = "#22c55e" if r.overall_confidence_score >= 0.65 else "#f59e0b" if r.overall_confidence_score >= 0.45 else "#ef4444"

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Interview Report – {r.candidate_name}</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
<style>
  *{{box-sizing:border-box;margin:0;padding:0}}
  body{{font-family:system-ui,sans-serif;background:#f8fafc;color:#1e293b;padding:24px}}
  h1{{font-size:1.5rem;font-weight:700;margin-bottom:4px}}
  .meta{{color:#64748b;font-size:.875rem;margin-bottom:24px}}
  .grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:16px;margin-bottom:24px}}
  .card{{background:#fff;border-radius:12px;padding:20px;box-shadow:0 1px 3px rgba(0,0,0,.08)}}
  .card h2{{font-size:.9rem;text-transform:uppercase;letter-spacing:.05em;color:#94a3b8;margin-bottom:12px}}
  table{{width:100%;border-collapse:collapse;font-size:.875rem}}
  td{{padding:6px 4px;border-bottom:1px solid #f1f5f9}}
  td:first-child{{color:#64748b}}
  td:last-child{{text-align:right;font-weight:500}}
  .warn{{color:#f59e0b}}
  .score-big{{font-size:2.5rem;font-weight:700;line-height:1}}
  .score-label{{font-size:.75rem;color:#94a3b8;margin-top:4px}}
  .verdict{{background:#eff6ff;border-left:4px solid #3b82f6;padding:12px 16px;border-radius:0 8px 8px 0;font-size:.9rem;margin-bottom:24px}}
  .ebar{{display:flex;align-items:center;gap:8px;margin-bottom:6px;font-size:.8rem}}
  .ebar span:first-child{{width:68px;color:#64748b}}
  .bar-bg{{flex:1;height:8px;background:#f1f5f9;border-radius:4px;overflow:hidden}}
  .bar-fill{{height:100%;background:#6366f1;border-radius:4px}}
  .alert-row{{display:flex;align-items:center;gap:8px;padding:6px 0;border-bottom:1px solid #f1f5f9;font-size:.8rem}}
  .badge{{display:inline-block;padding:2px 6px;border-radius:4px;font-size:.7rem;font-weight:600;background:#fee2e2;color:#991b1b}}
  .badge.gaze_away{{background:#fef3c7;color:#92400e}}
  .badge.face_absent{{background:#fee2e2;color:#991b1b}}
  .badge.multiple_faces{{background:#ede9fe;color:#5b21b6}}
  .badge.general{{background:#f0fdf4;color:#166534}}
  .ts{{color:#94a3b8;min-width:48px}}
  canvas{{max-height:180px}}
</style>
</head>
<body>
<h1>Interview Report: {r.candidate_name}</h1>
<div class="meta">Role: {r.job_role or "—"} &nbsp;·&nbsp; Duration: {r.duration_seconds:.0f}s &nbsp;·&nbsp; Frames: {r.total_frames} &nbsp;·&nbsp; {r.started_at.strftime("%Y-%m-%d %H:%M")} UTC</div>

<div class="verdict">{r.verdict}</div>

<div class="grid">
  <div class="card">
    <h2>Confidence Score</h2>
    <div class="score-big" style="color:{conf_color}">{r.overall_confidence_score:.0%}</div>
    <div class="score-label">Emotion × gaze weighted</div>
  </div>
  <div class="card">
    <h2>Integrity Score</h2>
    <div class="score-big" style="color:{integrity_color}">{r.integrity_score:.0%}</div>
    <div class="score-label">Penalised for person changes</div>
  </div>
  <div class="card">
    <h2>Dominant Emotion</h2>
    <div class="score-big" style="color:#6366f1;font-size:1.8rem">{r.emotion_summary.dominant_emotion.capitalize()}</div>
    <div class="score-label">Avg confidence: {r.emotion_summary.avg_confidence_score:.0%}</div>
  </div>
</div>

<div class="grid">
  <div class="card">
    <h2>Face Monitoring</h2>
    <table>{face_rows}</table>
  </div>
  <div class="card">
    <h2>Gaze / Attention</h2>
    <table>{gaze_rows}</table>
  </div>
  <div class="card">
    <h2>Emotion Breakdown</h2>
    {emotion_bars}
  </div>
</div>

<div class="card" style="margin-bottom:24px">
  <h2>Confidence Trend</h2>
  <canvas id="trendChart"></canvas>
</div>

<div class="card">
  <h2>Alerts ({len(r.alerts)})</h2>
  {alerts_html}
</div>

<script>
const trend = {trend_js};
new Chart(document.getElementById('trendChart'), {{
  type: 'line',
  data: {{
    labels: trend.map((_,i) => i),
    datasets: [{{
      label: 'Confidence',
      data: trend,
      borderColor: '#6366f1',
      backgroundColor: 'rgba(99,102,241,0.08)',
      tension: 0.4,
      fill: true,
      pointRadius: 0,
    }}]
  }},
  options: {{
    responsive: true,
    scales: {{
      y: {{ min: 0, max: 1, ticks: {{ callback: v => (v*100).toFixed(0)+'%' }} }},
      x: {{ display: false }}
    }},
    plugins: {{ legend: {{ display: false }} }}
  }}
}});
</script>
</body>
</html>"""
