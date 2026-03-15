"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

type Bundle = {
  id: string;
  role: string;
  resumeId: string;
  resume: any;
  transcriptText: string;
  evaluation: any | null;
  speechStats: any | null;
  updatedAt: number;
};

function pctFromOverallScore(score: number | null | undefined) {
  if (score === null || score === undefined || Number.isNaN(score)) return null;
  return Math.round((Number(score) / 10) * 100);
}

export function SessionDetailClient({ sessionId }: { sessionId: string }) {
  const [data, setData] = useState<Bundle | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  const BACKEND_URL = useMemo(
    () => process.env.NEXT_PUBLIC_BACKEND_URL?.trim() || "http://localhost:8000",
    []
  );

  useEffect(() => {
    setIsLoading(true);
    fetch(`${BACKEND_URL}/api/dashboard/interviews/${sessionId}`)
      .then(async (res) => {
        if (!res.ok) throw new Error(`Backend returned ${res.status}`);
        return res.json() as Promise<Bundle>;
      })
      .then((bundle) => {
        setData(bundle);
        setError(null);
      })
      .catch((e) => setError(e instanceof Error ? e.message : "Failed to load"))
      .finally(() => setIsLoading(false));
  }, [BACKEND_URL, sessionId]);

  const candidateName =
    data?.resume?.contact?.name || data?.resume?.contact?.email || "Candidate";
  const overallPct = pctFromOverallScore(data?.evaluation?.overall_score);

  return (
    <div className="mx-auto max-w-4xl px-4 py-8 sm:px-6 lg:px-8">
      <Link
        href="/interviewer"
        className="text-sm text-[var(--color-primary)] hover:underline"
      >
        ← Back to dashboard
      </Link>

      {error && (
        <div className="mt-6 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          Couldn’t load session. {error}
        </div>
      )}

      {isLoading || !data ? (
        <div className="mt-6 text-sm text-[var(--color-muted)]">Loading…</div>
      ) : (
        <>
          <div className="mt-6">
            <h1 className="text-2xl font-bold text-[var(--color-primary)]">
              {candidateName}
            </h1>
            <p className="mt-1 text-[var(--color-muted)]">
              {data.role} · Updated {new Date(data.updatedAt * 1000).toLocaleString()}
            </p>
          </div>

          <div className="mt-8 grid gap-6 sm:grid-cols-2">
            <div className="rounded-xl border border-[var(--color-border)] bg-[var(--color-surface-elevated)] p-5">
              <h2 className="text-sm font-medium text-[var(--color-muted)]">
                Overall score
              </h2>
              <p className="mt-1 text-3xl font-bold text-[var(--color-accent)]">
                {overallPct === null ? "—" : `${overallPct}%`}
              </p>
              {data.evaluation?.recommendation && (
                <p className="mt-2 text-sm text-[var(--color-muted)]">
                  {data.evaluation.recommendation}
                </p>
              )}
            </div>
            <div className="rounded-xl border border-[var(--color-border)] bg-[var(--color-surface-elevated)] p-5">
              <h2 className="text-sm font-medium text-[var(--color-muted)]">
                Speech summary
              </h2>
              {data.speechStats?.aggregate ? (
                <ul className="mt-2 space-y-1.5 text-sm">
                  <li className="flex justify-between">
                    <span className="text-[var(--color-muted)]">Utterances</span>
                    <span className="font-medium">
                      {data.speechStats.aggregate.utterance_count ?? "—"}
                    </span>
                  </li>
                  <li className="flex justify-between">
                    <span className="text-[var(--color-muted)]">Words</span>
                    <span className="font-medium">
                      {data.speechStats.aggregate.total_words ?? "—"}
                    </span>
                  </li>
                  <li className="flex justify-between">
                    <span className="text-[var(--color-muted)]">Fillers</span>
                    <span className="font-medium">
                      {data.speechStats.aggregate.total_fillers ?? "—"}
                    </span>
                  </li>
                </ul>
              ) : (
                <p className="mt-2 text-sm text-[var(--color-muted)]">—</p>
              )}
            </div>
          </div>

          {data.evaluation?.summary && (
            <div className="mt-6 rounded-xl border border-[var(--color-border)] bg-[var(--color-surface-elevated)] p-5">
              <h2 className="text-sm font-medium text-[var(--color-muted)]">
                Evaluation summary
              </h2>
              <p className="mt-2 text-sm">{data.evaluation.summary}</p>
            </div>
          )}

          <div className="mt-6 rounded-xl border border-[var(--color-border)] bg-[var(--color-surface-elevated)] p-5">
            <h2 className="text-sm font-medium text-[var(--color-muted)]">
              Transcript
            </h2>
            <pre className="mt-3 max-h-[420px] overflow-y-auto whitespace-pre-wrap text-sm text-[var(--color-muted)]">
              {data.transcriptText}
            </pre>
          </div>
        </>
      )}
    </div>
  );
}

