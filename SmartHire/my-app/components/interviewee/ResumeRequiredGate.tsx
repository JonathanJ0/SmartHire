"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { RESUME_ID_KEY } from "./ResumeUploader";

type Props = {
  children: React.ReactNode;
};

export function ResumeRequiredGate({ children }: Props) {
  const router = useRouter();
  const [hasResume, setHasResume] = useState<boolean | null>(null);

  useEffect(() => {
    const BACKEND_URL =
      process.env.NEXT_PUBLIC_BACKEND_URL?.trim() || "http://localhost:8000";

    const resumeId = localStorage.getItem(RESUME_ID_KEY);
    if (!resumeId) {
      setHasResume(false);
      router.replace("/interviewee/resume");
      return;
    }

    // Validate the resume exists on the backend (so upload is truly mandatory).
    fetch(`${BACKEND_URL}/api/resume/${resumeId}`)
      .then((res) => {
        if (!res.ok) throw new Error("not found");
        setHasResume(true);
      })
      .catch(() => {
        localStorage.removeItem(RESUME_ID_KEY);
        setHasResume(false);
        router.replace("/interviewee/resume");
      });
  }, [router]);

  if (hasResume === null) {
    return (
      <div className="mt-8 rounded-2xl border border-[var(--color-border)] bg-[var(--color-surface-elevated)] p-5 text-sm text-[var(--color-muted)]">
        Checking for resume…
      </div>
    );
  }

  if (!hasResume) {
    return (
      <div className="mt-8 rounded-2xl border border-[var(--color-border)] bg-[var(--color-surface-elevated)] p-5">
        <h2 className="text-base font-semibold text-[var(--color-primary)]">
          Resume required
        </h2>
        <p className="mt-2 text-sm text-[var(--color-muted)]">
          Please upload your resume before starting the interview.
        </p>
        <div className="mt-4 flex gap-3">
          <Link
            href="/interviewee/resume"
            className="rounded-lg bg-[var(--color-primary)] px-4 py-2 text-sm font-medium text-white hover:bg-[var(--color-primary-hover)]"
          >
            Upload resume
          </Link>
          <Link
            href="/"
            className="rounded-lg border border-[var(--color-border)] px-4 py-2 text-sm hover:bg-black/5"
          >
            Back home
          </Link>
        </div>
      </div>
    );
  }

  return <>{children}</>;
}

