import type { ExerciseGroup } from "@/lib/sessions";

/** Cómo se prescribe la carga: kg fijos, % de 1RM (el backend lo calcula con las marcas ya
 *  registradas del atleta), o sin carga. Es una sola por ejercicio; cada serie pone su valor. */
export type TipoCarga = "kg" | "porcentaje" | "libre";

/** Pesos del WOD por categoría y género (solo bloque metcon, solo en programas de grupo). */
export interface PesosWod {
  rxMale: number;
  rxFemale: number;
  scaledMale: number;
  scaledFemale: number;
}

/** Una serie: sus repeticiones y su carga (kg y % se guardan por separado para no perder el
 *  valor al cambiar de tipo de carga). */
export interface SerieDraft {
  reps: number;
  weight: number;
  porcentaje: number;
}

/** Todo lo que el coach llena para UN ejercicio, en cualquiera de los formularios. */
export interface ExerciseDraft {
  name: string;
  /** Una fila por serie, en orden: permite rampas como 50 %×3, 60 %×3, 70 %×1… */
  filas: SerieDraft[];
  /** 0 = sin RPE. Igual para todas las series del ejercicio. */
  rpe: number;
  tipo: TipoCarga;
  referencia: string;
  /** "" = sin bloque */
  block: string;
  nota: string;
  wod: PesosWod;
}

const SERIE_NUEVA: SerieDraft = { reps: 8, weight: 0, porcentaje: 75 };

/** Valores de un ejercicio nuevo: `series` filas iguales, con `reps`, `weight` y `porcentaje`. */
export function nuevoDraft(
  sobre: Partial<Omit<ExerciseDraft, "filas">> & Partial<SerieDraft> & { series?: number } = {},
): ExerciseDraft {
  const { series = 3, reps, weight, porcentaje, ...resto } = sobre;
  const fila: SerieDraft = {
    reps: reps ?? SERIE_NUEVA.reps,
    weight: weight ?? SERIE_NUEVA.weight,
    porcentaje: porcentaje ?? SERIE_NUEVA.porcentaje,
  };
  return {
    name: "",
    filas: Array.from({ length: series }, () => ({ ...fila })),
    rpe: 7,
    tipo: "kg",
    referencia: "",
    block: "",
    nota: "",
    wod: { rxMale: 0, rxFemale: 0, scaledMale: 0, scaledFemale: 0 },
    ...resto,
  };
}

/** Parte de las series ya guardadas de un ejercicio, una fila por serie. `permiteLibre`: los
 *  formularios que ofrecen "Sin carga" distinguen una serie sin peso de una de kg. */
export function draftDeEjercicio(group: ExerciseGroup, permiteLibre: boolean): ExerciseDraft {
  const primera = group.sets[0];
  const base = nuevoDraft({
    name: group.name,
    rpe: primera.rpe ?? 0,
    tipo: primera.prescribed_percentage ? "porcentaje" : permiteLibre && !primera.prescribed_weight ? "libre" : "kg",
    referencia: primera.reference_exercise ?? "",
    block: primera.block ?? "",
    nota: group.sets.find((s) => s.coach_note)?.coach_note ?? "",
  });
  return {
    ...base,
    filas: group.sets.map((s) => ({
      reps: s.prescribed_reps,
      weight: s.prescribed_weight ?? 0,
      porcentaje: s.prescribed_percentage ?? SERIE_NUEVA.porcentaje,
    })),
  };
}

export const esMetcon = (d: ExerciseDraft) => d.block === "metcon";

/** ¿Todas las series son iguales? (entonces se puede editar como "N series × R reps") */
export function esUniforme(d: ExerciseDraft): boolean {
  const [primera, ...resto] = d.filas;
  return resto.every((f) => f.reps === primera.reps && f.weight === primera.weight && f.porcentaje === primera.porcentaje);
}

/** Cambia el número de series: las nuevas copian la última; si sobran, se quitan del final. */
export function conNumeroDeSeries(filas: SerieDraft[], n: number): SerieDraft[] {
  if (n <= filas.length) return filas.slice(0, Math.max(1, n));
  const ultima = filas[filas.length - 1] ?? SERIE_NUEVA;
  return [...filas, ...Array.from({ length: n - filas.length }, () => ({ ...ultima }))];
}

/** La carga de UNA serie tal como la espera el backend. En metcon la carga va por
 *  categoría/género (ver `pesosWodParaEnviar`), así que aquí queda vacía. */
export function cargaDeFila(d: ExerciseDraft, fila: SerieDraft, metcon = false) {
  const referencia = d.referencia.trim();
  return {
    prescribed_weight: !metcon && d.tipo === "kg" && fila.weight > 0 ? fila.weight : null,
    prescribed_percentage: !metcon && d.tipo === "porcentaje" ? fila.porcentaje : null,
    reference_exercise: !metcon && d.tipo === "porcentaje" && referencia ? referencia : null,
  };
}

/** Carga del ejercicio cuando todas las series son iguales: la de la primera fila. */
export function cargaParaEnviar(d: ExerciseDraft, metcon = false) {
  return cargaDeFila(d, d.filas[0], metcon);
}

export function pesosWodParaEnviar(d: ExerciseDraft, metcon: boolean) {
  return {
    prescribed_weight_rx_male: metcon && d.wod.rxMale > 0 ? d.wod.rxMale : null,
    prescribed_weight_rx_female: metcon && d.wod.rxFemale > 0 ? d.wod.rxFemale : null,
    prescribed_weight_scaled_male: metcon && d.wod.scaledMale > 0 ? d.wod.scaledMale : null,
    prescribed_weight_scaled_female: metcon && d.wod.scaledFemale > 0 ? d.wod.scaledFemale : null,
  };
}

/** RPE, bloque y carga que comparten todos los cuerpos de petición (series iguales). */
export function camposComunes(d: ExerciseDraft, metcon = false) {
  return {
    rpe: d.rpe > 0 ? d.rpe : null,
    block: d.block || null,
    ...cargaParaEnviar(d, metcon),
  };
}

/** El cuerpo completo de la serie `i`: sus repeticiones y su propia carga. */
export function camposDeFila(d: ExerciseDraft, i: number, metcon = false) {
  const fila = d.filas[i];
  return {
    prescribed_reps: fila.reps,
    rpe: d.rpe > 0 ? d.rpe : null,
    block: d.block || null,
    ...cargaDeFila(d, fila, metcon),
  };
}

/** Identifica los DATOS GUARDADOS de un ejercicio (sus series y lo que tienen). Se usa como `key`
 *  de su tarjeta de edición: cuando el servidor devuelve otras series (p. ej. llegan las que se
 *  estaban creando), la tarjeta se reinicia con ellas en vez de quedarse con un borrador viejo que,
 *  al guardar, borraría las series que "faltan". */
export function firmaDeEjercicio(group: ExerciseGroup): string {
  const series = group.sets
    .map((s) =>
      [s.id, s.prescribed_reps, s.prescribed_weight, s.prescribed_percentage, s.reference_exercise, s.rpe, s.block, s.coach_note].join(":"),
    )
    .join(",");
  return `${group.name}|${series}`;
}
