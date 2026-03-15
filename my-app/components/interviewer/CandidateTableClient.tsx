"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

type DashboardRow = {
  id: string;
  candidateName: string;
  role: string;
  date: number; // epoch seconds
  overallScore: number | null;
  recommendation?: string | null;
  hasEvaluation: boolean;
  hasSpeechStats: boolean;
};

function ScoreBadge({ score }: { score: number | null }) {
  if (score === null || Number.isNaN(score)) {
    return <span className="text-[var(--color-muted)]">—</span>;
  }
  const pct = Math.round((score / 10) * 100);
  const color =
    pct >= 80
      ? "text-[var(--color-accent)] bg-[var(--color-accent)]/15"
      : pct >= 60
        ? "text-amber-600 bg-amber-500/15"
        : "text-red-600 bg-red-500/15";
  return (
    <span
      className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-sm font-medium ${color}`}
    >
      {pct}%
    </span>
  );
}

export function CandidateTableClient() {
  const [items, setItems] = useState<DashboardRow[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  const BACKEND_URL = useMemo(
    () => process.env.NEXT_PUBLIC_BACKEND_URL?.trim() || "http://localhost:8000",
    []
  );

  useEffect(() => {
    setIsLoading(true);
    fetch(`${BACKEND_URL}/api/dashboard/interviews`)
      .then(async (res) => {
        if (!res.ok) throw new Error(`Backend returned ${res.status}`);
        return res.json() as Promise<{ items: DashboardRow[] }>;
      })
      .then((data) => {
        setItems(data.items ?? []);
        setError(null);
      })
      .catch((e) => setError(e instanceof Error ? e.message : "Failed to load data"))
      .finally(() => setIsLoading(false));
  }, [BACKEND_URL]);

  return (
    <div className="rounded-xl border border-[var(--color-border)] bg-[var(--color-surface-elevated)] overflow-hidden">
      <div className="border-b border-[var(--color-border)] px-4 py-3 flex items-center justify-between">
        <p className="text-sm font-medium text-[var(--color-muted)]">
          Sessions
        </p>
        <p className="text-xs text-[var(--color-muted)]">
          Source: `backend/data`
        </p>
      </div>

      {error && (
        <div className="px-4 py-3 text-sm text-red-600">
          Couldn’t load dashboard data. {error}
        </div>
      )}

      {isLoading ? (
        <div className="px-4 py-6 text-sm text-[var(--color-muted)]">
          Loading sessions…
        </div>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead>
              <tr className="border-b border-[var(--color-border)] bg-[var(--color-surface)]">
                <th className="px-4 py-3 font-medium">Candidate</th>
                <th className="px-4 py-3 font-medium">Role</th>
                <th className="px-4 py-3 font-medium">Date</th>
                <th className="px-4 py-3 font-medium">Eval</th>
                <th className="px-4 py-3 font-medium">Speech</th>
                <th className="px-4 py-3 font-medium">Score</th>
                <th className="px-4 py-3 font-medium text-right">Actions</th>
              </tr>
            </thead>
            <tbody>
              {items.length === 0 ? (
                <tr>
                  <td
                    className="px-4 py-6 text-sm text-[var(--color-muted)]"
                    colSpan={7}
                  >
                    No completed interviews found yet.
                  </td>
                </tr>
              ) : (
                items.map((row) => (
                  <tr
                    key={row.id}
                    className="border-b border-[var(--color-border)] last:border-0 hover:bg-black/[0.02]"
                  >
                    <td className="px-4 py-3 font-medium">{row.candidateName}</td>
                    <td className="px-4 py-3 text-[var(--color-muted)]">
                      {row.role}
                    </td>
                    <td className="px-4 py-3">
                      {new Date(row.date * 1000).toLocaleString()}
                    </td>
                    <td className="px-4 py-3">
                      {row.hasEvaluation ? "Yes" : "—"}
                    </td>
                    <td className="px-4 py-3">
                      {row.hasSpeechStats ? "Yes" : "—"}
                    </td>
                    <td className="px-4 py-3">
                      <ScoreBadge score={row.overallScore ?? null} />
                    </td>
                    <td className="px-4 py-3 text-right">
                      <Link
                        href={`/interviewer/${row.id}`}
                        className="text-[var(--color-primary)] hover:underline font-medium"
                      >
                        View
                      </Link>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

