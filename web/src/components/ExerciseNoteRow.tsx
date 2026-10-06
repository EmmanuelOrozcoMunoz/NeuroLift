import { useState } from "react";

import { CoachNoteCallout } from "@/components/CoachNote";
import { IconCheck } from "@/components/icons";
import { SetRow } from "@/components/SetRow";
import { Spinner, cx } from "@/components/ui";
import { useLogSets } from "@/lib/queries";
import {
  coincideConLoProgramado,
  entradasComoProgramado,
  entradasParaDeshacer,
  estadoDelGrupo,
  groupSummary,
  resumenRegistrado,
} from "@/lib/sessions";
import type { ExerciseGroup } from "@/lib/sessions";
import { useWeightUnit } from "@/lib/units";

/**
 * Un ejercicio de la sesión como una línea de bloc de notas: nombre, lo programado y un ✓ para
 * tacharlo. El registro tiene dos formas:
 *
 *  - Normal: tocar el ✓ anota TODAS las series pendientes tal como estaban programadas (una sola
 *    petición). Tocarlo otra vez lo deshace, pero solo si lo anotado es justo lo programado: si el
 *    atleta registró otra cosa, el toque abre el registro avanzado en vez de borrarle sus números.
 *  - Avanzado: "Registro avanzado" despliega una fila por serie (SetRow) para anotar reps y peso
 *    reales de cada una.
 */
export function ExerciseNoteRow({
  grupo,
  mesocycleId,
  sessionId,
}: {
  grupo: ExerciseGroup;
  mesocycleId: string;
  sessionId: string;
}) {
  const unit = useWeightUnit();
  const logSets = useLogSets();
  const [avanzado, setAvanzado] = useState(false);

  const estado = estadoDelGrupo(grupo);
  const hecho = estado === "completo";
  const comoProgramado = hecho && coincideConLoProgramado(grupo);
  const anotadas = grupo.sets.filter((s) => s.actual_reps !== null && s.actual_reps !== undefined).length;

  function alTocarCheck() {
    if (hecho && !comoProgramado) {
      setAvanzado(true); // anotó otra cosa: no se la borramos de un toque
      return;
    }
    const entries = hecho ? entradasParaDeshacer(grupo) : entradasComoProgramado(grupo);
    if (entries.length > 0) logSets.mutate({ mesocycleId, sessionId, entries });
  }

  const rpe = grupo.sets.find((s) => s.rpe)?.rpe;
  const linea = hecho && !comoProgramado ? resumenRegistrado(grupo, unit) : groupSummary(grupo, unit);

  return (
    <li className="grid grid-cols-[3rem_1fr] items-start">
      <div className="flex justify-center pt-2.5">
        <button
          type="button"
          onClick={alTocarCheck}
          disabled={logSets.isPending}
          aria-pressed={hecho}
          aria-label={
            hecho && !comoProgramado
              ? `Editar lo registrado de ${grupo.name}`
              : hecho
                ? `Deshacer ${grupo.name}`
                : `Marcar ${grupo.name} como programado`
          }
          className={cx(
            "flex h-9 w-9 items-center justify-center rounded-full border-2 transition-colors disabled:opacity-60",
            hecho ? "border-done bg-done text-ink" : estado === "parcial" ? "border-warn text-warn" : "border-muted/60 text-transparent",
          )}
        >
          {logSets.isPending ? (
            <Spinner className="h-4 w-4" />
          ) : estado === "parcial" ? (
            <span className="text-[11px] leading-none font-bold tabular-nums">
              {anotadas}/{grupo.sets.length}
            </span>
          ) : (
            <IconCheck className="h-5 w-5" />
          )}
        </button>
      </div>

      <div className="min-w-0 py-3 pr-3 pl-3">
        <p className={cx("leading-tight font-bold", hecho && "text-muted line-through decoration-done/60")}>
          {grupo.name}
        </p>
        <p className="mt-0.5 text-sm text-muted tabular-nums">
          {linea}
          {rpe ? ` · RPE ${rpe}` : ""}
        </p>
        {hecho && comoProgramado && <p className="mt-0.5 text-xs font-semibold text-done">Hecho como estaba programado</p>}
        <CoachNoteCallout note={grupo.sets.find((st) => st.coach_note)?.coach_note} />

        <button
          type="button"
          onClick={() => setAvanzado((v) => !v)}
          aria-expanded={avanzado}
          className="mt-1.5 min-h-8 text-xs font-semibold text-brand"
        >
          {avanzado ? "Cerrar registro avanzado" : "Registro avanzado"}
        </button>

        {logSets.isError && (
          <p className="mt-1 text-xs font-medium text-danger">No se pudo guardar. Revisa tu conexión y vuelve a intentarlo.</p>
        )}

        {avanzado && (
          <div className="mt-2 space-y-2">
            {grupo.sets.map((set, indice) => (
              <SetRow key={set.id} set={set} index={indice + 1} mesocycleId={mesocycleId} />
            ))}
          </div>
        )}
      </div>
    </li>
  );
}
