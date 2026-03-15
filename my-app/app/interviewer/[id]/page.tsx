import { SessionDetailClient } from "@/components/interviewer/SessionDetailClient";

type Props = { params: Promise<{ id: string }> };

export default async function SessionDetailPage({ params }: Props) {
  const { id } = await params;
  return <SessionDetailClient sessionId={id} />;
}
