import { useState } from "react";

import { IconCheck } from "@/components/icons";
import { Spinner, Stepper, cx } from "@/components/ui";
import { formatKg } from "@/lib/dates";
import { useLogSet } from "@/lib/queries";
import { isSetLogged, loadLabel } from "@/lib/sessions";
import type { SetItem } from "@/lib/types";

/**
 * Una serie. Mientras no está registrada muestra los contadores; en cuanto se registra se
 * colapsa a una línea — así una sesión de 15 series no obliga a scrollear eternamente
 * conforme se va completando. Un toque en la línea vuelve a abrirla para corregir.
 */
export function SetRow({
  set,
  index,
  mesocycleId,
  readOnly = false,
}: {
  set: SetItem;
  index: number;
  mesocycleId: string;
  readOnly?: boolean;
}) {
  const logSet = useLogSet();
  const logged = isSetLogged(set);

  const [editing, setEditing] = useState(false);
  const [reps, setReps] = useState(set.actual_reps ?? set.prescribed_reps ?? 0);
  const [weight, setWeight] = useState(set.actual_weight ?? set.prescribed_weight ?? 0);

  const expanded = !logged || editing;

  function save() {
    logSet.mutate(
      { mesocycleId, setId: set.id, actual_reps: reps, actual_weight: weight },
      { onSuccess: () => setEditing(false) },
    );
    // La caché se actualiza de forma optimista, así que la fila puede colapsarse ya:
    // si el PUT falla de verdad, onError revierte y la fila vuelve a abrirse.
    setEditing(false);
  }

  if (!expanded) {
    return (
      <button
        type="button"
        disabled={readOnly}
        onClick={() => setEditing(true)}
        className="flex w-full items-center gap-3 rounded-xl bg-done-soft/60 px-3 py-2.5 text-left"
      >
        <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-done text-ink">
          <IconCheck className="h-3.5 w-3.5" />
        </span>
        <span className="text-sm font-semibold text-muted">Serie {index}</span>
        <span className="grow text-right text-sm font-bold tabular-nums">
          {set.actual_reps} reps
          {set.actual_weight ? ` · ${formatKg(set.actual_weight)} kg` : ""}
        </span>
      </button>
    );
  }

  return (
    <div className="rounded-xl bg-surface-2/60 p-3">
      <div className="mb-2 flex items-center justify-between gap-2">
        <span className="text-sm font-semibold">Serie {index}</span>
        <span className="truncate text-xs text-muted">
          Objetivo: {set.prescribed_reps} reps @ {loadLabel(set)}
          {set.rpe ? ` · RPE ${set.rpe}` : ""}
        </span>
      </div>

      <div className="flex items-center gap-2">
        <div className="grow">
          <Stepper value={reps} onChange={setReps} min={0} max={200} suffix="reps" compact />
        </div>
        <div className="grow">
          <Stepper value={weight} onChange={setWeight} step={2.5} min={0} max={1000} suffix="kg" compact />
        </div>
        <button
          type="button"
          aria-label={`Registrar serie ${index}`}
          disabled={readOnly || logSet.isPending}
          onClick={save}
          className={cx(
            "flex h-12 w-12 shrink-0 items-center justify-center rounded-xl",
            "bg-done text-ink active:bg-done/85 disabled:opacity-50",
          )}
        >
          {logSet.isPending ? <Spinner className="h-5 w-5" /> : <IconCheck className="h-6 w-6" />}
        </button>
      </div>

      {logSet.isError && (
        <p className="mt-2 text-xs font-medium text-danger">
          No se pudo guardar. Revisa tu conexión y vuelve a tocar ✓.
        </p>
      )}
    </div>
  );
}
