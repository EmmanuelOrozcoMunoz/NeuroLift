import { useState } from "react";
import type { ReactNode } from "react";

import { BlockSelect } from "@/components/BlockSelect";
import { CoachNoteField } from "@/components/CoachNote";
import { IconTrash } from "@/components/icons";
import { Button, Field, Segmented, Stepper } from "@/components/ui";
import { conNumeroDeSeries, esUniforme } from "@/lib/exerciseDraft";
import type { ExerciseDraft, PesosWod, SerieDraft, TipoCarga } from "@/lib/exerciseDraft";
import { useWeightUnit, WeightStepper } from "@/lib/units";

/** Estado de un formulario de ejercicio: el borrador completo y una función para cambiarle
 *  solo lo que cambió. `inicial` se evalúa una vez. */
export function useExerciseDraft(inicial: () => ExerciseDraft) {
  const [draft, setDraft] = useState(inicial);
  const cambiar = (cambios: Partial<ExerciseDraft>) => setDraft((d) => ({ ...d, ...cambios }));
  return [draft, cambiar, setDraft] as const;
}

const ETIQUETA_TIPO: Record<TipoCarga, (unit: string) => string> = {
  kg: (unit) => `${unit === "lb" ? "Lb" : "Kg"} fijos`,
  porcentaje: () => "% de 1RM",
  libre: () => "Sin carga",
};

/** Cómo se editan las series:
 *  - "uniforme": «N series × R reps» con una sola carga (todas las series iguales).
 *  - "porSerie": una fila por serie con sus repeticiones y su carga, como en la pantalla de
 *    registro del atleta; sirve para rampas como 50 %×3, 60 %×3, 70 %×1… */
export type ModoSeries = "uniforme" | "porSerie";

/**
 * Los campos que el coach llena para un ejercicio: nombre, bloque, series, carga y nota para el
 * atleta. Lo comparten el editor de sesión, el de plan y los dos del programa de grupo (cada uno
 * pone su propio botón y arma su petición con lib/exerciseDraft.ts).
 *
 * - `tipos`: qué formas de prescribir la carga ofrece ese formulario (y en qué orden).
 * - `modo`: uniforme o serie por serie (ver ModoSeries).
 * - `cargaAlternativa`: reemplaza la carga (p. ej. los pesos del WOD en metcon).
 * - `avisoCarga`: texto pequeño bajo la carga.
 */
export function ExerciseFormFields({
  draft,
  onChange,
  tipos,
  modo = "uniforme",
  cargaAlternativa,
  avisoCarga,
}: {
  draft: ExerciseDraft;
  onChange: (cambios: Partial<ExerciseDraft>) => void;
  tipos: TipoCarga[];
  modo?: ModoSeries;
  cargaAlternativa?: ReactNode;
  avisoCarga?: string;
}) {
  const unit = useWeightUnit();
  const porSerie = modo === "porSerie" && !cargaAlternativa;

  /** Cambia la fila `i`, o todas si `i` es null (modo uniforme). */
  function cambiarFila(i: number | null, cambios: Partial<SerieDraft>) {
    onChange({ filas: draft.filas.map((f, j) => (i === null || i === j ? { ...f, ...cambios } : f)) });
  }

  const primera = draft.filas[0];

  return (
    <>
      <Field label="Ejercicio" value={draft.name} onChange={(e) => onChange({ name: e.target.value })} className="mb-3" />
      <BlockSelect value={draft.block} onChange={(block) => onChange({ block })} />

      {!porSerie && (
        <div className="grid grid-cols-2 gap-3">
          <div>
            <span className="mb-1.5 block text-xs font-medium text-muted">Series</span>
            <Stepper
              value={draft.filas.length}
              onChange={(n) => onChange({ filas: conNumeroDeSeries(draft.filas, n) })}
              min={1}
              max={20}
              compact
            />
          </div>
          <div>
            <span className="mb-1.5 block text-xs font-medium text-muted">Reps</span>
            <Stepper value={primera.reps} onChange={(reps) => cambiarFila(null, { reps })} min={1} max={100} compact />
          </div>
          <div>
            <span className="mb-1.5 block text-xs font-medium text-muted">RPE</span>
            <Stepper value={draft.rpe} onChange={(rpe) => onChange({ rpe })} min={0} max={10} compact />
          </div>
        </div>
      )}

      {cargaAlternativa ?? (
        <div className="mt-3 border-t border-line pt-3">
          <span className="mb-1.5 block text-xs font-medium text-muted">Carga</span>
          <Segmented<TipoCarga>
            value={draft.tipo}
            onChange={(tipo) => onChange({ tipo })}
            options={tipos.map((tipo) => ({ value: tipo, label: ETIQUETA_TIPO[tipo](unit) }))}
          />
          {!porSerie && draft.tipo === "porcentaje" && (
            <div className="mt-2">
              <span className="mb-1.5 block text-xs font-medium text-muted">Porcentaje (%)</span>
              <Stepper
                value={primera.porcentaje}
                onChange={(porcentaje) => cambiarFila(null, { porcentaje })}
                step={5}
                min={0}
                max={150}
                compact
              />
            </div>
          )}
          {!porSerie && draft.tipo === "kg" && (
            <div className="mt-2">
              <span className="mb-1.5 block text-xs font-medium text-muted">Peso ({unit})</span>
              <WeightStepper valueKg={primera.weight} onChangeKg={(weight) => cambiarFila(null, { weight })} compact />
            </div>
          )}
          {draft.tipo === "porcentaje" && (
            <Field
              label="1RM de referencia (opcional)"
              placeholder="Ej. Back Squat — vacío usa el mismo ejercicio"
              value={draft.referencia}
              onChange={(e) => onChange({ referencia: e.target.value })}
              className="mt-2"
            />
          )}
          {avisoCarga && <p className="mt-2 text-xs text-muted">{avisoCarga}</p>}
        </div>
      )}

      {porSerie && (
        <div className="mt-3 border-t border-line pt-3">
          <div className="mb-2 flex items-center justify-between gap-3">
            <span className="text-xs font-medium text-muted">Series ({draft.filas.length})</span>
            <div className="w-32">
              <Stepper value={draft.rpe} onChange={(rpe) => onChange({ rpe })} min={0} max={10} suffix="RPE" compact />
            </div>
          </div>

          <div className="space-y-2">
            {draft.filas.map((fila, i) => (
              <FilaDeSerie
                key={i}
                numero={i + 1}
                fila={fila}
                tipo={draft.tipo}
                puedeQuitar={draft.filas.length > 1}
                onChange={(cambios) => cambiarFila(i, cambios)}
                onQuitar={() => onChange({ filas: draft.filas.filter((_, j) => j !== i) })}
              />
            ))}
          </div>

          <div className="mt-3 flex flex-wrap gap-2">
            <Button
              variant="secondary"
              onClick={() => onChange({ filas: conNumeroDeSeries(draft.filas, draft.filas.length + 1) })}
            >
              + Añadir serie
            </Button>
            {!esUniforme(draft) && (
              <Button
                variant="ghost"
                onClick={() => onChange({ filas: draft.filas.map(() => ({ ...draft.filas[0] })) })}
              >
                Igualar todas a la serie 1
              </Button>
            )}
          </div>
        </div>
      )}

      <CoachNoteField value={draft.nota} onChange={(nota) => onChange({ nota })} />
    </>
  );
}

