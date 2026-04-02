import { IntervieweeSession } from "@/components/interviewee/IntervieweeSession";
import { ResumeRequiredGate } from "@/components/interviewee/ResumeRequiredGate";

export default function IntervieweePage() {
  return (
    <div className="mx-auto max-w-6xl px-4 py-8 sm:px-6 lg:px-8">
      <h1 className="text-2xl font-bold text-[var(--color-primary)]">
        Interview session
      </h1>
      <p className="mt-1 text-sm text-[var(--color-muted)]">
        Turn on your camera and chat with the AI interviewer.
      </p>

      <ResumeRequiredGate>
        <IntervieweeSession />
      </ResumeRequiredGate>
    </div>
  );
}
