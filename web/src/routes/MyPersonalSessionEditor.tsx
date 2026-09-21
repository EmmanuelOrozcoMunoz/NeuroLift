import { useState } from "react";
import { useParams } from "react-router-dom";

import { PageHeader } from "@/components/AppShell";
import { SessionSetsEditor } from "@/components/SessionSetsEditor";
import { EmptyState, ErrorState, LoadingList, Toast } from "@/components/ui";
import { longDate } from "@/lib/dates";
import { useMesocycle } from "@/lib/queries";

/** El propio atleta agrega/edita los ejercicios de una sesión que él mismo creó a mano (sin
 *  coach) -- mismo componente que usa el coach (SessionSetsEditor), el backend ya limita esto a
 *  mesociclos is_self_managed=True. Para SEGUIR/registrar lo hecho, esa misma sesión se abre
 *  como cualquier otra en SessionDetail.tsx; esta pantalla es solo para armar el plan del día. */
export default function MyPersonalSessionEditor() {
  const { mesocycleId, sessionId } = useParams<{ mesocycleId: string; sessionId: string }>();
  const { data, isPending, error, refetch } = useMesocycle(mesocycleId);
  const [toast, setToast] = useState<string | null>(null);

  const session = data?.sessions.find((s) => s.id === sessionId);

  if (isPending) {
    return (
      <>
        <PageHeader title="Sesión" back={`/entrenos/${mesocycleId}`} />
        <LoadingList rows={3} />
      </>
    );
  }
  if (error) {
    return (
      <>
        <PageHeader title="Sesión" back={`/entrenos/${mesocycleId}`} />
        <ErrorState error={error} onRetry={() => void refetch()} />
      </>
    );
  }
  if (!session) {
    return (
      <>
        <PageHeader title="Sesión" back={`/entrenos/${mesocycleId}`} />
        <EmptyState title="No encontramos esta sesión" />
      </>
    );
  }

  return (
    <>
      <PageHeader
        title={longDate(session.scheduled_date)}
        subtitle={data?.name ?? "Mis entrenamientos"}
        back={`/entrenos/${mesocycleId}`}
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
