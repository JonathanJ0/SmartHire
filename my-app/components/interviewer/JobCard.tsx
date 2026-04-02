"use client";

export type Job = {
  id: string;
  title: string;
  department: string;
  location: string;
  job_type: string;
  description: string;
  requirements: string[];
  created_at: number;
};

type JobCardProps = {
  job: Job;
  /** If provided, renders a "Select this role" action button */
  onSelect?: (job: Job) => void;
  /** If provided, renders a "Delete" action button (interviewer side) */
  onDelete?: (job: Job) => void;
  selected?: boolean;
};

const JOB_TYPE_COLORS: Record<string, string> = {
  "Full-time": "bg-[oklch(0.93_0.05_260)] text-[oklch(0.35_0.18_260)]",
  "Part-time": "bg-[oklch(0.93_0.06_160)] text-[oklch(0.35_0.18_160)]",
  Contract: "bg-[oklch(0.94_0.06_60)] text-[oklch(0.38_0.15_60)]",
  Internship: "bg-[oklch(0.93_0.06_310)] text-[oklch(0.38_0.15_310)]",
};

export function JobCard({ job, onSelect, onDelete, selected = false }: JobCardProps) {
  const typeColor =
    JOB_TYPE_COLORS[job.job_type] ??
    "bg-[var(--color-border)] text-[var(--color-muted)]";

  return (
    <div
      className={`rounded-2xl border bg-[var(--color-surface-elevated)] p-6 shadow-sm transition-all flex flex-col gap-4 ${
        selected
          ? "border-[var(--color-primary)] ring-2 ring-[var(--color-primary)]/20"
          : "border-[var(--color-border)] hover:border-[var(--color-primary)]/50 hover:shadow-md"
      }`}
    >
      {/* Header */}
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <h3 className="text-lg font-semibold text-[var(--color-primary)] truncate">
            {job.title}
          </h3>
          {job.department && (
            <p className="mt-0.5 text-sm text-[var(--color-muted)]">
              {job.department}
            </p>
          )}
        </div>
        <span
          className={`shrink-0 rounded-full px-3 py-1 text-xs font-medium ${typeColor}`}
        >
          {job.job_type}
        </span>
      </div>

      {/* Meta chips */}
      <div className="flex flex-wrap gap-2">
        {job.location && (
          <span className="flex items-center gap-1 rounded-full border border-[var(--color-border)] px-3 py-0.5 text-xs text-[var(--color-muted)]">
            📍 {job.location}
          </span>
        )}
        {job.requirements.length > 0 && (
          <span className="flex items-center gap-1 rounded-full border border-[var(--color-border)] px-3 py-0.5 text-xs text-[var(--color-muted)]">
            ✅ {job.requirements.length} requirement{job.requirements.length !== 1 ? "s" : ""}
          </span>
        )}
      </div>

      {/* Description */}
      {job.description && (
        <p className="text-sm text-[var(--color-muted)] line-clamp-3 leading-relaxed">
          {job.description}
        </p>
      )}

      {/* Requirements list */}
      {job.requirements.length > 0 && (
        <ul className="flex flex-col gap-1.5">
          {job.requirements.slice(0, 5).map((req, i) => (
            <li key={i} className="flex items-start gap-2 text-sm text-[oklch(0.3_0.02_260)]">
              <span className="mt-0.5 text-[var(--color-accent)] shrink-0">▸</span>
              {req}
            </li>
          ))}
          {job.requirements.length > 5 && (
            <li className="text-xs text-[var(--color-muted)] pl-4">
              +{job.requirements.length - 5} more…
            </li>
          )}
        </ul>
      )}

      {/* Actions */}
      {(onSelect || onDelete) && (
        <div className="mt-auto flex items-center gap-3 pt-2 border-t border-[var(--color-border)]">
          {onSelect && (
            <button
              type="button"
              id={`select-job-${job.id}`}
              onClick={() => onSelect(job)}
              className={`rounded-lg px-4 py-2 text-sm font-medium transition ${
                selected
                  ? "bg-[var(--color-primary)] text-white cursor-default"
                  : "bg-[var(--color-primary)] text-white hover:bg-[var(--color-primary-hover)]"
              }`}
            >
              {selected ? "✓ Selected" : "Apply for this role"}
            </button>
          )}
          {onDelete && (
            <button
              type="button"
              id={`delete-job-${job.id}`}
              onClick={() => onDelete(job)}
              className="ml-auto rounded-lg border border-red-200 px-3 py-1.5 text-xs text-red-500 hover:bg-red-50 transition"
            >
              Delete
            </button>
          )}
        </div>
      )}
    </div>
  );
}
