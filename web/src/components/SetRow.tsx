import { useState } from "react";

import { BarbellPlates } from "@/components/BarbellPlates";
import { IconCheck, IconDumbbell, IconTrash } from "@/components/icons";
import { Spinner, Stepper, cx } from "@/components/ui";
import { useLogSet } from "@/lib/queries";
import { isSetLogged, loadLabel } from "@/lib/sessions";
import { formatWeight, useWeightUnit, WeightStepper } from "@/lib/units";
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
  const unit = useWeightUnit();

  const [editing, setEditing] = useState(false);
  const [reps, setReps] = useState(set.actual_reps ?? set.prescribed_reps ?? 0);
  const [weight, setWeight] = useState(set.actual_weight ?? set.prescribed_weight ?? 0);
  const [showPlates, setShowPlates] = useState(false);

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

  // Deshace un registro hecho sin querer: manda null (no 0) para que la serie vuelva a
  // "pendiente" de verdad, no a "0 reps a 0 kg" (isSetLogged distingue null de 0).
  function undo() {
    logSet.mutate({ mesocycleId, setId: set.id, actual_reps: null, actual_weight: null });
  }

  if (!expanded) {
    return (
      <div className="flex w-full items-center gap-2 rounded-xl bg-done-soft/60 px-3 py-2.5">
        <button
          type="button"
          disabled={readOnly}
          onClick={() => setEditing(true)}
          className="flex grow items-center gap-3 text-left"
        >
          <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-done text-ink">
            <IconCheck className="h-3.5 w-3.5" />
          </span>
          <span className="shrink-0 text-sm font-semibold whitespace-nowrap text-muted">Serie {index}</span>
          <span className="min-w-0 grow truncate text-right text-sm font-bold tabular-nums">
            {set.actual_reps} reps
            {set.actual_weight ? ` · ${formatWeight(set.actual_weight, unit)}` : ""}
          </span>
        </button>
        <button
          type="button"
          disabled={readOnly || logSet.isPending}
          onClick={undo}
          aria-label={`Deshacer registro de la serie ${index}`}
          className="shrink-0 rounded-lg p-1.5 text-muted active:bg-danger/10 active:text-danger disabled:opacity-40"
        >
          <IconTrash className="h-4 w-4" />
        </button>
      </div>
    );
  }

  return (
    <div className="rounded-xl bg-surface-2/60 p-3">
      {/* El objetivo va en su propia línea: junto a "Serie N" no cabe en un teléfono y partía
          "Serie 1" en dos renglones. */}
      <div className="mb-2">
        <span className="text-sm font-semibold">Serie {index}</span>
        <p className="text-xs text-muted">
          Objetivo: {set.prescribed_reps} reps @ {loadLabel(set, unit)}
          {set.rpe ? ` · RPE ${set.rpe}` : ""}
        </p>
      </div>

      {/* Los dos contadores comparten la fila completa (con el ✓ al lado no quedaba ancho para
          "148.8 lb" entre los botones − y +); el ✓ va debajo, a todo el ancho. */}
      <div className="grid grid-cols-2 gap-2">
        <Stepper value={reps} onChange={setReps} min={0} max={200} suffix="reps" compact />
        <WeightStepper valueKg={weight} onChangeKg={setWeight} compact />
      </div>
      <button
        type="button"
        aria-label={`Registrar serie ${index}`}
        disabled={readOnly || logSet.isPending}
        onClick={save}
        className={cx(
          "mt-2 flex h-11 w-full items-center justify-center gap-2 rounded-xl text-sm font-bold",
          "bg-done text-ink active:bg-done/85 disabled:opacity-50",
        )}
      >
        {logSet.isPending ? <Spinner className="h-5 w-5" /> : <IconCheck className="h-5 w-5" />}
        Registrar serie
      </button>

      <button
        type="button"
        onClick={() => setShowPlates((v) => !v)}
        className="mt-2 inline-flex items-center gap-1.5 text-xs font-semibold text-brand"
      >
        <IconDumbbell className="h-3.5 w-3.5" />
        {showPlates ? "Ocultar discos" : "Ver discos para la barra"}
      </button>
      {showPlates && <BarbellPlates weightKg={weight} />}

      {logSet.isError && (
        <p className="mt-2 text-xs font-medium text-danger">
          No se pudo guardar. Revisa tu conexión y vuelve a tocar ✓.
        </p>
      )}
    </div>
  );
}
