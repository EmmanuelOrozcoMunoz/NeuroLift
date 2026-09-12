import { formatSeconds } from "@/lib/dates";
import type { WodFormat } from "@/lib/types";

export const WOD_FORMAT_LABELS: Record<WodFormat, string> = {
  for_time: "Por tiempo",
  amrap: "AMRAP",
  emom: "EMOM",
  "1rm": "1RM",
};

export const WOD_FORMAT_OPTIONS: { value: WodFormat; label: string; hint: string }[] = [
  { value: "for_time", label: "Por tiempo", hint: "Menor tiempo = mejor" },
  { value: "amrap", label: "AMRAP", hint: "Más rondas/reps = mejor" },
  { value: "emom", label: "EMOM", hint: "Cumplir el ritmo cada intervalo" },
  { value: "1rm", label: "1RM", hint: "Peso máximo levantado" },
];

/** Campos mínimos que necesita formatWodResult — TrainingSession y RecentSessionSummary
 *  comparten esta forma exacta, así que sirve para ambos sin acoplarse a ninguno. */
export interface WodResultFields {
  wod_format: WodFormat | null;
  wod_time_seconds: number | null;
  wod_rounds: number | null;
  wod_extra_reps: number | null;
  wod_emom_completed: boolean | null;
}

/** "Por tiempo: 12:34" / "AMRAP: 5 rondas + 12 reps" / "EMOM: cumplido ✓" / "1RM: 100 kg" —
 *  mismo criterio que _format_wod_summary en el backend. `actualWeights` solo se usa para
 *  formato "1rm" (el peso máximo REAL logueado en esa sesión); pásalo vacío para los demás. */
export function formatWodResult(session: WodResultFields, actualWeights: number[] = []): string | null {
  if (!session.wod_format) return null;

  if (session.wod_format === "for_time" && session.wod_time_seconds != null) {
    return `Por tiempo: ${formatSeconds(session.wod_time_seconds)}`;
  }
  if (session.wod_format === "amrap" && (session.wod_rounds != null || session.wod_extra_reps != null)) {
    const rondas = session.wod_rounds ?? 0;
    const reps = session.wod_extra_reps ?? 0;
    return reps ? `AMRAP: ${rondas} rondas + ${reps} reps` : `AMRAP: ${rondas} rondas`;
  }
  if (session.wod_format === "emom" && session.wod_emom_completed != null) {
    return session.wod_emom_completed ? "EMOM: cumplido ✓" : "EMOM: no completó ✗";
  }
  if (session.wod_format === "1rm" && actualWeights.length > 0) {
    return `1RM: ${Math.max(...actualWeights)} kg`;
  }
  return null;
}
