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
  monitorStats: any | null;
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
    <div className="mx-auto max-w-5xl px-4 py-8 sm:px-6 lg:px-8">
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
          <div className="mt-6 border-b border-[var(--color-border)] pb-6">
            <h1 className="text-3xl font-bold text-[var(--color-primary)]">
              {candidateName}
            </h1>
            <p className="mt-1 text-lg text-[var(--color-muted)]">
              {data.role}
            </p>
            <p className="mt-1 text-xs text-[var(--color-muted)] opacity-70">
              Session ID: {data.id} · Concluded {new Date(data.updatedAt * 1000).toLocaleString()}
            </p>
          </div>

          <div className="mt-8 grid gap-6 sm:grid-cols-3">
            {/* Overall Score Card */}
            <div className="rounded-xl border border-[var(--color-border)] bg-[var(--color-surface-elevated)] p-5 shadow-sm">
              <h2 className="text-sm font-semibold uppercase tracking-wider text-[var(--color-muted)]">
                AI Recommendation
              </h2>
              <p className="mt-2 text-4xl font-bold text-[var(--color-accent)]">
                {overallPct === null ? "—" : `${overallPct}%`}
              </p>
              {data.evaluation?.recommendation && (
                <p className="mt-2 inline-flex rounded-full bg-[var(--color-accent)]/10 px-3 py-1 text-sm font-medium text-[var(--color-accent)]">
                  {data.evaluation.recommendation}
                </p>
              )}
            </div>

            {/* Speech Summary Card */}
            <div className="rounded-xl border border-[var(--color-border)] bg-[var(--color-surface-elevated)] p-5 shadow-sm">
              <h2 className="text-sm font-semibold uppercase tracking-wider text-[var(--color-muted)]">
                Speech Analytics
              </h2>
              {data.speechStats?.aggregate ? (
                <ul className="mt-3 space-y-2 text-sm">
                  <li className="flex justify-between border-b border-[var(--color-border)] pb-1">
                    <span className="text-[var(--color-muted)]">Utterances</span>
                    <span className="font-semibold text-[var(--color-primary)]">
                      {data.speechStats.aggregate.utterance_count ?? "—"}
                    </span>
                  </li>
                  <li className="flex justify-between border-b border-[var(--color-border)] pb-1">
                    <span className="text-[var(--color-muted)]">Words spoken</span>
                    <span className="font-semibold text-[var(--color-primary)]">
                      {data.speechStats.aggregate.total_words ?? "—"}
                    </span>
                  </li>
                  <li className="flex justify-between border-b border-[var(--color-border)] pb-1">
                    <span className="text-[var(--color-muted)]">Filler words</span>
                    <span className="font-semibold text-amber-600">
                      {data.speechStats.aggregate.total_fillers ?? "—"}
                    </span>
                  </li>
                </ul>
              ) : (
                <p className="mt-3 text-sm text-[var(--color-muted)]">No speech data captured.</p>
              )}
            </div>

            {/* Monitor Summary Card */}
            <div className="rounded-xl border border-[var(--color-border)] bg-[var(--color-surface-elevated)] p-5 shadow-sm">
              <h2 className="text-sm font-semibold uppercase tracking-wider text-[var(--color-muted)]">
                Facial Telemetry
              </h2>
              {data.monitorStats?.stats ? (
                <ul className="mt-3 space-y-2 text-sm">
                  <li className="flex justify-between border-b border-[var(--color-border)] pb-1">
                    <span className="text-[var(--color-muted)]">Suspicion Score</span>
                    <span className="font-semibold text-red-500">
                      {data.monitorStats.stats.suspicious_score ?? "—"}
                    </span>
                  </li>
                  <li className="flex justify-between border-b border-[var(--color-border)] pb-1">
                    <span className="text-[var(--color-muted)]">Total Alerts</span>
                    <span className="font-semibold text-[var(--color-primary)]">
                      {data.monitorStats.stats.total_alerts ?? 0}
                    </span>
                  </li>
                  <li className="flex justify-between border-b border-[var(--color-border)] pb-1">
                    <span className="text-[var(--color-muted)]">No Face Frames</span>
                    <span className="font-semibold text-[var(--color-primary)]">
                      {data.monitorStats.stats.no_face_frames ?? 0}
                    </span>
                  </li>
                  <li className="flex justify-between pb-1">
                    <span className="text-[var(--color-muted)]">Gaze Away Events</span>
                    <span className="font-semibold text-[var(--color-primary)]">
                      {data.monitorStats.stats.gaze_away_events ?? 0}
                    </span>
                  </li>
                </ul>
              ) : (
                <p className="mt-3 text-sm text-[var(--color-muted)]">No video telemetry captured.</p>
              )}
            </div>
          </div>

          {/* Deep Evaluation Report */}
          {data.evaluation && (
            <div className="mt-8">
              <h2 className="text-xl font-bold text-[var(--color-primary)]">Evaluation Report</h2>
              <div className="mt-4 rounded-xl border border-[var(--color-border)] bg-[var(--color-surface-elevated)] p-6 shadow-sm">
                
                {/* Executive Summary */}
                {data.evaluation.summary && (
                  <div className="mb-6">
                    <h3 className="text-sm font-semibold uppercase tracking-wider text-[var(--color-muted)] mb-2">Executive Summary</h3>
                    <p className="text-sm leading-relaxed text-[var(--color-primary)]">
                      {data.evaluation.summary}
                    </p>
                  </div>
                )}

                {/* Flags and Positives */}
                {(data.evaluation.notable_positives?.length > 0 || data.evaluation.red_flags?.length > 0) && (
                  <div className="mb-8 grid gap-4 grid-cols-1 md:grid-cols-2">
                    {data.evaluation.notable_positives?.length > 0 && (
                      <div className="rounded-lg border border-green-200 bg-green-50 p-4">
                        <h4 className="font-semibold text-green-800 flex items-center gap-2">
                          <span className="text-lg">✅</span> Notable Positives
                        </h4>
                        <ul className="mt-2 list-inside list-disc text-sm text-green-700 space-y-1">
                          {data.evaluation.notable_positives.map((p: string, i: number) => (
                            <li key={i}>{p}</li>
                          ))}
                        </ul>
                      </div>
                    )}
                    {data.evaluation.red_flags?.length > 0 && (
                      <div className="rounded-lg border border-red-200 bg-red-50 p-4">
                        <h4 className="font-semibold text-red-800 flex items-center gap-2">
                          <span className="text-lg">⚠️</span> Red Flags
                        </h4>
                        <ul className="mt-2 list-inside list-disc text-sm text-red-700 space-y-1">
                          {data.evaluation.red_flags.map((f: string, i: number) => (
                            <li key={i}>{f}</li>
                          ))}
                        </ul>
                      </div>
                    )}
                  </div>
                )}

                {/* Metric Breakdown */}
                {data.evaluation.metrics && Object.keys(data.evaluation.metrics).length > 0 && (
                  <div>
                    <h3 className="text-sm font-semibold uppercase tracking-wider text-[var(--color-muted)] mb-4 border-b border-[var(--color-border)] pb-2">
                      Metric Breakdown
                    </h3>
                    <div className="space-y-6">
                      {Object.entries(data.evaluation.metrics).map(([metricName, metric]: [string, any]) => {
                        const label = metricName.replace(/_/g, " ");
                        const score = Number(metric.score || 0);
                        const progressPct = score * 10;
                        const barColor = score >= 8 ? "bg-green-500" : score >= 5 ? "bg-amber-500" : "bg-red-500";

                        return (
                          <div key={metricName} className="rounded-lg bg-[var(--color-surface)] p-4 border border-[var(--color-border)]">
                            <div className="flex items-center justify-between mb-2">
                              <h4 className="capitalize font-semibold text-[var(--color-primary)] text-sm">{label}</h4>
                              <span className={`px-2 py-0.5 rounded text-xs font-bold text-white ${barColor}`}>
                                {score} / 10
                              </span>
                            </div>
                            
                            {/* Visual Progress Bar */}
                            <div className="w-full bg-[var(--color-border)] rounded-full h-1.5 mb-3">
                              <div className={`${barColor} h-1.5 rounded-full`} style={{ width: `${progressPct}%` }}></div>
                            </div>

                            <p className="text-sm text-[var(--color-muted)] mb-3 leading-relaxed">
                              {metric.justification}
                            </p>

                            {(metric.strengths?.length > 0 || metric.improvements?.length > 0) && (
                              <div className="mt-3 grid gap-3 sm:grid-cols-2 text-xs">
                                {metric.strengths?.length > 0 && (
                                  <div>
                                    <span className="font-semibold text-[var(--color-primary)]">Strengths:</span>
                                    <ul className="list-inside list-disc text-[var(--color-muted)] mt-1">
                                      {metric.strengths.map((s: string, i: number) => <li key={i}>{s}</li>)}
                                    </ul>
                                  </div>
                                )}
                                {metric.improvements?.length > 0 && (
                                  <div>
                                    <span className="font-semibold text-[var(--color-primary)]">Opportunities:</span>
                                    <ul className="list-inside list-disc text-[var(--color-muted)] mt-1">
                                      {metric.improvements.map((im: string, i: number) => <li key={i}>{im}</li>)}
                                    </ul>
                                  </div>
                                )}
                              </div>
                            )}
                          </div>
                        );
                      })}
                    </div>
                  </div>
                )}
              </div>
            </div>
          )}

          <div className="mt-8 rounded-xl border border-[var(--color-border)] bg-[var(--color-surface-elevated)] p-6 shadow-sm">
            <h2 className="text-sm font-semibold uppercase tracking-wider text-[var(--color-muted)] mb-2 border-b border-[var(--color-border)] pb-2">
              Raw Transcript
            </h2>
            <pre className="mt-4 max-h-[500px] overflow-y-auto whitespace-pre-wrap text-[13px] leading-relaxed text-[var(--color-muted)] font-mono">
              {data.transcriptText}
            </pre>
          </div>
        </>
      )}
    </div>
  );
}
