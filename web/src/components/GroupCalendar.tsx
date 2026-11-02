import { useState } from "react";
import { useNavigate } from "react-router-dom";

import { TrainingCalendar } from "@/components/TrainingCalendar";
import type { CalendarSession } from "@/components/TrainingCalendar";
import { Button, Sheet } from "@/components/ui";
import { useCreateGroupDay } from "@/lib/coachQueries";
import { longDate } from "@/lib/dates";
import type { GroupMesocycleProgram } from "@/lib/types";

/** El programa donde caen los días que se programan uno por uno desde el calendario (ver
 *  services/groups.py:PROGRAMA_DIARIO_DEL_GRUPO en el backend). */
export const PROGRAMA_DIARIO = "Programación diaria";

function capitalizar(texto: string): string {
  return texto.charAt(0).toUpperCase() + texto.slice(1);
}

/** Calendario del grupo: los días con algo programado (de cualquier programa) quedan marcados. Tocar un
 *  día abre una hoja con lo que hay ese día y, si el día no está en la "Programación diaria", un botón para
 *  programarlo para todo el grupo sin armar un mesociclo. */
export function GroupCalendar({
  groupId,
  programs,
  onError,
}: {
  groupId: string;
  programs: GroupMesocycleProgram[];
  onError: (message: string) => void;
}) {
  const navigate = useNavigate();
  const createDay = useCreateGroupDay(groupId);
  const [dia, setDia] = useState<string | null>(null);

  // Un punto por cada fecha con sesión de algún programa (todos los miembros comparten las fechas)
  const sesiones: CalendarSession[] = programs.flatMap((programa) =>
    programa.session_dates.map((fecha) => ({
      id: `${programa.name}|${programa.start_date}|${fecha}`,
      mesocycle_id: programa.athletes[0]?.mesocycle_id ?? "",
      scheduled_date: fecha,
      status: "pending" as const,
    })),
  );

  function abrir(programa: { name: string; start_date: string }, fecha: string) {
    navigate(
      `/coach/grupos/${groupId}/programas/${encodeURIComponent(programa.name)}/${programa.start_date}?fecha=${fecha}`,
    );
  }

  const programasDelDia = dia ? programs.filter((p) => p.session_dates.includes(dia)) : [];
  const enElDiario = programasDelDia.some((p) => p.name === PROGRAMA_DIARIO);

  function programar() {
    if (!dia) return;
    createDay.mutate(dia, {
      onSuccess: (r) => {
        setDia(null);
        navigate(
          `/coach/grupos/${groupId}/programas/${encodeURIComponent(r.program_name)}/${r.program_start_date}?fecha=${r.scheduled_date}`,
        );
      },
      onError: (err) => onError(err instanceof Error ? err.message : "No se pudo programar el día."),
    });
  }

  return (
    <>
      <TrainingCalendar sessions={sesiones} onDayTap={setDia} />
      <p className="mt-2 text-center text-xs text-muted">Toca un día para programarlo o editarlo para todo el grupo.</p>

      <Sheet open={dia !== null} onClose={() => setDia(null)} title={dia ? capitalizar(longDate(dia)) : ""}>
        <div className="space-y-3 pb-4">
          {programasDelDia.length > 0 && (
            <div className="space-y-2">
              <p className="text-xs font-semibold tracking-wide text-muted uppercase">Ya programado en</p>
              {programasDelDia.map((programa) => (
                <button
                  key={`${programa.name}-${programa.start_date}`}
                  type="button"
                  onClick={() => dia && abrir(programa, dia)}
                  className="w-full rounded-xl border border-line bg-surface-2 px-4 py-3 text-left font-semibold active:bg-line"
                >
                  {programa.name}
                  <span className="block text-xs font-normal text-muted">Abrir y editar este día</span>
                </button>
              ))}
            </div>
          )}

          {!enElDiario && (
            <>
              <Button full loading={createDay.isPending} onClick={programar}>
                {programasDelDia.length > 0 ? "Programar un día aparte" : "Programar este día"}
              </Button>
              <p className="text-center text-xs text-muted">
                Se crea el día para todo el grupo en «{PROGRAMA_DIARIO}» y lo escribes ahí, bloque por bloque.
              </p>
            </>
          )}
        </div>
      </Sheet>
    </>
  );
}
