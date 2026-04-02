"use client";

export type ImprovementArea = {
  id: string;
  title: string;
  description: string;
  priority: "high" | "medium" | "low";
};

const mockAreas: ImprovementArea[] = [
  {
    id: "1",
    title: "Structure your answers (STAR)",
    description: "Use Situation, Task, Action, Result when describing past projects to keep answers clear and complete.",
    priority: "high",
  },
  {
    id: "2",
    title: "Pause before answering",
    description: "Take a moment to think before responding. It shows deliberation and often improves clarity.",
    priority: "medium",
  },
  {
    id: "3",
    title: "Ask clarifying questions",
    description: "When given a scenario, ask one or two clarifying questions before diving into the solution.",
    priority: "medium",
  },
];

function PriorityBadge({ priority }: { priority: ImprovementArea["priority"] }) {
  const styles = {
    high: "bg-amber-500/15 text-amber-700",
    medium: "bg-blue-500/15 text-blue-700",
    low: "bg-[var(--color-muted)]/20 text-[var(--color-muted)]",
  };
  return (
    <span
      className={`inline-flex rounded-full px-2 py-0.5 text-xs font-medium capitalize ${styles[priority]}`}
    >
      {priority}
    </span>
  );
}

export function FeedbackSection() {
  return (
    <div className="rounded-xl border border-[var(--color-border)] bg-[var(--color-surface-elevated)] overflow-hidden">
      <div className="border-b border-[var(--color-border)] px-4 py-2.5">
        <h3 className="text-sm font-medium text-[var(--color-muted)] flex items-center gap-2">
          <span aria-hidden>💡</span>
          Areas to improve
        </h3>
      </div>
      <ul className="divide-y divide-[var(--color-border)]">
        {mockAreas.map((area) => (
          <li key={area.id} className="px-4 py-3">
            <div className="flex items-start justify-between gap-2">
              <span className="text-sm font-medium text-[var(--color-primary)]">
                {area.title}
              </span>
              <PriorityBadge priority={area.priority} />
            </div>
            <p className="mt-1 text-sm text-[var(--color-muted)]">
              {area.description}
            </p>
          </li>
        ))}
      </ul>
    </div>
  );
}
