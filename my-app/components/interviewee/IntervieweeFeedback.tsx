"use client";

import { useEffect, useState } from "react";
import type { ChatMessage } from "./ChatBox";
import { CHAT_STORAGE_KEY } from "./ChatBox";
import { FeedbackSection } from "./FeedbackSection";

export function IntervieweeFeedback() {
  const [messages, setMessages] = useState<ChatMessage[] | null>(null);

  useEffect(() => {
    if (typeof window === "undefined") return;
    const raw = localStorage.getItem(CHAT_STORAGE_KEY);
    if (!raw) {
      setMessages([]);
      return;
    }
    try {
      const parsed = JSON.parse(raw) as Array<
        Omit<ChatMessage, "timestamp"> & { timestamp: string }
      >;
      setMessages(
        parsed.map((m) => ({
          ...m,
          timestamp: new Date(m.timestamp),
        }))
      );
    } catch {
      setMessages([]);
    }
  }, []);

  if (messages === null) {
    return (
      <div className="mt-6 text-sm text-[var(--color-muted)]">
        Loading your interview transcript…
      </div>
    );
  }

  return (
    <div className="mt-6 space-y-6">
      <div className="rounded-2xl border border-[var(--color-border)] bg-[var(--color-surface-elevated)] p-5">
        <h2 className="text-sm font-medium text-[var(--color-muted)]">
          Transcript
        </h2>
        {messages.length === 0 ? (
          <p className="mt-2 text-sm text-[var(--color-muted)]">
            No transcript found for this session.
          </p>
        ) : (
          <ul className="mt-3 max-h-[360px] space-y-3 overflow-y-auto pr-1 text-sm">
            {messages.map((msg) => (
              <li
                key={msg.id}
                className={`flex ${
                  msg.role === "user" ? "justify-end" : "justify-start"
                }`}
              >
                <div
                  className={`max-w-[80%] rounded-xl px-3 py-2 ${
                    msg.role === "user"
                      ? "bg-[var(--color-primary)]/10 text-[var(--color-primary)]"
                      : "bg-[var(--color-surface)] border border-[var(--color-border)]"
                  }`}
                >
                  <p>{msg.content}</p>
                  <p className="mt-1 text-[10px] text-[var(--color-muted)]">
                    {msg.role === "user" ? "You" : "AI interviewer"}
                  </p>
                </div>
              </li>
            ))}
          </ul>
        )}
      </div>

      <FeedbackSection />
    </div>
  );
}

