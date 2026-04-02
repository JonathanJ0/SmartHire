import Link from "next/link";

export type CandidateSession = {
  id: string;
  candidateName: string;
  role: string;
  date: string;
  duration: string;
  overallScore: number;
  status: "completed" | "in-progress";
};

const mockSessions: CandidateSession[] = [
  {
    id: "1",
    candidateName: "Alex Chen",
    role: "Frontend Developer",
    date: "2025-02-20",
    duration: "32 min",
    overallScore: 82,
    status: "completed",
  },
  {
    id: "2",
    candidateName: "Jordan Lee",
    role: "Full Stack Engineer",
    date: "2025-02-19",
    duration: "45 min",
    overallScore: 78,
    status: "completed",
  },
  {
    id: "3",
    candidateName: "Sam Rivera",
    role: "Frontend Developer",
    date: "2025-02-21",
    duration: "—",
    overallScore: 0,
    status: "in-progress",
  },
];

function ScoreBadge({ score }: { score: number }) {
  if (score === 0) return <span className="text-[var(--color-muted)]">—</span>;
  const color =
    score >= 80
      ? "text-[var(--color-accent)] bg-[var(--color-accent)]/15"
      : score >= 60
        ? "text-amber-600 bg-amber-500/15"
        : "text-red-600 bg-red-500/15";
  return (
    <span
      className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-sm font-medium ${color}`}
    >
      {score}%
    </span>
  );
}

export function CandidateTable() {
  return (
    <div className="rounded-xl border border-[var(--color-border)] bg-[var(--color-surface-elevated)] overflow-hidden">
      <div className="overflow-x-auto">
        <table className="w-full text-left text-sm">
          <thead>
            <tr className="border-b border-[var(--color-border)] bg-[var(--color-surface)]">
              <th className="px-4 py-3 font-medium">Candidate</th>
              <th className="px-4 py-3 font-medium">Role</th>
              <th className="px-4 py-3 font-medium">Date</th>
              <th className="px-4 py-3 font-medium">Duration</th>
              <th className="px-4 py-3 font-medium">Score</th>
              <th className="px-4 py-3 font-medium">Status</th>
              <th className="px-4 py-3 font-medium text-right">Actions</th>
            </tr>
          </thead>
          <tbody>
            {mockSessions.map((session) => (
              <tr
                key={session.id}
                className="border-b border-[var(--color-border)] last:border-0 hover:bg-black/[0.02]"
              >
                <td className="px-4 py-3 font-medium">{session.candidateName}</td>
                <td className="px-4 py-3 text-[var(--color-muted)]">
                  {session.role}
                </td>
                <td className="px-4 py-3">{session.date}</td>
                <td className="px-4 py-3">{session.duration}</td>
                <td className="px-4 py-3">
                  <ScoreBadge score={session.overallScore} />
                </td>
                <td className="px-4 py-3">
                  <span
                    className={`inline-flex rounded-full px-2.5 py-0.5 text-xs font-medium ${
                      session.status === "completed"
                        ? "bg-[var(--color-accent)]/15 text-[var(--color-accent)]"
                        : "bg-amber-500/15 text-amber-700"
                    }`}
                  >
                    {session.status === "completed" ? "Completed" : "In progress"}
                  </span>
                </td>
                <td className="px-4 py-3 text-right">
                  <Link
                    href={`/interviewer/${session.id}`}
                    className="text-[var(--color-primary)] hover:underline font-medium"
                  >
                    View
                  </Link>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
