import { useParams } from "react-router-dom";

import { PageHeader } from "@/components/AppShell";
import { SessionCard } from "@/components/SessionCard";
import { Badge, EmptyState, ErrorState, LoadingList, SectionTitle } from "@/components/ui";
import { daysFromToday, parseApiDate } from "@/lib/dates";
import { useMesocycle } from "@/lib/queries";
import { splitSessions } from "@/lib/sessions";
import type { TrainingSession } from "@/lib/types";

/** Semana 1, 2, 3... contadas desde el inicio del mesociclo. */
function weekNumber(startDate: string, sessionDate: string): number {
  const diffDays = Math.floor(
    (parseApiDate(sessionDate).getTime() - parseApiDate(startDate).getTime()) / 86_400_000,
  );
  return Math.floor(Math.max(0, diffDays) / 7) + 1;
}

export default function MesocycleDetail() {
  const { mesocycleId } = useParams<{ mesocycleId: string }>();
  const { data, isPending, error, refetch } = useMesocycle(mesocycleId);

  const { originals, adaptedByParent } = splitSessions(data?.sessions ?? []);
  const completadas = originals.filter((session) => session.status === "completed").length;

  // Agrupamos por semana para que un mesociclo de 8 semanas no sea una lista infinita
  const porSemana = new Map<number, TrainingSession[]>();
  for (const session of originals) {
    const week = data ? weekNumber(data.start_date, session.scheduled_date) : 1;
    const lista = porSemana.get(week) ?? [];
    lista.push(session);
    porSemana.set(week, lista);
  }

  // La semana que contiene hoy (o la más cercana) es la que interesa: se abre primero
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
        subtitle={data ? `${data.discipline} · ${completadas}/${originals.length} sesiones hechas` : undefined}
        back="/entrenos"
      />

      {isPending && <LoadingList rows={4} />}
      {!isPending && error && <ErrorState error={error} onRetry={() => void refetch()} />}

      {!isPending && !error && originals.length === 0 && (
        <EmptyState title="Este mesociclo todavía no tiene sesiones">
          Tu coach aún no ha cargado los días de entrenamiento.
        </EmptyState>
      )}

      {[...porSemana.entries()].map(([week, sesiones]) => (
        <section key={week}>
          <SectionTitle
            action={
              week === semanaActual ? <Badge tone="brand">Semana en curso</Badge> : undefined
            }
          >
            Semana {week}
          </SectionTitle>
          <div className="space-y-3">
            {sesiones.map((session) => (
              <SessionCard
                key={session.id}
                session={session}
                mesocycleId={mesocycleId!}
                adapted={adaptedByParent.get(session.id)}
              />
            ))}
          </div>
        </section>
      ))}
    </>
  );
}
