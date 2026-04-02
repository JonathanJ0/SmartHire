"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { RESUME_ID_KEY } from "./ResumeUploader";

export type ChatMessage = {
  id: string;
  role: "user" | "ai";
  content: string;
  timestamp: Date;
};

type ChatBoxProps = {
  isSessionEnded?: boolean;
};

export const CHAT_STORAGE_KEY = "umamaj.interviewee.chat";
export const INTERVIEW_SESSION_KEY = "umamaj.interviewSessionId";

export function ChatBox({ isSessionEnded = false }: ChatBoxProps) {
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: "welcome",
      role: "ai",
      content:
        "Hi! I’m your AI interviewer. When you’re ready, tell me a bit about yourself and we’ll start the session.",
      timestamp: new Date(),
    },
  ]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [hasSpeechSupport, setHasSpeechSupport] = useState(false);
  const [isRecording, setIsRecording] = useState(false);
  const [speechError, setSpeechError] = useState<string | null>(null);
  const [interviewSessionId, setInterviewSessionId] = useState<string | null>(null);
  const [interviewError, setInterviewError] = useState<string | null>(null);
  const [audioEnabled, setAudioEnabled] = useState(true);
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const lastObjectUrlRef = useRef<string | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);

  const BACKEND_URL =
    process.env.NEXT_PUBLIC_BACKEND_URL?.trim() || "http://localhost:8000";

  const playTts = useCallback(
    async (text: string) => {
      if (!audioEnabled) return;
      const clean = text.trim();
      if (!clean) return;
      try {
        const res = await fetch(`${BACKEND_URL}/api/tts`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ text: clean }),
        });
        if (!res.ok) return;
        const blob = await res.blob();
        const url = URL.createObjectURL(blob);

        if (!audioRef.current) audioRef.current = new Audio();
        const audio = audioRef.current;

        if (lastObjectUrlRef.current) {
          URL.revokeObjectURL(lastObjectUrlRef.current);
        }
        lastObjectUrlRef.current = url;

        audio.src = url;
        audio.volume = 1.0;
        await audio.play();
      } catch {
        // Autoplay may be blocked; fail silently.
      }
    },
    [BACKEND_URL, audioEnabled]
  );

  const scrollToBottom = useCallback(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, []);

  useEffect(() => {
    return () => {
      if (lastObjectUrlRef.current) {
        URL.revokeObjectURL(lastObjectUrlRef.current);
        lastObjectUrlRef.current = null;
      }
    };
  }, []);

  useEffect(() => {
    if (typeof window === "undefined") return;
    const raw = localStorage.getItem(CHAT_STORAGE_KEY);
    if (!raw) return;
    try {
      const parsed = JSON.parse(raw) as Array<
        Omit<ChatMessage, "timestamp"> & { timestamp: string }
      >;
      setMessages(
        parsed.map((m) => ({ ...m, timestamp: new Date(m.timestamp) }))
      );
    } catch {
      // ignore and keep default welcome message
    }
  }, []);

  useEffect(() => {
    if (typeof window === "undefined") return;
    const serializable = messages.map((m) => ({
      ...m,
      timestamp: m.timestamp.toISOString(),
    }));
    localStorage.setItem(CHAT_STORAGE_KEY, JSON.stringify(serializable));
  }, [messages]);

  useEffect(() => {
    if (typeof window === "undefined") return;
    const SpeechCtor =
      (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
    if (SpeechCtor) {
      setHasSpeechSupport(true);
    }
  }, []);

  useEffect(() => {
    if (typeof window === "undefined") return;
    if (isSessionEnded) return;
    if (interviewSessionId) return;

    const resumeId = localStorage.getItem(RESUME_ID_KEY);
    if (!resumeId) return;

    setInterviewError(null);
    setIsLoading(true);

    fetch(`${BACKEND_URL}/api/interview/start`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ resume_id: resumeId, role: "Software Engineer" }),
    })
      .then(async (res) => {
        if (!res.ok) {
          const body = await res.json().catch(() => null);
          const detail =
            body && typeof body === "object" && "detail" in body
              ? String((body as any).detail)
              : `Failed to start interview (${res.status})`;
          throw new Error(detail);
        }
        return res.json() as Promise<{
          interview_session_id: string;
          opening_message: string;
        }>;
      })
      .then((data) => {
        setInterviewSessionId(data.interview_session_id);
        if (typeof window !== "undefined") {
          localStorage.setItem(
            INTERVIEW_SESSION_KEY,
            data.interview_session_id
          );
        }
        void playTts(data.opening_message);
        setMessages((prev) => [
          ...prev,
          {
            id: `ai-opening-${Date.now()}`,
            role: "ai",
            content: data.opening_message,
            timestamp: new Date(),
          },
        ]);
      })
      .catch((e) => {
        setInterviewError(e instanceof Error ? e.message : "Failed to start interview.");
      })
      .finally(() => {
        setIsLoading(false);
        scrollToBottom();
      });
  }, [BACKEND_URL, interviewSessionId, isSessionEnded, playTts, scrollToBottom]);

  const sendMessageFromText = useCallback(
    async (text: string) => {
      const trimmed = text.trim();
      if (!trimmed || isLoading) return;
      if (!interviewSessionId) {
        setInterviewError("Interview is not ready yet. Please wait a moment.");
        return;
      }

      const userMsg: ChatMessage = {
        id: `user-${Date.now()}`,
        role: "user",
        content: trimmed,
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, userMsg]);
      setIsLoading(true);
      scrollToBottom();

      try {
        const res = await fetch(`${BACKEND_URL}/api/interview/message`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            interview_session_id: interviewSessionId,
            user_text: trimmed,
          }),
        });
        if (!res.ok) {
          const body = await res.json().catch(() => null);
          const detail =
            body && typeof body === "object" && "detail" in body
              ? String((body as any).detail)
              : `Interview request failed (${res.status})`;
          throw new Error(detail);
        }
        const data = (await res.json()) as {
          assistant_message: string;
          is_concluded: boolean;
        };
        const aiMsg: ChatMessage = {
          id: `ai-${Date.now()}`,
          role: "ai",
          content: data.assistant_message,
          timestamp: new Date(),
        };
        setMessages((prev) => [...prev, aiMsg]);
        // Attach this utterance to the speech statistics pipeline.
        void fetch(`${BACKEND_URL}/api/speech/analyse-text`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            text: trimmed,
            interview_session_id: interviewSessionId,
          }),
        }).catch(() => {
          // Ignore analysis errors for UI flow.
        });
        void playTts(data.assistant_message);
      } catch (e) {
        setInterviewError(e instanceof Error ? e.message : "Interview failed.");
      } finally {
        setIsLoading(false);
        scrollToBottom();
      }
    },
    [BACKEND_URL, interviewSessionId, isLoading, playTts, scrollToBottom]
  );

  const sendMessage = useCallback(async () => {
    const text = input.trim();
    if (!text) return;
    setInput("");
    await sendMessageFromText(text);
  }, [input, sendMessageFromText]);

  const handleStartSpeech = useCallback(() => {
    setSpeechError(null);
    if (isLoading || isRecording) return;
    if (typeof window === "undefined") return;

    const SpeechCtor =
      (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
    if (!SpeechCtor) {
      setHasSpeechSupport(false);
      setSpeechError(
        "Speech recognition is not supported in this browser. You can still type your answers."
      );
      return;
    }

    const recognition = new SpeechCtor();
recognition.lang = "en-US";
recognition.interimResults = true;  // get interim results
recognition.continuous = true;       // don't auto-stop
recognition.maxAlternatives = 1;

let finalTranscript = "";
let silenceTimer: ReturnType<typeof setTimeout> | null = null;

recognition.onresult = (event: any) => {
  let interim = "";

  for (let i = event.resultIndex; i < event.results.length; i++) {
    const result = event.results[i];
    if (result.isFinal) {
      finalTranscript += result[0].transcript + " ";
    } else {
      interim = result[0].transcript;
    }
  }

  // Reset the silence timer every time speech comes in
  if (silenceTimer) clearTimeout(silenceTimer);
  silenceTimer = setTimeout(() => {
    const text = (finalTranscript + interim).trim();
    if (text) {
      void sendMessageFromText(text);
      finalTranscript = "";
    }
    recognition.stop();
  }, 5000); // submit after 1.5s of silence
};

    recognition.onerror = () => {
      setSpeechError(
        "Sorry, I couldn’t hear that. Please try again or type your answer."
      );
    };

    recognition.onend = () => {
      setIsRecording(false);
    };

    setIsRecording(true);
    recognition.start();
  }, [BACKEND_URL, isLoading, isRecording, sendMessageFromText]);

  return (
    <div className="flex flex-col rounded-xl border border-[var(--color-border)] bg-[var(--color-surface-elevated)] overflow-hidden min-h-[520px] flex-1">
      <div className="border-b border-[var(--color-border)] px-4 py-2 flex items-center justify-between">
        <h3 className="text-sm font-medium text-[var(--color-muted)]">
          Chat with AI interviewer
        </h3>
        <div className="flex items-center gap-3">
          <button
            type="button"
            onClick={() => setAudioEnabled((v) => !v)}
            className="text-xs text-[var(--color-muted)] hover:text-[var(--color-primary)]"
            aria-pressed={audioEnabled}
          >
            Audio: {audioEnabled ? "On" : "Off"}
          </button>
          {isSessionEnded && (
            <span className="text-xs text-[var(--color-muted)]">Session ended</span>
          )}
        </div>
      </div>
      <div className="flex-1 overflow-y-auto p-4 space-y-3">
        {messages.map((msg) => (
          <div
            key={msg.id}
            className={`flex ${
              msg.role === "user" ? "justify-end" : "justify-start"
            }`}
          >
            <div
              className={`max-w-[85%] px-4 py-2.5 text-sm ${
                msg.role === "user" ? "chat-user" : "chat-ai"
              }`}
            >
              {msg.content}
            </div>
          </div>
        ))}
        {isLoading && (
          <div className="flex justify-start">
            <div className="chat-ai px-4 py-2.5 text-sm text-[var(--color-muted)]">
              Typing…
            </div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>
      {!isSessionEnded && (
        <>
          {hasSpeechSupport ? (
            <div className="flex items-center justify-between gap-3 border-t border-[var(--color-border)] px-4 py-3">
              <p className="text-xs text-[var(--color-muted)]">
                Press the button, speak your answer, then pause. We’ll turn it into text.
              </p>
              <button
                type="button"
                onClick={handleStartSpeech}
                disabled={isLoading || isRecording}
                className={`rounded-full px-4 py-2 text-sm font-medium text-white ${
                  isRecording
                    ? "bg-red-500 hover:bg-red-600"
                    : "bg-[var(--color-primary)] hover:bg-[var(--color-primary-hover)]"
                } disabled:opacity-50 disabled:cursor-not-allowed`}
              >
                {isRecording ? "Listening…" : "Speak answer"}
              </button>
            </div>
          ) : (
            <form
              className="flex gap-2 border-t border-[var(--color-border)] p-3"
              onSubmit={(e) => {
                e.preventDefault();
                void sendMessage();
              }}
            >
              <input
                type="text"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                placeholder="Type your message…"
                className="flex-1 rounded-lg border border-[var(--color-border)] bg-[var(--color-surface)] px-3 py-2 text-sm outline-none focus:border-[var(--color-primary)] focus:ring-1 focus:ring-[var(--color-primary)]"
                disabled={isLoading}
              />
              <button
                type="submit"
                disabled={!input.trim() || isLoading}
                className="rounded-lg bg-[var(--color-primary)] px-4 py-2 text-sm font-medium text-white hover:bg-[var(--color-primary-hover)] disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Send
              </button>
            </form>
          )}
          {speechError && (
            <p className="px-4 pb-3 text-xs text-red-600">{speechError}</p>
          )}
          {interviewError && (
            <p className="px-4 pb-3 text-xs text-red-600">{interviewError}</p>
          )}
        </>
      )}
    </div>
  );
}

