import Link from "next/link";

export default function HomePage() {
  return (
    <div className="mx-auto max-w-4xl px-4 py-16 sm:px-6 lg:px-8">
      <div className="text-center">
        <h1 className="text-4xl font-bold tracking-tight text-[var(--color-primary)] sm:text-5xl">
          Interview Evaluation
        </h1>
        <p className="mt-4 text-lg text-[var(--color-muted)]">
          Practice with an AI interviewer, or evaluate candidate performance.
        </p>
      </div>

      <div className="mt-16 grid gap-8 sm:grid-cols-2">
        <Link
          href="/interviewee/resume"
          className="group relative overflow-hidden rounded-2xl border border-[var(--color-border)] bg-[var(--color-surface-elevated)] p-8 shadow-sm transition hover:border-[var(--color-primary)] hover:shadow-md"
        >
          <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-[var(--color-primary)]/10 text-[var(--color-primary)]">
            <span className="text-2xl" aria-hidden>🎥</span>
          </div>
          <h2 className="mt-4 text-xl font-semibold">Interviewee</h2>
          <p className="mt-2 text-sm text-[var(--color-muted)]">
            Start a session: turn on your camera and chat with the AI interviewer.
          </p>
          <span className="mt-4 inline-block text-sm font-medium text-[var(--color-primary)] group-hover:underline">
            Go to session →
          </span>
        </Link>

        <Link
          href="/interviewer"
          className="group relative overflow-hidden rounded-2xl border border-[var(--color-border)] bg-[var(--color-surface-elevated)] p-8 shadow-sm transition hover:border-[var(--color-accent)] hover:shadow-md"
        >
          <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-[var(--color-accent)]/15 text-[var(--color-accent)]">
            <span className="text-2xl" aria-hidden>📊</span>
          </div>
          <h2 className="mt-4 text-xl font-semibold">Interviewer</h2>
          <p className="mt-2 text-sm text-[var(--color-muted)]">
            View performance of candidates and review session details.
          </p>
          <span className="mt-4 inline-block text-sm font-medium text-[var(--color-accent)] group-hover:underline">
            Open dashboard →
          </span>
        </Link>
      </div>
    </div>
  );
}
