import { CandidateTableClient } from "@/components/interviewer/CandidateTableClient";

export default function InterviewerPage() {
  return (
    <div className="mx-auto max-w-6xl px-4 py-8 sm:px-6 lg:px-8">
      <h1 className="text-2xl font-bold text-[var(--color-primary)]">
        Interviewer dashboard
      </h1>
      <p className="mt-1 text-sm text-[var(--color-muted)]">
        View and evaluate candidate interview sessions.
      </p>

      <div className="mt-8">
        <CandidateTableClient />
      </div>
    </div>
  );
}