/** Una serie: repeticiones y carga con los mismos controles que la pantalla de registro. */
function FilaDeSerie({
  numero,
  fila,
  tipo,
  puedeQuitar,
  onChange,
  onQuitar,
}: {
  numero: number;
  fila: SerieDraft;
  tipo: TipoCarga;
  puedeQuitar: boolean;
  onChange: (cambios: Partial<SerieDraft>) => void;
  onQuitar: () => void;
}) {
  return (
    <div className="rounded-2xl bg-surface-2 p-3">
      <div className="mb-2 flex items-center justify-between">
        <span className="font-semibold">Serie {numero}</span>
        {puedeQuitar && (
          <button
            type="button"
            aria-label={`Quitar la serie ${numero}`}
            onClick={onQuitar}
            className="rounded-lg p-1.5 text-danger active:bg-danger/10"
          >
            <IconTrash className="h-4 w-4" />
          </button>
        )}
      </div>
      <div className={tipo === "libre" ? "" : "grid grid-cols-2 gap-2"}>
        <Stepper value={fila.reps} onChange={(reps) => onChange({ reps })} min={1} max={100} suffix="reps" compact />
        {tipo === "porcentaje" && (
          <Stepper
            value={fila.porcentaje}
            onChange={(porcentaje) => onChange({ porcentaje })}
            step={5}
            min={0}
            max={150}
            suffix="%"
            compact
          />
        )}
        {tipo === "kg" && (
          <WeightStepper valueKg={fila.weight} onChangeKg={(weight) => onChange({ weight })} compact />
        )}
      </div>
    </div>
  );
}

const CAMPOS_WOD: { clave: keyof PesosWod; etiqueta: string }[] = [
  { clave: "rxMale", etiqueta: "RX Hombres" },
  { clave: "rxFemale", etiqueta: "RX Mujeres" },
  { clave: "scaledMale", etiqueta: "Scaled Hombres" },
  { clave: "scaledFemale", etiqueta: "Scaled Mujeres" },
];

/** Reemplaza la carga en un bloque metcon: un peso por categoría y género. */
export function PesosWodFields({
  wod,
  onChange,
}: {
  wod: PesosWod;
  onChange: (wod: PesosWod) => void;
}) {
  const unit = useWeightUnit();
  return (
    <div className="mt-3 border-t border-line pt-3">
      <p className="mb-2 text-xs font-medium text-muted">Pesos del WOD ({unit}) — por categoría y género</p>
      <div className="grid grid-cols-2 gap-3">
        {CAMPOS_WOD.map(({ clave, etiqueta }) => (
          <div key={clave}>
            <span className="mb-1 block text-[11px] text-muted">{etiqueta}</span>
            <WeightStepper valueKg={wod[clave]} onChangeKg={(kg) => onChange({ ...wod, [clave]: kg })} compact />
          </div>
        ))}
      </div>
    </div>
  );
}
