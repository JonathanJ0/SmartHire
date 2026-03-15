import Link from "next/link";
import { IntervieweeFeedback } from "@/components/interviewee/IntervieweeFeedback";

export default function IntervieweeFeedbackPage() {
  return (
    <div className="mx-auto max-w-4xl px-4 py-8 sm:px-6 lg:px-8">
      <div className="flex items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-[var(--color-primary)]">
            Interview feedback
          </h1>
          <p className="mt-1 text-sm text-[var(--color-muted)]">
            Review your transcript and see areas you can improve.
          </p>
        </div>
        <Link
          href="/interviewee"
          className="rounded-lg border border-[var(--color-border)] px-3 py-1.5 text-sm hover:bg-black/5"
        >
          Back to interview
        </Link>
      </div>

      <IntervieweeFeedback />
    </div>
  );
}

