import { useParams } from "react-router-dom";

import { PageHeader } from "@/components/AppShell";
import { SessionCard } from "@/components/SessionCard";
import { Badge, EmptyState, ErrorState, LoadingList, SectionTitle } from "@/components/ui";
import { daysFromToday, parseApiDate } from "@/lib/dates";
import { useMesocycle } from "@/lib/queries";
import { sortSessions } from "@/lib/sessions";
import type { TrainingSession } from "@/lib/types";

function weekNumber(startDate: string, sessionDate: string): number {
  const diffDays = Math.floor(
    (parseApiDate(sessionDate).getTime() - parseApiDate(startDate).getTime()) / 86_400_000,
  );
  return Math.floor(Math.max(0, diffDays) / 7) + 1;
}

/** Vista del coach de un mesociclo: igual estructura que la del atleta (semanas + tarjetas de
 *  sesión), pero cada tarjeta abre el EDITOR de series, no el registro de entrenamiento. */
export default function CoachMesocycleEditor() {
  const { mesocycleId } = useParams<{ mesocycleId: string }>();
  const { data, isPending, error, refetch } = useMesocycle(mesocycleId);

  // Las sesiones "adaptadas al tiempo" son cosa del atleta; el coach solo edita las originales.
  const originales = sortSessions((data?.sessions ?? []).filter((s) => !s.parent_session_id));

  const porSemana = new Map<number, TrainingSession[]>();
  for (const session of originales) {
    const week = data ? weekNumber(data.start_date, session.scheduled_date) : 1;
    const lista = porSemana.get(week) ?? [];
    lista.push(session);
    porSemana.set(week, lista);
  }

  const semanaActual = (() => {
    let mejor = 1;
    let mejorDistancia = Number.POSITIVE_INFINITY;
    for (const [week, sesiones] of porSemana) {
      for (const session of sesiones) {
        const distancia = Math.abs(daysFromToday(session.scheduled_date));
        if (distancia < mejorDistancia) {
          mejorDistancia = distancia;
          mejor = week;
        }
      }
    }
    return mejor;
  })();

  return (
    <>
      <PageHeader
        title={data?.name ?? "Mesociclo"}
        subtitle={data ? `${data.discipline} · ${originales.length} sesiones` : undefined}
        back
      />

      {isPending && <LoadingList rows={4} />}
      {!isPending && error && <ErrorState error={error} onRetry={() => void refetch()} />}

      {!isPending && !error && originales.length === 0 && (
        <EmptyState title="Este mesociclo todavía no tiene sesiones" />
      )}

      {[...porSemana.entries()].map(([week, sesiones]) => (
        <section key={week}>
          <SectionTitle action={week === semanaActual ? <Badge tone="brand">En curso</Badge> : undefined}>
            Semana {week}
          </SectionTitle>
          <div className="space-y-3">
            {sesiones.map((session) => (
              <SessionCard
                key={session.id}
                session={session}
                mesocycleId={mesocycleId!}
                to={`/coach/mesociclos/${mesocycleId}/sesion/${session.id}`}
              />
            ))}
          </div>
        </section>
      ))}
    </>
  );
}
