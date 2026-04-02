"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

export function RoleBasedNav() {
  const pathname = usePathname() ?? "";

  const isInterviewer = pathname.startsWith("/interviewer");
  const isInterviewee = pathname.startsWith("/interviewee");

  if (!isInterviewer && !isInterviewee) return null;

  return (
    <div className="flex gap-6">
      {isInterviewee && (
        <Link
          href="/interviewee/jobs"
          className="text-sm text-[var(--color-muted)] hover:text-[var(--color-primary)] transition"
        >
          Browse Jobs
        </Link>
      )}

      {isInterviewer && (
        <>
          <Link
            href="/interviewer"
            className="text-sm text-[var(--color-muted)] hover:text-[var(--color-primary)] transition"
          >
            Dashboard
          </Link>
          <Link
            href="/interviewer/jobs"
            className="text-sm text-[var(--color-muted)] hover:text-[var(--color-primary)] transition"
          >
            Manage Jobs
          </Link>
        </>
      )}
    </div>
  );
}

