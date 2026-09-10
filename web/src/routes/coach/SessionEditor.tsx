import { useState } from "react";
import { useParams } from "react-router-dom";

import { PageHeader } from "@/components/AppShell";
import { SessionSetsEditor } from "@/components/SessionSetsEditor";
import { EmptyState, ErrorState, LoadingList, Toast } from "@/components/ui";
import { longDate } from "@/lib/dates";
import { useMesocycle } from "@/lib/queries";

export default function CoachSessionEditor() {
  const { mesocycleId, sessionId } = useParams<{ mesocycleId: string; sessionId: string }>();
  const { data, isPending, error, refetch } = useMesocycle(mesocycleId);
  const [toast, setToast] = useState<string | null>(null);

  const session = data?.sessions.find((s) => s.id === sessionId);

  if (isPending) {
    return (
      <>
        <PageHeader title="Sesión" back={`/coach/mesociclos/${mesocycleId}`} />
        <LoadingList rows={3} />
      </>
    );
  }
  if (error) {
    return (
      <>
        <PageHeader title="Sesión" back={`/coach/mesociclos/${mesocycleId}`} />
        <ErrorState error={error} onRetry={() => void refetch()} />
      </>
    );
  }
  if (!session) {
    return (
      <>
        <PageHeader title="Sesión" back={`/coach/mesociclos/${mesocycleId}`} />
        <EmptyState title="No encontramos esta sesión" />
      </>
    );
  }

  return (
    <>
      <PageHeader
        title={longDate(session.scheduled_date)}
        subtitle={data?.name ?? "Mesociclo"}
        back={`/coach/mesociclos/${mesocycleId}`}
      />

      <SessionSetsEditor mesocycleId={mesocycleId!} session={session} onFeedback={setToast} />

      {toast && <Toast message={toast} onDismiss={() => setToast(null)} />}
    </>
  );
}
