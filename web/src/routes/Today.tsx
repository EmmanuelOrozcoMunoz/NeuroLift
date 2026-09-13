import { useQueries } from "@tanstack/react-query";
import { Link } from "react-router-dom";

import { PageHeader } from "@/components/AppShell";
import { IconDumbbell, IconStore } from "@/components/icons";
import { SessionCard } from "@/components/SessionCard";
import { Button, Card, EmptyState, ErrorState, LoadingList, SectionTitle } from "@/components/ui";
import { apiFetch } from "@/lib/api";
import { useCurrentUser } from "@/lib/auth";
import { daysFromToday, longDate, parseApiDate, todayIso, toApiDate } from "@/lib/dates";
import { queryKeys, useMesocycles } from "@/lib/queries";
import { splitSessions } from "@/lib/sessions";
import type { MesocycleFull, TrainingSession } from "@/lib/types";

interface SessionRef {
  session: TrainingSession;
  mesocycleId: string;
  mesocycleName: string;
  adapted?: TrainingSession;
}

/** Lunes de la semana en curso, en formato de la API. */
function startOfWeekIso(): string {
  const now = new Date();
  const dayOfWeek = (now.getDay() + 6) % 7; // 0 = lunes
  const monday = new Date(now.getFullYear(), now.getMonth(), now.getDate() - dayOfWeek);
  return toApiDate(monday);
}

export default function Today() {
  const user = useCurrentUser();
  const mesocycles = useMesocycles(user.id);

  // Un atleta puede tener a la vez el mesociclo de su coach y un plan que adquirió, así que
  // "hoy" se busca en todos los mesociclos activos, no en uno solo.
  const activos = (mesocycles.data ?? []).filter((mesocycle) => mesocycle.is_active).slice(0, 5);

  const detalles = useQueries({
    queries: activos.map((mesocycle) => ({
      queryKey: queryKeys.mesocycle(mesocycle.id),
      queryFn: () => apiFetch<MesocycleFull>(`/mesocycles/${mesocycle.id}`),
    })),
  });

  const cargando = mesocycles.isPending || detalles.some((query) => query.isPending);
  const error = mesocycles.error ?? detalles.find((query) => query.error)?.error;

  const todas: SessionRef[] = [];
  for (const query of detalles) {
    const mesocycle = query.data;
    if (!mesocycle) continue;
    const { originals, adaptedByParent } = splitSessions(mesocycle.sessions);
    for (const session of originals) {
      todas.push({
        session,
        mesocycleId: mesocycle.id,
        mesocycleName: mesocycle.name ?? "Mi rutina",
        adapted: adaptedByParent.get(session.id),
      });
    }
  }

  const hoyIso = todayIso();
  const deHoy = todas.filter((item) => item.session.scheduled_date === hoyIso);
  const proximas = todas
    .filter((item) => daysFromToday(item.session.scheduled_date) > 0)
    .sort(
      (a, b) =>
        parseApiDate(a.session.scheduled_date).getTime() -
        parseApiDate(b.session.scheduled_date).getTime(),
    )
    .slice(0, 3);
  const pendientesAtras = todas
    .filter(
      (item) =>
        daysFromToday(item.session.scheduled_date) < 0 &&
        item.session.status !== "completed" &&
        item.session.sets.length > 0,
    )
    .slice(-2);

  // Progreso de la semana en curso
  const lunes = startOfWeekIso();
  const deLaSemana = todas.filter(
    (item) => item.session.scheduled_date >= lunes && item.session.scheduled_date <= addDays(lunes, 6),
  );
  const hechasSemana = deLaSemana.filter((item) => item.session.status === "completed").length;

  const nombreCorto = user.full_name.split(" ")[0];

  return (
    <>
      <PageHeader title={`Hola, ${nombreCorto}`} subtitle={capitalize(longDate(hoyIso))} />

      {cargando && <LoadingList rows={2} />}

      {!cargando && error && <ErrorState error={error} onRetry={() => void mesocycles.refetch()} />}

      {!cargando && !error && (
        <>
          {deLaSemana.length > 0 && (
            <Card className="mb-4 flex flex-wrap items-center justify-between gap-x-3 gap-y-2">
              <div className="shrink-0">
                <p className="text-sm text-muted">Esta semana</p>
                <p className="text-2xl font-bold">
                  {hechasSemana}
                  <span className="text-base font-semibold text-muted">/{deLaSemana.length}</span>
                  <span className="ml-1.5 text-sm font-medium text-muted">sesiones</span>
                </p>
              </div>
              <div className="flex min-w-0 flex-1 flex-wrap justify-end gap-1.5">
                {deLaSemana.map((item) => (
                  <span
                    key={item.session.id}
                    title={item.session.scheduled_date}
                    className={
                      item.session.status === "completed"
                        ? "h-8 w-2.5 shrink-0 rounded-full bg-done"
                        : item.session.scheduled_date === hoyIso
                          ? "h-8 w-2.5 shrink-0 rounded-full bg-brand"
                          : "h-8 w-2.5 shrink-0 rounded-full bg-surface-2"
                    }
                  />
                ))}
              </div>
            </Card>
          )}

          {todas.length === 0 ? (
            <EmptyState
              icon={<IconStore className="h-10 w-10" />}
              title="Todavía no tienes entrenamientos"
              action={
                <Link to="/planes">
                  <Button>Ver planes disponibles</Button>
                </Link>
              }
            >
              Pídele a tu coach que te programe un mesociclo, o adquiere un plan hecho por un
              entrenador y empieza por tu cuenta.
            </EmptyState>
          ) : deHoy.length > 0 ? (
            <>
              <SectionTitle>Tu sesión de hoy</SectionTitle>
              <div className="space-y-3">
                {deHoy.map((item) => (
                  <SessionCard
                    key={item.session.id}
                    session={item.session}
                    mesocycleId={item.mesocycleId}
                    adapted={item.adapted}
                    highlight
                  />
                ))}
              </div>
            </>
          ) : (
            <EmptyState icon={<IconDumbbell className="h-10 w-10" />} title="Hoy descansas">
              No tienes sesión programada para hoy. Aprovecha para recuperar.
            </EmptyState>
          )}

          {pendientesAtras.length > 0 && (
            <>
              <SectionTitle>Sin registrar</SectionTitle>
              <div className="space-y-3">
                {pendientesAtras.map((item) => (
                  <SessionCard
                    key={item.session.id}
                    session={item.session}
                    mesocycleId={item.mesocycleId}
                    adapted={item.adapted}
                  />
                ))}
              </div>
            </>
          )}

          {proximas.length > 0 && (
            <>
              <SectionTitle
                action={
                  <Link to="/entrenos" className="text-xs font-semibold text-brand">
                    Ver todo
                  </Link>
                }
              >
                Lo que viene
              </SectionTitle>
              <div className="space-y-3">
                {proximas.map((item) => (
                  <SessionCard
                    key={item.session.id}
                    session={item.session}
                    mesocycleId={item.mesocycleId}
                    adapted={item.adapted}
                  />
                ))}
              </div>
            </>
          )}
        </>
      )}
    </>
  );
}

function addDays(iso: string, days: number): string {
  const date = parseApiDate(iso);
  date.setDate(date.getDate() + days);
  return toApiDate(date);
}

function capitalize(text: string): string {
  return text.charAt(0).toUpperCase() + text.slice(1);
}
