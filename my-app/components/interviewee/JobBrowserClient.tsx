"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { JobCard, type Job } from "@/components/interviewer/JobCard";

export const SELECTED_ROLE_KEY = "umamaj.selectedRole";
export const SELECTED_JOB_ID_KEY = "umamaj.selectedJobId";

export function JobBrowserClient() {
  const BACKEND_URL =
    process.env.NEXT_PUBLIC_BACKEND_URL?.trim() || "http://localhost:8000";

  const router = useRouter();
  const [jobs, setJobs] = useState<Job[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedId, setSelectedId] = useState<string | null>(null);

  useEffect(() => {
    // Restore any previously selected job
    const prevId = localStorage.getItem(SELECTED_JOB_ID_KEY);
    if (prevId) setSelectedId(prevId);

    fetch(`${BACKEND_URL}/api/jobs`)
      .then(async (res) => {
        if (!res.ok) throw new Error(`Failed to load jobs (${res.status})`);
        return res.json() as Promise<{ items: Job[] }>;
      })
      .then((data) => {
        setJobs(data.items);
      })
      .catch((e) => {
        setError(e instanceof Error ? e.message : "Failed to load jobs.");
      })
      .finally(() => setIsLoading(false));
  }, [BACKEND_URL]);

  function handleSelect(job: Job) {
    setSelectedId(job.id);
    localStorage.setItem(SELECTED_ROLE_KEY, job.title);
    localStorage.setItem(SELECTED_JOB_ID_KEY, job.id);
  }

  function handleContinue() {
    router.push("/interviewee/resume");
  }

  return (
    <div className="flex flex-col gap-8">
      {/* Sticky bottom bar when job is selected */}
      {selectedId && (
        <div className="fixed bottom-0 inset-x-0 z-50 border-t border-[var(--color-border)] bg-[var(--color-surface-elevated)]/90 backdrop-blur px-4 py-4 flex items-center justify-between gap-4">
          <p className="text-sm text-[var(--color-muted)]">
            Role selected:{" "}
            <span className="font-semibold text-[var(--color-primary)]">
              {jobs.find((j) => j.id === selectedId)?.title ?? ""}
            </span>
          </p>
          <button
            id="continue-to-resume"
            type="button"
            onClick={handleContinue}
            className="rounded-lg bg-[var(--color-primary)] px-5 py-2.5 text-sm font-medium text-white hover:bg-[var(--color-primary-hover)] transition"
          >
            Continue → Upload Resume
          </button>
        </div>
      )}

      {isLoading ? (
        <div className="py-16 text-center text-sm text-[var(--color-muted)]">
          Loading open positions…
        </div>
      ) : error ? (
        <div className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-600">
          {error}
          <p className="mt-1 text-xs">Make sure the backend is running at {BACKEND_URL}.</p>
        </div>
      ) : jobs.length === 0 ? (
        <div className="rounded-2xl border border-dashed border-[var(--color-border)] py-20 text-center">
          <p className="text-4xl mb-3">🔍</p>
          <p className="font-medium text-[var(--color-primary)]">No open positions yet</p>
          <p className="mt-1 text-sm text-[var(--color-muted)]">
            Check back later or contact the hiring team.
          </p>
        </div>
      ) : (
        <div className={`grid gap-5 sm:grid-cols-2 xl:grid-cols-3 ${selectedId ? "pb-24" : ""}`}>
          {jobs.map((job) => (
            <JobCard
              key={job.id}
              job={job}
              onSelect={handleSelect}
              selected={job.id === selectedId}
            />
          ))}
        </div>
      )}
    </div>
  );
}
