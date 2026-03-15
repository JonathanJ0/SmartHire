import Link from "next/link";
import { ResumeUploader } from "@/components/interviewee/ResumeUploader";

export default function ResumePage() {
  return (
    <div className="mx-auto max-w-3xl px-4 py-8 sm:px-6 lg:px-8">
      <div className="flex items-center justify-between gap-4">
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
          className="rounded-lg border border-[var(--color-border)] px-3 py-1.5 text-sm hover:bg-black/5"
        >
          Start Interview
        </Link>
      </div>

      <div className="mt-6">
        <ResumeUploader />
      </div>
    </div>
  );
}

