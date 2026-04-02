import { JobsManagerClient } from "@/components/interviewer/JobsManagerClient";
import Link from "next/link";

export const metadata = {
  title: "Manage Jobs – SmartHire",
  description: "Post and manage open job positions for candidates to apply to.",
};

export default function InterviewerJobsPage() {
  return (
    <div className="mx-auto max-w-6xl px-4 py-8 sm:px-6 lg:px-8">
      <div className="flex items-center gap-2 mb-1">
        <Link
          href="/interviewer"
          className="text-sm text-[var(--color-muted)] hover:text-[var(--color-primary)] transition"
        >
          ← Dashboard
        </Link>
      </div>
      <h1 className="text-2xl font-bold text-[var(--color-primary)]">
        Manage job openings
      </h1>
      <p className="mt-1 text-sm text-[var(--color-muted)]">
        Post roles for candidates to browse and apply for. Each role becomes available to interviewees on their job board.
      </p>

      <div className="mt-8">
        <JobsManagerClient />
      </div>
    </div>
  );
}
