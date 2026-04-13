import { CodingExercise } from "@/components/interviewee/CodingExercise";
import Link from "next/link";

export default function IntervieweeCodingPage() {
  return (
    <div className="mx-auto max-w-6xl px-4 py-8 sm:px-6 lg:px-8">
      <div className="flex items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-[var(--color-primary)]">
            Coding exercise
          </h1>
          <p className="mt-1 text-sm text-[var(--color-muted)]">
            Based on your interview, complete a short coding task and explain your approach.
          </p>
        </div>
        <Link
          href="/interviewee/feedback"
          className="rounded-lg border border-[var(--color-border)] px-3 py-1.5 text-sm hover:bg-black/5"
        >
          Skip to feedback
        </Link>
      </div>

      <CodingExercise />
    </div>
  );
}

