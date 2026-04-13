 "use client";

import { useRouter } from "next/navigation";
import { useCallback, useEffect, useMemo, useState } from "react";
import { CODING_SESSION_KEY } from "./IntervieweeSession";

export function CodingExercise() {
  const router = useRouter();
  const [language, setLanguage] = useState("Python");
  const [code, setCode] = useState("");
  const [explanation, setExplanation] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isRecording, setIsRecording] = useState(false);
  const [speechError, setSpeechError] = useState<string | null>(null);
  const [question, setQuestion] = useState<{
    title: string;
    description: string;
    examples: string[];
    constraints: string[];
  } | null>(null);
  const [questionError, setQuestionError] = useState<string | null>(null);
  const [isLoadingQuestion, setIsLoadingQuestion] = useState(true);

  const BACKEND_URL = useMemo(
    () => process.env.NEXT_PUBLIC_BACKEND_URL?.trim() || "http://localhost:8000",
    []
  );

  useEffect(() => {
    if (typeof window === "undefined") return;
    const sessionId =
      localStorage.getItem(CODING_SESSION_KEY) ||
      localStorage.getItem("umamaj.interviewSessionId");
    if (!sessionId) {
      setQuestionError("Missing interview session. Please start an interview first.");
      setIsLoadingQuestion(false);
      return;
    }

    setIsLoadingQuestion(true);
    setQuestionError(null);

    fetch(`${BACKEND_URL}/api/coding/question`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ interview_session_id: sessionId }),
    })
      .then(async (res) => {
        if (!res.ok) {
          const body = await res.json().catch(() => null);
          const detail =
            body && typeof body === "object" && "detail" in body
              ? String((body as any).detail)
              : `Failed to load coding question (${res.status})`;
          throw new Error(detail);
        }
        return res.json() as Promise<{
          title: string;
          description: string;
          examples: string[];
          constraints: string[];
        }>;
      })
      .then((q) => {
        setQuestion(q);
      })
      .catch((e) => {
        setQuestionError(e instanceof Error ? e.message : "Failed to load coding question.");
      })
      .finally(() => {
        setIsLoadingQuestion(false);
      });
  }, [BACKEND_URL]);

  const handleStartExplanationSpeech = useCallback(() => {
    setSpeechError(null);
    if (isRecording) return;
    if (typeof window === "undefined") return;

    const SpeechCtor =
      (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
    if (!SpeechCtor) {
      setSpeechError(
        "Speech recognition is not supported in this browser."
      );
      return;
    }

    const recognition = new SpeechCtor();
    recognition.lang = "en-US";
    recognition.interimResults = true;
    recognition.continuous = true;
    recognition.maxAlternatives = 1;

    let finalTranscript = explanation ? explanation + " " : "";
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

      if (silenceTimer) clearTimeout(silenceTimer);
      silenceTimer = setTimeout(() => {
        const text = (finalTranscript + interim).trim();
        if (text) {
          setExplanation(text);
        }
        recognition.stop();
      }, 5000);
    };

    recognition.onerror = () => {
      setSpeechError(
        "Sorry, I couldn’t hear that. Please try again or type your explanation."
      );
    };

    recognition.onend = () => {
      setIsRecording(false);
    };

    setIsRecording(true);
    recognition.start();
  }, [explanation, isRecording]);

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    if (typeof window === "undefined") return;

    const sessionId =
      localStorage.getItem(CODING_SESSION_KEY) ||
      localStorage.getItem("umamaj.interviewSessionId");
    if (!sessionId) {
      setSpeechError("Missing interview session. Please start an interview first.");
      return;
    }

    setIsSubmitting(true);

    try {
      await fetch(`${BACKEND_URL}/api/coding/submit`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          interview_session_id: sessionId,
          language,
          code,
          explanation,
          question,
        }),
      });

      router.push("/interviewee/feedback");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="mt-8 space-y-6">
      <div className="rounded-xl border border-[var(--color-border)] bg-[var(--color-surface-elevated)] p-4">
        <h2 className="text-sm font-medium text-[var(--color-muted)]">
          Coding question
        </h2>
        {isLoadingQuestion ? (
          <p className="mt-2 text-xs text-[var(--color-muted)]">
            Generating a question based on your interview…
          </p>
        ) : questionError ? (
          <p className="mt-2 text-xs text-red-600">{questionError}</p>
        ) : question ? (
          <div className="mt-2 space-y-2 text-sm">
            <h3 className="font-semibold text-[var(--color-primary)]">
              {question.title}
            </h3>
            <p className="text-[var(--color-muted)] whitespace-pre-line">
              {question.description}
            </p>
            {question.examples.length > 0 && (
              <div className="mt-2">
                <p className="text-xs font-semibold text-[var(--color-muted)]">
                  Examples
                </p>
                <ul className="mt-1 list-inside list-disc text-xs text-[var(--color-muted)] space-y-0.5">
                  {question.examples.map((ex, i) => (
                    <li key={i}>{ex}</li>
                  ))}
                </ul>
              </div>
            )}
            {question.constraints.length > 0 && (
              <div className="mt-2">
                <p className="text-xs font-semibold text-[var(--color-muted)]">
                  Constraints
                </p>
                <ul className="mt-1 list-inside list-disc text-xs text-[var(--color-muted)] space-y-0.5">
                  {question.constraints.map((c, i) => (
                    <li key={i}>{c}</li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        ) : (
          <p className="mt-2 text-xs text-[var(--color-muted)]">
            No question available.
          </p>
        )}
      </div>

      <div className="flex flex-col gap-6 lg:flex-row lg:items-start">
        <div className="flex-1 space-y-3">
          <div className="flex items-center justify-between gap-3">
            <h2 className="text-sm font-medium text-[var(--color-muted)]">
              Coding panel
            </h2>
            <select
              value={language}
              onChange={(e) => setLanguage(e.target.value)}
              className="rounded-md border border-[var(--color-border)] bg-[var(--color-surface-elevated)] px-2 py-1 text-xs outline-none focus:border-[var(--color-primary)] focus:ring-1 focus:ring-[var(--color-primary)]"
            >
              <option>Python</option>
              <option>JavaScript</option>
              <option>TypeScript</option>
              <option>Java</option>
              <option>C++</option>
            </select>
          </div>
          <div className="rounded-xl border border-[var(--color-border)] bg-[var(--color-surface-elevated)] p-3">
            <textarea
              value={code}
              onChange={(e) => setCode(e.target.value)}
              placeholder="Write your solution here..."
              className="h-64 w-full resize-y rounded-md border border-[var(--color-border)] bg-[var(--color-surface)] px-3 py-2 text-sm font-mono outline-none focus:border-[var(--color-primary)] focus:ring-1 focus:ring-[var(--color-primary)]"
            />
          </div>
        </div>

        <div className="flex-1 space-y-3">
          <div className="flex items-center justify-between gap-3">
            <h2 className="text-sm font-medium text-[var(--color-muted)]">
              Explanation panel
            </h2>
            <button
              type="button"
              onClick={handleStartExplanationSpeech}
              disabled={isRecording}
              className="rounded-full px-3 py-1.5 text-xs font-medium text-white bg-[var(--color-primary)] hover:bg-[var(--color-primary-hover)] disabled:opacity-60 disabled:cursor-not-allowed"
            >
              {isRecording ? "Listening…" : "Speak explanation"}
            </button>
          </div>
          <div className="rounded-xl border border-[var(--color-border)] bg-[var(--color-surface-elevated)] p-3 space-y-2">
            <textarea
              value={explanation}
              readOnly
              placeholder="Your spoken explanation will appear here..."
              className="h-56 w-full resize-none rounded-md border border-[var(--color-border)] bg-[var(--color-surface)] px-3 py-2 text-sm outline-none"
            />
            {speechError && (
              <p className="text-xs text-red-600">{speechError}</p>
            )}
          </div>
        </div>
      </div>

      <div className="flex items-center justify-between gap-4">
        <p className="text-xs text-[var(--color-muted)]">
          When you&apos;re satisfied with your solution and explanation, submit to continue.
        </p>
        <button
          type="submit"
          disabled={isSubmitting || (!code.trim() && !explanation.trim())}
          className="rounded-lg bg-[var(--color-primary)] px-4 py-2 text-sm font-medium text-white hover:bg-[var(--color-primary-hover)] disabled:cursor-not-allowed disabled:opacity-60"
        >
          {isSubmitting ? "Submitting..." : "Submit solution"}
        </button>
      </div>
    </form>
  );
}

