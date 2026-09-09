import { formatKg, parseApiDate } from "@/lib/dates";
import type { SetItem, TrainingSession } from "@/lib/types";

/** Series de un mismo ejercicio, en el orden en que el coach las prescribió. */
export interface ExerciseGroup {
  name: string;
  sets: SetItem[];
}

/**
 * El backend no garantiza orden en la relación `sets` (no tiene order_by), así que se ordena
 * aquí por set_order antes de agrupar. Se agrupa por nombre de ejercicio conservando el orden
 * de aparición: así "Back Squat 4x5" se lee como un bloque y no como cuatro filas sueltas.
 */
export function groupSets(sets: SetItem[]): ExerciseGroup[] {
  const ordered = [...sets].sort((a, b) => a.set_order - b.set_order);
  const groups: ExerciseGroup[] = [];

  for (const set of ordered) {
    const name = set.exercise?.name ?? "Ejercicio";
    const last = groups.at(-1);
    if (last && last.name === name) {
      last.sets.push(set);
    } else {
      groups.push({ name, sets: [set] });
    }
  }

  return groups;
}

export function sortSessions(sessions: TrainingSession[]): TrainingSession[] {
  return [...sessions].sort(
    (a, b) => parseApiDate(a.scheduled_date).getTime() - parseApiDate(b.scheduled_date).getTime(),
  );
}

/**
 * Separa las sesiones "normales" de sus versiones adaptadas al tiempo. Una sesión adaptada
 * vive el mismo día que su original y apunta a ella con parent_session_id; la original nunca
 * se modifica, así que el atleta puede elegir cuál seguir.
 */
export function splitSessions(sessions: TrainingSession[]): {
  originals: TrainingSession[];
  adaptedByParent: Map<string, TrainingSession>;
} {
  const originals: TrainingSession[] = [];
  const adaptedByParent = new Map<string, TrainingSession>();

  for (const session of sessions) {
    if (session.parent_session_id) {
      adaptedByParent.set(session.parent_session_id, session);
    } else {
      originals.push(session);
    }
  }

  return { originals: sortSessions(originals), adaptedByParent };
}

export function isSetLogged(set: SetItem): boolean {
  return set.actual_reps !== null && set.actual_reps !== undefined;
}

export function sessionProgress(session: TrainingSession): { logged: number; total: number } {
  return {
    logged: session.sets.filter(isSetLogged).length,
    total: session.sets.length,
  };
}

/** Texto de la carga prescrita, tal como debe leerlo el atleta. */
export function loadLabel(set: SetItem): string {
  if (set.prescribed_weight) return `${formatKg(set.prescribed_weight)} kg`;
  if (set.prescribed_percentage) {
    const reference = set.reference_exercise ?? set.exercise?.name;
    return `${Math.round(set.prescribed_percentage)}% de tu 1RM de ${reference}`;
  }
  return "peso libre";
}

/** "4 x 5 @ 135 kg" — resumen compacto de un bloque de ejercicio. */
export function groupSummary(group: ExerciseGroup): string {
  const first = group.sets[0];
  if (!first) return "";
  const reps = new Set(group.sets.map((set) => set.prescribed_reps));
  const repsLabel = reps.size === 1 ? String(first.prescribed_reps) : [...reps].join("/");
  return `${group.sets.length} x ${repsLabel} @ ${loadLabel(first)}`;
}
