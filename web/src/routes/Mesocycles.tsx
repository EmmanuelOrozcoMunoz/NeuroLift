import { useState } from "react";
import { Link } from "react-router-dom";

import { PageHeader } from "@/components/AppShell";
import { IconChevronRight, IconStore } from "@/components/icons";
import { TrainingCalendar } from "@/components/TrainingCalendar";
import { Badge, Button, EmptyState, ErrorState, LoadingList, Segmented } from "@/components/ui";
import { useCurrentUser } from "@/lib/auth";
import { shortDate } from "@/lib/dates";
import { useMesocycles, useMesocyclesWithSessions } from "@/lib/queries";

type Vista = "lista" | "calendario";

export default function Mesocycles() {
  const user = useCurrentUser();
  const { data, isPending, error, refetch } = useMesocycles(user.id);
  const [vista, setVista] = useState<Vista>("lista");

  // Activos primero, y dentro de cada grupo el más reciente arriba
  const mesociclos = [...(data ?? [])].sort((a, b) => {
    if (a.is_active !== b.is_active) return a.is_active ? -1 : 1;
    return b.start_date.localeCompare(a.start_date);
  });

  return (
    <>
      <PageHeader title="Mis entrenos" subtitle="Todos tus mesociclos y planes" />

      {isPending && <LoadingList rows={3} />}
      {!isPending && error && <ErrorState error={error} onRetry={() => void refetch()} />}

      {!isPending && !error && mesociclos.length === 0 && (
        <EmptyState
          icon={<IconStore className="h-10 w-10" />}
          title="Sin mesociclos todavía"
          action={
            <Link to="/planes">
              <Button>Ver planes</Button>
            </Link>
          }
        >
          Cuando tu coach te programe una rutina —o cuando adquieras un plan— aparecerá aquí.
        </EmptyState>
      )}

      {!isPending && !error && mesociclos.length > 0 && (
        <>
          <div className="mb-4">
            <Segmented
              options={[
                { value: "lista", label: "Lista" },
                { value: "calendario", label: "Calendario" },
              ]}
              value={vista}
              onChange={setVista}
            />
          </div>

          {vista === "lista" && (
            <div className="space-y-3">
              {mesociclos.map((mesocycle) => (
                <Link
                  key={mesocycle.id}
                  to={`/entrenos/${mesocycle.id}`}
                  className="flex items-center gap-3 rounded-2xl border border-line bg-surface p-4 active:bg-surface-2"
                >
                  <div className="min-w-0 grow">
                    <div className="flex items-center gap-2">
                      <span className="truncate font-bold">{mesocycle.name ?? "Mi rutina"}</span>
                      {mesocycle.is_active ? <Badge tone="done">Activo</Badge> : <Badge>Finalizado</Badge>}
                    </div>
                    <p className="mt-1 text-sm text-muted">
                      {mesocycle.discipline} · desde {shortDate(mesocycle.start_date)}
                      {mesocycle.end_date ? ` hasta ${shortDate(mesocycle.end_date)}` : ""}
                    </p>
                  </div>
                  <IconChevronRight className="h-5 w-5 shrink-0 text-muted" />
                </Link>
              ))}
            </div>
          )}

          {vista === "calendario" && <CalendarioEntrenos userId={user.id} />}
        </>
      )}
    </>
  );
}

function CalendarioEntrenos({ userId }: { userId: string }) {
  const { sessions, isPending, error } = useMesocyclesWithSessions(userId);

  if (isPending) return <LoadingList rows={3} />;
  if (error) return <ErrorState error={error} />;
  return <TrainingCalendar sessions={sessions} />;
}
