"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { ResumeUploader } from "@/components/interviewee/ResumeUploader";
import { SELECTED_ROLE_KEY } from "@/components/interviewee/JobBrowserClient";

export default function ResumePage() {
  const [selectedRole, setSelectedRole] = useState<string | null>(null);

  useEffect(() => {
    setSelectedRole(localStorage.getItem(SELECTED_ROLE_KEY));
  }, []);

  return (
    <div className="mx-auto max-w-3xl px-4 py-8 sm:px-6 lg:px-8">
      <div className="flex items-center gap-2 mb-1">
        <Link
          href="/interviewee/jobs"
          className="text-sm text-[var(--color-muted)] hover:text-[var(--color-primary)] transition"
        >
          ← Browse Jobs
        </Link>
      </div>

      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-[var(--color-primary)]">
            Resume
          </h1>
          <p className="mt-1 text-sm text-[var(--color-muted)]">
            Add your resume before starting the interview.
          </p>
        </div>
        <Link
          href="/interviewee"
          className="shrink-0 rounded-lg border border-[var(--color-border)] px-3 py-1.5 text-sm hover:bg-black/5 transition"
        >
          Start Interview
        </Link>
      </div>

      {/* Selected role badge */}
      {selectedRole && (
        <div className="mt-4 flex items-center gap-2 rounded-xl border border-[var(--color-accent)]/40 bg-[oklch(0.96_0.04_160)] px-4 py-2.5">
          <span className="text-base">💼</span>
          <div className="flex-1 min-w-0">
            <p className="text-sm font-medium text-[oklch(0.3_0.12_160)]">
              Applying for:{" "}
              <span className="font-semibold">{selectedRole}</span>
            </p>
            <p className="text-xs text-[oklch(0.45_0.08_160)] mt-0.5">
              Your AI interview will be tailored specifically for this role.
            </p>
          </div>
          <Link
            href="/interviewee/jobs"
            className="shrink-0 text-xs text-[var(--color-muted)] hover:text-[var(--color-primary)] underline underline-offset-2 transition"
          >
            Change
          </Link>
        </div>
      )}

      {!selectedRole && (
        <div className="mt-4 flex items-center gap-2 rounded-xl border border-yellow-200 bg-yellow-50 px-4 py-2.5">
          <span className="text-base">⚠️</span>
          <p className="text-sm text-yellow-700">
            No role selected.{" "}
            <Link href="/interviewee/jobs" className="font-medium underline underline-offset-2">
              Browse jobs
            </Link>{" "}
            to pick a role first.
          </p>
        </div>
      )}

      <div className="mt-6">
        <ResumeUploader />
      </div>
    </div>
  );
}
