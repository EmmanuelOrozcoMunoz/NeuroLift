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
  // La programación de una clase vuelve al horario de clases, no a un mesociclo de atleta
  const backTo = data?.class_id ? "/clases" : `/coach/mesociclos/${mesocycleId}`;

  if (isPending) {
    return (
      <>
        <PageHeader title="Sesión" back={backTo} />
        <LoadingList rows={3} />
      </>
    );
  }
  if (error) {
    return (
      <>
        <PageHeader title="Sesión" back={backTo} />
        <ErrorState error={error} onRetry={() => void refetch()} />
      </>
    );
  }
  if (!session) {
    return (
      <>
        <PageHeader title="Sesión" back={backTo} />
        <EmptyState title="No encontramos esta sesión" />
      </>
    );
  }

  return (
    <>
      <PageHeader
        title={longDate(session.scheduled_date)}
        subtitle={data?.class_id ? `Clase · ${data.name}` : (data?.name ?? "Mesociclo")}
        back={backTo}
      />

      <SessionSetsEditor
        mesocycleId={mesocycleId!}
        discipline={data?.discipline ?? ""}
        session={session}
        onFeedback={setToast}
      />

      {toast && <Toast message={toast} onDismiss={() => setToast(null)} />}
    </>
  );
}
