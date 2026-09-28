import type { ExerciseGroup } from "@/lib/sessions";

/** Cómo se prescribe la carga: kg fijos, % de 1RM (el backend lo calcula con las marcas ya
 *  registradas del atleta), o sin carga. */
export type TipoCarga = "kg" | "porcentaje" | "libre";

/** Pesos del WOD por categoría y género (solo bloque metcon, solo en programas de grupo). */
export interface PesosWod {
  rxMale: number;
  rxFemale: number;
  scaledMale: number;
  scaledFemale: number;
}

/** Todo lo que el coach llena para UN ejercicio, en cualquiera de los formularios. */
export interface ExerciseDraft {
  name: string;
  series: number;
  reps: number;
  /** 0 = sin RPE */
  rpe: number;
  tipo: TipoCarga;
  weight: number;
  porcentaje: number;
  referencia: string;
  /** "" = sin bloque */
  block: string;
  nota: string;
  wod: PesosWod;
}

/** Valores de un ejercicio nuevo; cada formulario ajusta los que le corresponden. */
export function nuevoDraft(sobre: Partial<ExerciseDraft> = {}): ExerciseDraft {
  return {
    name: "",
    series: 3,
    reps: 8,
    rpe: 7,
    tipo: "kg",
    weight: 0,
    porcentaje: 75,
    referencia: "",
    block: "",
    nota: "",
    wod: { rxMale: 0, rxFemale: 0, scaledMale: 0, scaledFemale: 0 },
    ...sobre,
  };
}

/** Parte de las series ya guardadas de un ejercicio. `permiteLibre`: los formularios que ofrecen
 *  "Sin carga" distinguen una serie sin peso de una de kg; los demás la muestran como kg. */
export function draftDeEjercicio(group: ExerciseGroup, permiteLibre: boolean): ExerciseDraft {
  const primera = group.sets[0];
  const sinPeso = !primera.prescribed_weight;
  return nuevoDraft({
    name: group.name,
    series: group.sets.length,
    reps: primera.prescribed_reps,
    rpe: primera.rpe ?? 0,
    tipo: primera.prescribed_percentage ? "porcentaje" : permiteLibre && sinPeso ? "libre" : "kg",
    weight: primera.prescribed_weight ?? 0,
    porcentaje: primera.prescribed_percentage ?? 75,
    referencia: primera.reference_exercise ?? "",
    block: primera.block ?? "",
    nota: group.sets.find((s) => s.coach_note)?.coach_note ?? "",
  });
}

export const esMetcon = (d: ExerciseDraft) => d.block === "metcon";

/** Los campos de carga tal como los espera el backend. En metcon la carga va por categoría/género
 *  (ver `pesosWodParaEnviar`), así que aquí queda vacía. */
export function cargaParaEnviar(d: ExerciseDraft, metcon = false) {
  const referencia = d.referencia.trim();
  return {
    prescribed_weight: !metcon && d.tipo === "kg" && d.weight > 0 ? d.weight : null,
    prescribed_percentage: !metcon && d.tipo === "porcentaje" ? d.porcentaje : null,
    reference_exercise: !metcon && d.tipo === "porcentaje" && referencia ? referencia : null,
  };
}

export function pesosWodParaEnviar(d: ExerciseDraft, metcon: boolean) {
  return {
    prescribed_weight_rx_male: metcon && d.wod.rxMale > 0 ? d.wod.rxMale : null,
    prescribed_weight_rx_female: metcon && d.wod.rxFemale > 0 ? d.wod.rxFemale : null,
    prescribed_weight_scaled_male: metcon && d.wod.scaledMale > 0 ? d.wod.scaledMale : null,
    prescribed_weight_scaled_female: metcon && d.wod.scaledFemale > 0 ? d.wod.scaledFemale : null,
  };
}

/** RPE, bloque y carga: lo que comparten todos los cuerpos de petición. */
export function camposComunes(d: ExerciseDraft, metcon = false) {
  return {
    rpe: d.rpe > 0 ? d.rpe : null,
    block: d.block || null,
    ...cargaParaEnviar(d, metcon),
  };
}
