"use client";

import { useCallback, useEffect, useRef, useState } from "react";

type VideoCaptureProps = {
  autoStart?: boolean;
};

export const MONITOR_SESSION_KEY = "umamaj.monitor.session_id";

export function VideoCapture({ autoStart = false }: VideoCaptureProps) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const monitorSessionIdRef = useRef<string | null>(null);
  const monitorIntervalRef = useRef<number | null>(null);
  const [isLive, setIsLive] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [monitorError, setMonitorError] = useState<string | null>(null);
  const [monitorStatus, setMonitorStatus] = useState<
    | {
        connected: boolean;
        alertsCount: number;
        lastAlert?: { event_type: string; details: string; timestamp: string } | null;
        gaze?: { horizontal: string; vertical: string } | null;
        suspicionScore?: string | null;
      }
    | null
  >(null);

  const BACKEND_URL =
    process.env.NEXT_PUBLIC_BACKEND_URL?.trim() || "http://localhost:8000";

  const startVideo = useCallback(async () => {
    setError(null);
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { width: 1280, height: 720 },
        audio: true,
      });
      streamRef.current = stream;
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
      }
      setIsLive(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not access camera");
    }
  }, []);

  const stopVideo = useCallback(() => {
    streamRef.current?.getTracks().forEach((t) => t.stop());
    streamRef.current = null;
    if (videoRef.current) {
      videoRef.current.srcObject = null;
    }
    setIsLive(false);
  }, []);

  const stopMonitoring = useCallback(async () => {
    if (monitorIntervalRef.current) {
      window.clearInterval(monitorIntervalRef.current);
      monitorIntervalRef.current = null;
    }
    const sessionId = monitorSessionIdRef.current;
    monitorSessionIdRef.current = null;
    if (typeof window !== "undefined") {
      localStorage.removeItem(MONITOR_SESSION_KEY);
    }
    if (!sessionId) return;

    try {
      const res = await fetch(`${BACKEND_URL}/api/session/end`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ session_id: sessionId }),
      });
      if (res.ok) {
        const data = (await res.json()) as { report?: unknown };
        localStorage.setItem(
          "umamaj.monitor.report",
          JSON.stringify({ sessionId, ...data })
        );
      }
    } catch {
      // ignore backend end-session errors on cleanup
    }
  }, [BACKEND_URL]);

  const startMonitoring = useCallback(async () => {
    setMonitorError(null);
    try {
      const res = await fetch(`${BACKEND_URL}/api/session/start`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ candidate_name: "Candidate" }),
      });
      if (!res.ok) {
        throw new Error(`Backend returned ${res.status}`);
      }
      const startData = (await res.json()) as { session_id: string };
      monitorSessionIdRef.current = startData.session_id;
      if (typeof window !== "undefined") {
        localStorage.setItem(MONITOR_SESSION_KEY, startData.session_id);
      }
      setMonitorStatus({
        connected: true,
        alertsCount: 0,
        lastAlert: null,
        gaze: null,
        suspicionScore: null,
      });

      const sendFrame = async () => {
        const sessionId = monitorSessionIdRef.current;
        const video = videoRef.current;
        if (!sessionId || !video) return;
        if (video.videoWidth === 0 || video.videoHeight === 0) return;

        const canvas = document.createElement("canvas");
        canvas.width = video.videoWidth;
        canvas.height = video.videoHeight;
        const ctx = canvas.getContext("2d");
        if (!ctx) return;
        ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
        const image_data_url = canvas.toDataURL("image/jpeg", 0.6);

        const frameRes = await fetch(`${BACKEND_URL}/api/session/frame`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            session_id: sessionId,
            image_data_url,
            return_overlay: false,
          }),
        });
        if (!frameRes.ok) {
          throw new Error(`Frame request failed: ${frameRes.status}`);
        }
        const frameData = (await frameRes.json()) as {
          alerts_count: number;
          last_alert?: { event_type: string; details: string; timestamp: string } | null;
          gaze?: { horizontal: string; vertical: string } | null;
          stats?: { suspicion_score?: string | null };
        };

        setMonitorStatus((prev) => ({
          connected: true,
          alertsCount: frameData.alerts_count ?? prev?.alertsCount ?? 0,
          lastAlert: frameData.last_alert ?? prev?.lastAlert ?? null,
          gaze: frameData.gaze ?? prev?.gaze ?? null,
          suspicionScore: frameData.stats?.suspicion_score ?? prev?.suspicionScore ?? null,
        }));
      };

      // low FPS to keep payload small during development
      monitorIntervalRef.current = window.setInterval(() => {
        void sendFrame().catch((e) => {
          setMonitorError(e instanceof Error ? e.message : "Monitor error");
          setMonitorStatus((prev) => (prev ? { ...prev, connected: false } : prev));
        });
      }, 1000);
    } catch (e) {
      setMonitorError(e instanceof Error ? e.message : "Could not connect to backend");
      setMonitorStatus({ connected: false, alertsCount: 0 });
    }
  }, [BACKEND_URL]);

  useEffect(() => {
    if (!autoStart) return;
    if (isLive) return;
    if (error) return;
    void startVideo();
  }, [autoStart, error, isLive, startVideo]);

  useEffect(() => {
    if (!isLive) return;
    void startMonitoring();
    return () => {
      void stopMonitoring();
    };
  }, [isLive, startMonitoring, stopMonitoring]);

  useEffect(() => {
    return () => {
      stopVideo();
      void stopMonitoring();
    };
  }, [stopMonitoring, stopVideo]);

  return (
    <div className="flex flex-col rounded-xl overflow-hidden border border-[var(--color-border)] bg-black/5 w-full max-w-[280px] shrink-0">
      <div className="relative aspect-video max-h-[160px] bg-black/10">
        <video
          ref={videoRef}
          autoPlay
          playsInline
          muted
          className="h-full w-full object-cover"
        />
        {monitorStatus && (
          <div className="absolute top-2 right-2 flex flex-col gap-1 rounded-lg bg-black/60 px-2 py-1 text-[11px] text-white">
            <div className="flex items-center justify-between gap-2">
              <span className="opacity-90">Monitor</span>
              <span
                className={`h-2 w-2 rounded-full ${
                  monitorStatus.connected ? "bg-emerald-400" : "bg-red-400"
                }`}
                aria-label={monitorStatus.connected ? "connected" : "disconnected"}
              />
            </div>
            <div className="flex items-center justify-between gap-2">
              <span className="opacity-90">Alerts</span>
              <span className="font-medium">{monitorStatus.alertsCount}</span>
            </div>
            {monitorStatus.gaze && (
              <div className="opacity-90">
                Gaze: {monitorStatus.gaze.horizontal}/{monitorStatus.gaze.vertical}
              </div>
            )}
          </div>
        )}
        {monitorError && (
          <div className="absolute bottom-2 right-2 rounded-lg bg-red-600/90 px-2 py-1 text-[11px] text-white">
            Monitor error
          </div>
        )}
        {!isLive && !error && (
          <div className="absolute inset-0 flex flex-col items-center justify-center gap-3 bg-[var(--color-surface)]">
            <span className="text-4xl opacity-60">📷</span>
            <p className="text-sm text-[var(--color-muted)]">Camera off</p>
            <button
              type="button"
              onClick={startVideo}
              className="rounded-lg bg-[var(--color-primary)] px-4 py-2 text-sm font-medium text-white hover:bg-[var(--color-primary-hover)]"
            >
              Start camera
            </button>
          </div>
        )}
        {error && (
          <div className="absolute inset-0 flex flex-col items-center justify-center gap-3 bg-[var(--color-surface)] p-4">
            <span className="text-4xl opacity-60">⚠️</span>
            <p className="text-sm text-red-600">{error}</p>
            <button
              type="button"
              onClick={startVideo}
              className="rounded-lg bg-[var(--color-primary)] px-4 py-2 text-sm font-medium text-white hover:bg-[var(--color-primary-hover)]"
            >
              Try again
            </button>
          </div>
        )}
        {isLive && (
          <div className="absolute bottom-2 left-2 flex items-center gap-1.5 rounded-full bg-red-500/90 px-2 py-1 text-xs font-medium text-white">
            <span className="h-1.5 w-1.5 rounded-full bg-white animate-pulse" />
            Live
          </div>
        )}
      </div>
      {isLive && (
        <div className="flex justify-end border-t border-[var(--color-border)] p-2">
          <button
            type="button"
            onClick={() => {
              stopVideo();
              void stopMonitoring();
            }}
            className="rounded-lg border border-[var(--color-border)] px-3 py-1.5 text-sm hover:bg-black/5"
          >
            Stop camera
          </button>
        </div>
      )}
    </div>
  );
}
