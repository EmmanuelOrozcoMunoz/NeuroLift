import { useState } from "react";
import type { ReactNode } from "react";

import { BlockSelect } from "@/components/BlockSelect";
import { CoachNoteField } from "@/components/CoachNote";
import { Field, Segmented, Stepper } from "@/components/ui";
import type { ExerciseDraft, PesosWod, TipoCarga } from "@/lib/exerciseDraft";
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

/**
 * Los campos que el coach llena para un ejercicio: nombre, bloque, series/reps/RPE, carga y nota
 * para el atleta. Lo comparten el editor de sesión, el de plan y los dos del programa de grupo
 * (cada uno pone su propio botón y arma su petición con lib/exerciseDraft.ts).
 *
 * - `tipos`: qué formas de prescribir la carga ofrece ese formulario (y en qué orden).
 * - `cargaAlternativa`: reemplaza el bloque de carga (p. ej. los pesos del WOD en metcon).
 * - `avisoCarga`: texto pequeño bajo la carga.
 */
export function ExerciseFormFields({
  draft,
  onChange,
  tipos,
  cargaAlternativa,
  avisoCarga,
}: {
  draft: ExerciseDraft;
  onChange: (cambios: Partial<ExerciseDraft>) => void;
  tipos: TipoCarga[];
  cargaAlternativa?: ReactNode;
  avisoCarga?: string;
}) {
  const unit = useWeightUnit();

  return (
    <>
      <Field label="Ejercicio" value={draft.name} onChange={(e) => onChange({ name: e.target.value })} className="mb-3" />
      <BlockSelect value={draft.block} onChange={(block) => onChange({ block })} />

      <div className="grid grid-cols-2 gap-3">
        <div>
          <span className="mb-1.5 block text-xs font-medium text-muted">Series</span>
          <Stepper value={draft.series} onChange={(series) => onChange({ series })} min={1} max={20} compact />
        </div>
        <div>
          <span className="mb-1.5 block text-xs font-medium text-muted">Reps</span>
          <Stepper value={draft.reps} onChange={(reps) => onChange({ reps })} min={1} max={100} compact />
        </div>
        <div>
          <span className="mb-1.5 block text-xs font-medium text-muted">RPE</span>
          <Stepper value={draft.rpe} onChange={(rpe) => onChange({ rpe })} min={0} max={10} compact />
        </div>
      </div>

      {cargaAlternativa ?? (
        <div className="mt-3 border-t border-line pt-3">
          <span className="mb-1.5 block text-xs font-medium text-muted">Carga</span>
          <Segmented<TipoCarga>
            value={draft.tipo}
            onChange={(tipo) => onChange({ tipo })}
            options={tipos.map((tipo) => ({ value: tipo, label: ETIQUETA_TIPO[tipo](unit) }))}
          />
          {draft.tipo === "porcentaje" && (
            <div className="mt-2">
              <span className="mb-1.5 block text-xs font-medium text-muted">Porcentaje (%)</span>
              <Stepper
                value={draft.porcentaje}
                onChange={(porcentaje) => onChange({ porcentaje })}
                step={5}
                min={0}
                max={150}
                compact
              />
            </div>
          )}
          {draft.tipo === "kg" && (
            <div className="mt-2">
              <span className="mb-1.5 block text-xs font-medium text-muted">Peso ({unit})</span>
              <WeightStepper valueKg={draft.weight} onChangeKg={(weight) => onChange({ weight })} compact />
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

      <CoachNoteField value={draft.nota} onChange={(nota) => onChange({ nota })} />
    </>
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
