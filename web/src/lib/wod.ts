import { formatSeconds } from "@/lib/dates";
import { formatWeight } from "@/lib/units";
import type { WeightUnit, WodFormat } from "@/lib/types";

export const WOD_FORMAT_LABELS: Record<WodFormat, string> = {
  for_time: "Por tiempo",
  amrap: "AMRAP (rondas y reps)",
  amrap_reps: "AMRAP (solo reps)",
  emom: "EMOM",
  tabata: "Tabata",
  "1rm": "Peso",
  calories: "Calorías",
  distance: "Distancia (m)",
  watts: "Vatios (W)",
};

type WodFormatOption = { value: WodFormat; label: string; hint: string };

/** Los 4 protocolos "clásicos" con reloj propio — se muestran primero, como plantillas
 *  rápidas (mismo criterio que un picker de cronómetro: AMRAP/EMOM/TABATA/FOR TIME). */
export const WOD_TIMER_TEMPLATES: WodFormatOption[] = [
  { value: "for_time", label: "Por tiempo", hint: "Menor tiempo = mejor" },
  { value: "amrap", label: "AMRAP (rondas y reps)", hint: "Más rondas/reps = mejor" },
  { value: "emom", label: "EMOM", hint: "1 ronda por minuto — cumplir el ritmo" },
  { value: "tabata", label: "Tabata", hint: "Reps de tu peor ronda = mejor" },
];

/** Formas de puntuar que no dependen de un reloj con protocolo fijo — el coach elige la
 *  unidad y, si aplica, un time cap propio. */
export const WOD_OTHER_SCORE_TYPES: WodFormatOption[] = [
  { value: "amrap_reps", label: "AMRAP (solo reps)", hint: "Más reps totales = mejor" },
  { value: "1rm", label: "Peso", hint: "Mayor peso = mejor" },
  { value: "calories", label: "Calorías", hint: "Más calorías = mejor" },
  { value: "distance", label: "Distancia (m)", hint: "Mayor distancia = mejor" },
  { value: "watts", label: "Vatios (W)", hint: "Mayor potencia = mejor" },
];

export const WOD_FORMAT_OPTIONS: WodFormatOption[] = [...WOD_TIMER_TEMPLATES, ...WOD_OTHER_SCORE_TYPES];

/** Formatos donde el coach puede fijar un timer (cap duro para "for_time", duración total para
 *  "emom" — 1 ronda por minuto —, duración de la ventana para los demás) — tabata/1rm no lo
 *  necesitan (protocolo fijo o resultado sin reloj). */
export const WOD_FORMATS_WITH_TIME_CAP: WodFormat[] = [
  "for_time",
  "amrap",
  "amrap_reps",
  "emom",
  "calories",
  "distance",
  "watts",
];

export const wodFormatUsesTimeCap = (format: WodFormat | null): boolean =>
  format != null && WOD_FORMATS_WITH_TIME_CAP.includes(format);

/** Campos mínimos que necesita formatWodResult — TrainingSession y RecentSessionSummary
 *  comparten esta forma exacta, así que sirve para ambos sin acoplarse a ninguno. */
export interface WodResultFields {
  wod_format: WodFormat | null;
  wod_time_seconds: number | null;
  wod_rounds: number | null;
  wod_extra_reps: number | null;
  wod_emom_completed: boolean | null;
  wod_calories: number | null;
  wod_distance_meters: number | null;
  wod_watts: number | null;
}

/** "Por tiempo: 12:34" / "AMRAP: 5 rondas + 12 reps" / "AMRAP: 42 reps" / "EMOM: cumplido ✓" /
 *  "Peso: 100 kg" / "215 cal" / "1000 m" / "320 W" — mismo criterio que _format_wod_summary en
 *  el backend. `actualWeights` solo se usa para formato "1rm" (el peso máximo REAL logueado en
 *  esa sesión); pásalo vacío para los demás. */
export function formatWodResult(
  session: WodResultFields,
  actualWeights: number[] = [],
  unit: WeightUnit = "kg",
): string | null {
  if (!session.wod_format) return null;

  if (session.wod_format === "for_time" && session.wod_time_seconds != null) {
    return `Por tiempo: ${formatSeconds(session.wod_time_seconds)}`;
  }
  if (session.wod_format === "amrap" && (session.wod_rounds != null || session.wod_extra_reps != null)) {
    const rondas = session.wod_rounds ?? 0;
    const reps = session.wod_extra_reps ?? 0;
    return reps ? `AMRAP: ${rondas} rondas + ${reps} reps` : `AMRAP: ${rondas} rondas`;
  }
  if (session.wod_format === "amrap_reps" && session.wod_extra_reps != null) {
    return `AMRAP: ${session.wod_extra_reps} reps`;
  }
  if (session.wod_format === "tabata" && session.wod_extra_reps != null) {
    return `Tabata: ${session.wod_extra_reps} reps (peor ronda)`;
  }
  if (session.wod_format === "emom" && session.wod_emom_completed != null) {
    return session.wod_emom_completed ? "EMOM: cumplido ✓" : "EMOM: no completó ✗";
  }
  if (session.wod_format === "1rm" && actualWeights.length > 0) {
    return `Peso: ${formatWeight(Math.max(...actualWeights), unit)}`;
  }
  if (session.wod_format === "calories" && session.wod_calories != null) {
    return `${session.wod_calories} cal`;
  }
  if (session.wod_format === "distance" && session.wod_distance_meters != null) {
    return `${session.wod_distance_meters} m`;
  }
  if (session.wod_format === "watts" && session.wod_watts != null) {
    return `${session.wod_watts} W`;
  }
  return null;
}
