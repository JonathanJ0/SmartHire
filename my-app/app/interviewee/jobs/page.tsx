import { JobBrowserClient } from "@/components/interviewee/JobBrowserClient";

export const metadata = {
  title: "Browse Open Roles – SmartHire",
  description: "Explore open job positions and select a role to interview for.",
};

export default function IntervieweeJobsPage() {
  return (
    <div className="mx-auto max-w-6xl px-4 py-8 sm:px-6 lg:px-8">
      <h1 className="text-2xl font-bold text-[var(--color-primary)]">
        Open positions
      </h1>
      <p className="mt-1 text-sm text-[var(--color-muted)]">
        Browse available roles below. Select one to start your AI-powered interview session.
      </p>

      <div className="mt-8">
        <JobBrowserClient />
      </div>
    </div>
  );
}
