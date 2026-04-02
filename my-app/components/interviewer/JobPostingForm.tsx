"use client";

import { useState } from "react";
import type { Job } from "./JobCard";

type Props = {
  onCreated: (job: Job) => void;
};

const JOB_TYPES = ["Full-time", "Part-time", "Contract", "Internship"];

export function JobPostingForm({ onCreated }: Props) {
  const BACKEND_URL =
    process.env.NEXT_PUBLIC_BACKEND_URL?.trim() || "http://localhost:8000";

  const [title, setTitle] = useState("");
  const [department, setDepartment] = useState("");
  const [location, setLocation] = useState("Remote");
  const [jobType, setJobType] = useState("Full-time");
  const [description, setDescription] = useState("");
  const [requirements, setRequirements] = useState<string[]>([""]);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function addRequirement() {
    setRequirements((prev) => [...prev, ""]);
  }

  function updateRequirement(index: number, value: string) {
    setRequirements((prev) => prev.map((r, i) => (i === index ? value : r)));
  }

  function removeRequirement(index: number) {
    setRequirements((prev) => prev.filter((_, i) => i !== index));
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!title.trim()) {
      setError("Job title is required.");
      return;
    }
    setError(null);
    setIsSubmitting(true);
    try {
      const res = await fetch(`${BACKEND_URL}/api/jobs`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          title: title.trim(),
          department: department.trim(),
          location: location.trim(),
          job_type: jobType,
          description: description.trim(),
          requirements: requirements.filter((r) => r.trim()),
        }),
      });
      if (!res.ok) {
        const body = await res.json().catch(() => null);
        throw new Error(
          body?.detail ?? `Failed to create job (${res.status})`
        );
      }
      const job = (await res.json()) as Job;
      onCreated(job);
      // Reset
      setTitle("");
      setDepartment("");
      setLocation("Remote");
      setJobType("Full-time");
      setDescription("");
      setRequirements([""]);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to post job.");
    } finally {
      setIsSubmitting(false);
    }
  }

  const inputClass =
    "w-full rounded-lg border border-[var(--color-border)] bg-[var(--color-surface)] px-3 py-2 text-sm outline-none focus:border-[var(--color-primary)] focus:ring-2 focus:ring-[var(--color-primary)]/20 transition";

  return (
    <div className="rounded-2xl border border-[var(--color-border)] bg-[var(--color-surface-elevated)] overflow-hidden">
      <div className="border-b border-[var(--color-border)] px-6 py-4">
        <h2 className="text-base font-semibold text-[var(--color-primary)]">
          Post a new job opening
        </h2>
        <p className="mt-0.5 text-sm text-[var(--color-muted)]">
          Fill in the details below. Interviewees will see and apply for this role.
        </p>
      </div>

      <form onSubmit={(e) => void handleSubmit(e)} className="p-6 flex flex-col gap-5">
        {/* Title & Department */}
        <div className="grid gap-4 sm:grid-cols-2">
          <div>
            <label htmlFor="job-title" className="block text-sm font-medium mb-1.5">
              Job Title <span className="text-red-500">*</span>
            </label>
            <input
              id="job-title"
              type="text"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="e.g. Software Engineer"
              className={inputClass}
              required
            />
          </div>
          <div>
            <label htmlFor="job-department" className="block text-sm font-medium mb-1.5">
              Department
            </label>
            <input
              id="job-department"
              type="text"
              value={department}
              onChange={(e) => setDepartment(e.target.value)}
              placeholder="e.g. Engineering"
              className={inputClass}
            />
          </div>
        </div>

        {/* Location & Type */}
        <div className="grid gap-4 sm:grid-cols-2">
          <div>
            <label htmlFor="job-location" className="block text-sm font-medium mb-1.5">
              Location
            </label>
            <input
              id="job-location"
              type="text"
              value={location}
              onChange={(e) => setLocation(e.target.value)}
              placeholder="e.g. Remote, New York"
              className={inputClass}
            />
          </div>
          <div>
            <label htmlFor="job-type" className="block text-sm font-medium mb-1.5">
              Job Type
            </label>
            <select
              id="job-type"
              value={jobType}
              onChange={(e) => setJobType(e.target.value)}
              className={inputClass}
            >
              {JOB_TYPES.map((t) => (
                <option key={t} value={t}>
                  {t}
                </option>
              ))}
            </select>
          </div>
        </div>

        {/* Description */}
        <div>
          <label htmlFor="job-description" className="block text-sm font-medium mb-1.5">
            Description
          </label>
          <textarea
            id="job-description"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="Describe the role, team, and what the candidate will be working on…"
            rows={4}
            className={`${inputClass} resize-none`}
          />
        </div>

        {/* Requirements */}
        <div>
          <p className="text-sm font-medium mb-2">Requirements</p>
          <div className="flex flex-col gap-2">
            {requirements.map((req, i) => (
              <div key={i} className="flex gap-2 items-center">
                <input
                  type="text"
                  value={req}
                  onChange={(e) => updateRequirement(i, e.target.value)}
                  placeholder={`Requirement ${i + 1}`}
                  className={`${inputClass} flex-1`}
                  id={`req-${i}`}
                />
                {requirements.length > 1 && (
                  <button
                    type="button"
                    onClick={() => removeRequirement(i)}
                    className="shrink-0 rounded-lg border border-[var(--color-border)] px-2.5 py-2 text-sm text-[var(--color-muted)] hover:bg-red-50 hover:border-red-200 hover:text-red-500 transition"
                  >
                    ✕
                  </button>
                )}
              </div>
            ))}
            <button
              type="button"
              onClick={addRequirement}
              className="self-start text-sm text-[var(--color-primary)] hover:underline"
            >
              + Add requirement
            </button>
          </div>
        </div>

        {error && (
          <p className="text-sm text-red-600 rounded-lg bg-red-50 border border-red-200 px-3 py-2">
            {error}
          </p>
        )}

        <div className="flex justify-end">
          <button
            id="submit-job-posting"
            type="submit"
            disabled={isSubmitting}
            className="rounded-lg bg-[var(--color-primary)] px-6 py-2.5 text-sm font-medium text-white hover:bg-[var(--color-primary-hover)] disabled:opacity-50 disabled:cursor-not-allowed transition"
          >
            {isSubmitting ? "Posting…" : "Post job opening"}
          </button>
        </div>
      </form>
    </div>
  );
}
