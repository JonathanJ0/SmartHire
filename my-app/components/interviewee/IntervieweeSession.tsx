"use client";

import { useRouter } from "next/navigation";
import { ChatBox } from "./ChatBox";
import { VideoCapture, MONITOR_SESSION_KEY } from "./VideoCapture";
import { INTERVIEW_SESSION_KEY } from "./ChatBox";

export const CODING_SESSION_KEY = "umamaj.codingSessionId";

export function IntervieweeSession() {
  const router = useRouter();
  const BACKEND_URL =
    process.env.NEXT_PUBLIC_BACKEND_URL?.trim() || "http://localhost:8000";

  const handleEndSession = async () => {
    try {
      if (typeof window !== "undefined") {
        const sessionId = localStorage.getItem(INTERVIEW_SESSION_KEY);
        const monitorId = localStorage.getItem(MONITOR_SESSION_KEY);
        if (sessionId) {
          localStorage.setItem(CODING_SESSION_KEY, sessionId);
          void fetch(`${BACKEND_URL}/api/interview/end`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              interview_session_id: sessionId,
              monitor_session_id: monitorId,
            }),
          });
        }
      }
    } catch {
      // Best-effort; still navigate to coding panel.
    } finally {
      router.push("/interviewee/coding");
    }
  };

  return (
    <div className="mt-8 flex flex-col gap-6 lg:flex-row lg:items-start">
      <div className="flex justify-end lg:order-2 lg:shrink-0">
        <VideoCapture autoStart />
      </div>

      <div className="flex flex-1 flex-col gap-6 lg:order-1 lg:min-w-0">
        <div className="min-h-[520px]">
          <ChatBox />
        </div>

        <div className="flex flex-col items-start gap-2 rounded-xl border border-[var(--color-border)] bg-[var(--color-surface-elevated)] px-4 py-3">
          <p className="text-sm text-[var(--color-muted)]">
            When you’re done with the interview, end the session to see your feedback.
          </p>
          <button
            type="button"
            onClick={() => void handleEndSession()}
            className="rounded-lg bg-[var(--color-primary)] px-4 py-2 text-sm font-medium text-white hover:bg-[var(--color-primary-hover)]"
          >
            End session &amp; move to coding
          </button>
        </div>
      </div>
    </div>
  );
}

