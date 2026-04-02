/**
 * InterviewMonitorClient
 * ─────────────────────
 * Drop this into your frontend to stream webcam frames to the
 * FastAPI video-monitor server and receive real-time analysis.
 *
 * Usage
 * -----
 *   const client = new InterviewMonitorClient({ baseUrl: 'http://localhost:8000' });
 *
 *   await client.startSession({
 *     session_id: crypto.randomUUID(),
 *     config: { candidate_name: 'Jane Doe', job_role: 'Senior Engineer' }
 *   });
 *
 *   // Attach to a <video> element
 *   client.startStreaming(videoElement, {
 *     fps: 5,
 *     onFrame: (analysis) => updateOverlay(analysis),
 *     onAlert: (alert)    => showAlert(alert),
 *   });
 *
 *   // When interview ends
 *   const report = await client.endSessionAndGetReport();
 */

export class InterviewMonitorClient {
  /**
   * @param {Object} opts
   * @param {string} opts.baseUrl  - FastAPI base URL (no trailing slash)
   */
  constructor({ baseUrl = 'http://localhost:8000' } = {}) {
    this.baseUrl = baseUrl;
    this._sessionId = null;
    this._frameIndex = 0;
    this._streamInterval = null;
    this._canvas = document.createElement('canvas');
    this._ctx = this._canvas.getContext('2d');
  }

  // ── Session lifecycle ──────────────────────────────────────────────────────

  /**
   * Create a new monitoring session on the server.
   * @param {Object} body  - { session_id, config: { candidate_name, job_role, ... } }
   */
  async startSession(body) {
    const res = await fetch(`${this.baseUrl}/sessions/start`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
    if (!res.ok) throw new Error(`startSession failed: ${await res.text()}`);
    this._sessionId = body.session_id;
    this._frameIndex = 0;
    return res.json();
  }

  async endSession() {
    if (!this._sessionId) throw new Error('No active session');
    this.stopStreaming();
    const res = await fetch(`${this.baseUrl}/sessions/${this._sessionId}/end`, {
      method: 'POST',
    });
    if (!res.ok) throw new Error(`endSession failed: ${await res.text()}`);
    return res.json();
  }

  async getSessionStatus() {
    if (!this._sessionId) throw new Error('No active session');
    const res = await fetch(`${this.baseUrl}/sessions/${this._sessionId}/status`);
    return res.json();
  }

  // ── Frame streaming ────────────────────────────────────────────────────────

  /**
   * Begin capturing frames from a <video> element and streaming them.
   *
   * @param {HTMLVideoElement} videoEl
   * @param {Object} opts
   * @param {number}   opts.fps          - Capture rate (default: 5)
   * @param {number}   opts.quality      - JPEG quality 0–1 (default: 0.6)
   * @param {Function} opts.onFrame      - Called with FrameAnalysis on each frame
   * @param {Function} opts.onAlert      - Called with each alert string
   * @param {Function} opts.onError      - Called on network/server errors
   */
  startStreaming(videoEl, {
    fps = 5,
    quality = 0.6,
    onFrame = null,
    onAlert = null,
    onError = null,
  } = {}) {
    if (!this._sessionId) throw new Error('Call startSession() first');
    if (this._streamInterval) this.stopStreaming();

    const intervalMs = 1000 / fps;

    this._streamInterval = setInterval(async () => {
      try {
        const b64 = this._captureFrame(videoEl, quality);
        const analysis = await this._sendFrame(b64);

        onFrame?.(analysis);

        if (analysis.alerts?.length > 0) {
          analysis.alerts.forEach(alert => onAlert?.(alert));
        }
      } catch (err) {
        onError?.(err);
      }
    }, intervalMs);
  }

  stopStreaming() {
    if (this._streamInterval) {
      clearInterval(this._streamInterval);
      this._streamInterval = null;
    }
  }

  // ── Report ─────────────────────────────────────────────────────────────────

  /** Fetch full JSON report (can be called during or after session). */
  async getReport() {
    if (!this._sessionId) throw new Error('No active session');
    const res = await fetch(`${this.baseUrl}/reports/${this._sessionId}`);
    if (!res.ok) throw new Error(`getReport failed: ${await res.text()}`);
    return res.json();
  }

  /** Returns the URL of the HTML report page. */
  getReportHtmlUrl() {
    if (!this._sessionId) throw new Error('No active session');
    return `${this.baseUrl}/reports/${this._sessionId}/html`;
  }

  /** Convenience: end session then return the final report. */
  async endSessionAndGetReport() {
    await this.endSession();
    return this.getReport();
  }

  // ── Internal helpers ───────────────────────────────────────────────────────

  _captureFrame(videoEl, quality) {
    this._canvas.width = videoEl.videoWidth || 640;
    this._canvas.height = videoEl.videoHeight || 480;
    this._ctx.drawImage(videoEl, 0, 0);
    const dataUrl = this._canvas.toDataURL('image/jpeg', quality);
    // Strip the "data:image/jpeg;base64," prefix
    return dataUrl.split(',')[1];
  }

  async _sendFrame(b64) {
    const body = {
      session_id: this._sessionId,
      frame_index: this._frameIndex++,
      timestamp: performance.now() / 1000,
      image_b64: b64,
    };
    const res = await fetch(`${this.baseUrl}/monitor/analyze-frame`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
    if (!res.ok) throw new Error(`analyzeFrame failed: ${await res.text()}`);
    return res.json();
  }
}


// ── Overlay helper ─────────────────────────────────────────────────────────
/**
 * Renders a simple real-time overlay on a <canvas> placed over the video.
 * Call updateOverlay(analysis) from onFrame.
 */
export function createOverlayRenderer(canvasEl) {
  const ctx = canvasEl.getContext('2d');

  return function updateOverlay(analysis) {
    ctx.clearRect(0, 0, canvasEl.width, canvasEl.height);

    // Face bounding box
    const bbox = analysis.face?.bbox;
    if (bbox) {
      const [x, y, w, h] = bbox;
      const hasAlerts = analysis.alerts?.length > 0;
      ctx.strokeStyle = hasAlerts ? '#ef4444' : '#22c55e';
      ctx.lineWidth = 2;
      ctx.strokeRect(x, y, w, h);
    }

    // Confidence badge
    const cs = analysis.confidence_score;
    if (cs !== null && cs !== undefined) {
      const pct = Math.round(cs * 100);
      const color = pct >= 65 ? '#22c55e' : pct >= 45 ? '#f59e0b' : '#ef4444';
      ctx.fillStyle = 'rgba(0,0,0,0.55)';
      ctx.roundRect?.(8, 8, 130, 30, 6);
      ctx.fill();
      ctx.fillStyle = color;
      ctx.font = 'bold 13px system-ui';
      ctx.fillText(`Confidence: ${pct}%`, 16, 28);
    }

    // Gaze zone
    const zone = analysis.gaze?.attention_zone;
    if (zone && zone !== 'on_screen') {
      ctx.fillStyle = 'rgba(239,68,68,0.75)';
      ctx.font = 'bold 12px system-ui';
      ctx.fillText(`⚠ ${zone.replace(/_/g, ' ')}`, 8, 56);
    }
  };
}
