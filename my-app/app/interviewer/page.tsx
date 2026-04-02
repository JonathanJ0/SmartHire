import Link from "next/link";
import { CandidateTableClient } from "@/components/interviewer/CandidateTableClient";

export default function InterviewerPage() {
  return (
    <div className="mx-auto max-w-6xl px-4 py-8 sm:px-6 lg:px-8">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-[var(--color-primary)]">
            Interviewer dashboard
          </h1>
          <p className="mt-1 text-sm text-[var(--color-muted)]">
            View and evaluate candidate interview sessions.
          </p>
        </div>
        <Link
          href="/interviewer/jobs"
          className="shrink-0 rounded-lg border border-[var(--color-primary)] px-4 py-2 text-sm font-medium text-[var(--color-primary)] hover:bg-[var(--color-primary)] hover:text-white transition"
        >
          📋 Manage Jobs
        </Link>
      </div>

      <div className="mt-8">
        <CandidateTableClient />
      </div>
    </div>
  );
}
