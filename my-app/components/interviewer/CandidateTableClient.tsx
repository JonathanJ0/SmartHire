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
  hasMonitor: boolean;
};

type SortOption = "date_desc" | "date_asc" | "score_pct_desc" | "score_pct_asc";

function scoreToPct(score: number | null | undefined) {
  if (score === null || score === undefined || Number.isNaN(score)) return null;
  return Math.round((Number(score) / 10) * 100);
}

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
  const [sortOption, setSortOption] = useState<SortOption>("date_desc");

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

  const sortedItems = useMemo(() => {
    const copy = [...items];

    copy.sort((a, b) => {
      const roleA = (a.role ?? "").toLowerCase();
      const roleB = (b.role ?? "").toLowerCase();
      if (roleA < roleB) return -1;
      if (roleA > roleB) return 1;

      const nameA = a.candidateName?.toLowerCase() ?? "";
      const nameB = b.candidateName?.toLowerCase() ?? "";

      if (sortOption === "date_desc") {
        const d = b.date - a.date;
        if (d !== 0) return d;
        return nameA.localeCompare(nameB);
      }
      if (sortOption === "date_asc") {
        const d = a.date - b.date;
        if (d !== 0) return d;
        return nameA.localeCompare(nameB);
      }

      const pctA = scoreToPct(a.overallScore);
      const pctB = scoreToPct(b.overallScore);

      // Put sessions without evaluation score at the end for both directions.
      if (pctA === null && pctB === null) return b.date - a.date;
      if (pctA === null) return 1;
      if (pctB === null) return -1;

      if (sortOption === "score_pct_desc") {
        const d = pctB - pctA;
        if (d !== 0) return d;
        return b.date - a.date;
      }

      const d = pctA - pctB;
      if (d !== 0) return d;
      return b.date - a.date;
    });

    return copy;
  }, [items, sortOption]);

  return (
    <div className="rounded-xl border border-[var(--color-border)] bg-[var(--color-surface-elevated)] overflow-hidden">
      <div className="border-b border-[var(--color-border)] px-4 py-3 flex items-center justify-between gap-3 flex-wrap">
        <div className="flex items-center gap-4">
          <p className="text-sm font-medium text-[var(--color-muted)]">Sessions</p>
          <p className="text-xs text-[var(--color-muted)]">Source: `backend/data`</p>
        </div>

        <div className="flex items-center gap-2">
          <label htmlFor="dashboard-sort" className="text-xs text-[var(--color-muted)]">
            Sort
          </label>
          <select
            id="dashboard-sort"
            value={sortOption}
            onChange={(e) => setSortOption(e.target.value as SortOption)}
            className="text-xs border border-[var(--color-border)] rounded-md px-2 py-1 bg-[var(--color-surface)]"
          >
            <option value="date_desc">Date (newest)</option>
            <option value="date_asc">Date (oldest)</option>
            <option value="score_pct_desc">Score % (highest)</option>
            <option value="score_pct_asc">Score % (lowest)</option>
          </select>
        </div>
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
                <th className="px-4 py-3 font-medium">Monitor</th>
                <th className="px-4 py-3 font-medium">Score</th>
                <th className="px-4 py-3 font-medium text-right">Actions</th>
              </tr>
            </thead>
            <tbody>
              {sortedItems.length === 0 ? (
                <tr>
                  <td
                    className="px-4 py-6 text-sm text-[var(--color-muted)]"
                    colSpan={8}
                  >
                    No completed interviews found yet.
                  </td>
                </tr>
              ) : (
                sortedItems.map((row) => (
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
                      {row.hasMonitor ? "Yes" : "—"}
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

