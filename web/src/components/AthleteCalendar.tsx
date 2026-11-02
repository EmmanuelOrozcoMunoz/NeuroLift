import { useState } from "react";
import { useNavigate } from "react-router-dom";

import { PROGRAMA_DIARIO } from "@/components/GroupCalendar";
import { TrainingCalendar } from "@/components/TrainingCalendar";
import { Button, ErrorState, LoadingList, Sheet } from "@/components/ui";
import { useCreateAthleteDay } from "@/lib/coachQueries";
import { longDate } from "@/lib/dates";
import { useMesocycles, useMesocyclesWithSessions } from "@/lib/queries";

function capitalizar(texto: string): string {
  return texto.charAt(0).toUpperCase() + texto.slice(1);
}

/** Calendario de UN atleta del coach: los días que tiene algo programado (de cualquier mesociclo) quedan
 *  marcados. Tocar un día abre una hoja con lo que hay ese día y, si el día no está en su "Programación
 *  diaria", un botón para programarlo sin armar un mesociclo. Es el equivalente, para un atleta suelto, del
 *  calendario de un grupo (ver GroupCalendar). */
export function AthleteCalendar({ athleteId, onError }: { athleteId: string; onError: (message: string) => void }) {
  const navigate = useNavigate();
  const { sessions, isPending, error } = useMesocyclesWithSessions(athleteId);
  const mesocycles = useMesocycles(athleteId);
  const createDay = useCreateAthleteDay(athleteId);
  const [dia, setDia] = useState<string | null>(null);

  if (isPending) return <LoadingList rows={2} />;
  if (error) return <ErrorState error={error} />;

  const nombreDe = (mesocycleId: string) => mesocycles.data?.find((m) => m.id === mesocycleId)?.name ?? "Rutina";
  const sesionesDelDia = dia ? sessions.filter((s) => s.scheduled_date === dia) : [];
  const enElDiario = sesionesDelDia.some((s) => nombreDe(s.mesocycle_id) === PROGRAMA_DIARIO);

  function abrir(mesocycleId: string, sessionId: string) {
    navigate(`/coach/mesociclos/${mesocycleId}/sesion/${sessionId}`);
  }

  function programar() {
    if (!dia) return;
    createDay.mutate(dia, {
      onSuccess: (r) => {
        setDia(null);
        abrir(r.mesocycle_id, r.session_id);
      },
      onError: (err) => onError(err instanceof Error ? err.message : "No se pudo programar el día."),
    });
  }

  return (
    <>
      <TrainingCalendar sessions={sessions} onDayTap={setDia} />
      <p className="mt-2 text-center text-xs text-muted">Toca un día para programarlo o editarlo.</p>

      <Sheet open={dia !== null} onClose={() => setDia(null)} title={dia ? capitalizar(longDate(dia)) : ""}>
        <div className="space-y-3 pb-4">
          {sesionesDelDia.length > 0 && (
            <div className="space-y-2">
              <p className="text-xs font-semibold tracking-wide text-muted uppercase">Ya programado en</p>
              {sesionesDelDia.map((sesion) => (
                <button
                  key={sesion.id}
                  type="button"
                  onClick={() => abrir(sesion.mesocycle_id, sesion.id)}
                  className="w-full rounded-xl border border-line bg-surface-2 px-4 py-3 text-left font-semibold active:bg-line"
                >
                  {nombreDe(sesion.mesocycle_id)}
                  <span className="block text-xs font-normal text-muted">Abrir y editar este día</span>
                </button>
              ))}
            </div>
          )}

          {!enElDiario && (
            <>
              <Button full loading={createDay.isPending} onClick={programar}>
                {sesionesDelDia.length > 0 ? "Programar un día aparte" : "Programar este día"}
              </Button>
              <p className="text-center text-xs text-muted">
                Se crea el día en «{PROGRAMA_DIARIO}» de este atleta y lo escribes ahí, bloque por bloque.
              </p>
            </>
          )}
        </div>
      </Sheet>
    </>
  );
}
