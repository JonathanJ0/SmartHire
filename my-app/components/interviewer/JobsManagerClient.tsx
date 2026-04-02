"use client";

import { useEffect, useState } from "react";
import { JobCard, type Job } from "@/components/interviewer/JobCard";
import { JobPostingForm } from "@/components/interviewer/JobPostingForm";

export function JobsManagerClient() {
  const BACKEND_URL =
    process.env.NEXT_PUBLIC_BACKEND_URL?.trim() || "http://localhost:8000";

  const [jobs, setJobs] = useState<Job[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showForm, setShowForm] = useState(false);

  useEffect(() => {
    fetchJobs();
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function fetchJobs() {
    setIsLoading(true);
    setError(null);
    try {
      const res = await fetch(`${BACKEND_URL}/api/jobs`);
      if (!res.ok) throw new Error(`Failed to load jobs (${res.status})`);
      const data = (await res.json()) as { items: Job[] };
      setJobs(data.items);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load jobs.");
    } finally {
      setIsLoading(false);
    }
  }

  function handleCreated(job: Job) {
    setJobs((prev) => [job, ...prev]);
    setShowForm(false);
  }

  async function handleDelete(job: Job) {
    if (!confirm(`Delete "${job.title}"? This cannot be undone.`)) return;
    try {
      const res = await fetch(`${BACKEND_URL}/api/jobs/${job.id}`, {
        method: "DELETE",
      });
      if (!res.ok) throw new Error(`Delete failed (${res.status})`);
      setJobs((prev) => prev.filter((j) => j.id !== job.id));
    } catch (e) {
      alert(e instanceof Error ? e.message : "Delete failed.");
    }
  }

  return (
    <div className="flex flex-col gap-8">
      {/* Top bar */}
      <div className="flex items-center justify-between gap-4">
        <div>
          <h2 className="text-xl font-semibold">Open positions</h2>
          <p className="mt-0.5 text-sm text-[var(--color-muted)]">
            {jobs.length} job{jobs.length !== 1 ? "s" : ""} posted
          </p>
        </div>
        <button
          id="toggle-job-form"
          type="button"
          onClick={() => setShowForm((v) => !v)}
          className="rounded-lg bg-[var(--color-primary)] px-4 py-2 text-sm font-medium text-white hover:bg-[var(--color-primary-hover)] transition"
        >
          {showForm ? "✕ Cancel" : "+ Post new job"}
        </button>
      </div>

      {/* Post form */}
      {showForm && (
        <JobPostingForm onCreated={handleCreated} />
      )}

      {/* Jobs list */}
      {isLoading ? (
        <div className="text-sm text-[var(--color-muted)] py-8 text-center">
          Loading job postings…
        </div>
      ) : error ? (
        <div className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-600">
          {error}
        </div>
      ) : jobs.length === 0 ? (
        <div className="rounded-2xl border border-dashed border-[var(--color-border)] py-16 text-center">
          <p className="text-4xl mb-3">📋</p>
          <p className="font-medium text-[var(--color-primary)]">No job postings yet</p>
          <p className="mt-1 text-sm text-[var(--color-muted)]">
            Click &ldquo;Post new job&rdquo; above to create the first one.
          </p>
        </div>
      ) : (
        <div className="grid gap-5 sm:grid-cols-2 xl:grid-cols-3">
          {jobs.map((job) => (
            <JobCard key={job.id} job={job} onDelete={handleDelete} />
          ))}
        </div>
      )}
    </div>
  );
}
