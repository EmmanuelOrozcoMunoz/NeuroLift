import { BLOCK_KEYS, blockLabel } from "@/lib/blocks";
import { parseApiDate } from "@/lib/dates";
import { formatWeight } from "@/lib/units";
import type { SetItem, TrainingSession, WeightUnit } from "@/lib/types";

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

/** Un bloque de la sesión (calentamiento, fuerza...) con sus ejercicios ya agrupados. */
export interface SessionBlockGroup {
  /** null = sin bloque asignado (dato viejo, o el coach no lo especificó). */
  key: string | null;
  /** Vacío cuando NINGÚN set de la sesión tiene bloque — así el llamador sabe que no debe
   *  mostrar encabezados de sección (comportamiento idéntico al de antes de que existieran). */
  label: string;
  groups: ExerciseGroup[];
}

/**
 * Agrupa las series de una sesión por bloque (calentamiento/fuerza/weightlifting/skills/metcon/
 * accesorios/principal) y dentro de cada bloque por ejercicio (groupSets). Si NINGÚN set trae
 * bloque (sesiones viejas, o el coach no los usa), devuelve un solo grupo sin etiqueta — se ve
 * exactamente igual que antes de que existieran los bloques.
 *
 * `blockOrder` es el `Session.block_order` guardado (ej. "warmup,strength,metcon"), tal cual
 * viene de la API — si el coach reordenó los bloques de ESTA sesión, se respeta ese orden en vez
 * del canónico de BLOCK_KEYS. Cualquier bloque presente pero ausente de esa lista (ej. porque se
 * agregó un ejercicio de un bloque nuevo después de fijar el orden) cae al final, en su posición
 * canónica — así nunca desaparece un bloque por no estar en la lista guardada.
 */
export function groupByBlock(sets: SetItem[], blockOrder?: string | null): SessionBlockGroup[] {
  const ordered = [...sets].sort((a, b) => a.set_order - b.set_order);
  const anyBlocked = ordered.some((set) => set.block);
  if (!anyBlocked) {
    return [{ key: null, label: "", groups: groupSets(ordered) }];
  }

  const buckets = new Map<string | null, SetItem[]>();
  for (const set of ordered) {
    const key = set.block ?? null;
    const list = buckets.get(key);
    if (list) list.push(set);
    else buckets.set(key, [set]);
  }

  const customOrder = (blockOrder ?? "").split(",").filter(Boolean);
  const orderSource = customOrder.length > 0 ? customOrder : BLOCK_KEYS;
  const known = [
    ...orderSource.filter((key) => buckets.has(key)),
    ...BLOCK_KEYS.filter((key) => buckets.has(key) && !orderSource.includes(key)),
  ];
  const custom = [...buckets.keys()].filter(
    (key): key is string => key !== null && !(BLOCK_KEYS as readonly string[]).includes(key),
  );
  const orderedKeys: (string | null)[] = [...known, ...custom, ...(buckets.has(null) ? [null] : [])];

  return orderedKeys.map((key) => ({
    key,
    label: key ? blockLabel(key) : "Otros ejercicios",
    groups: groupSets(buckets.get(key)!),
  }));
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

/** Texto de la carga prescrita, tal como debe leerlo el atleta. Cuando el coach prescribió un
 *  % de 1RM, el backend ya resolvió el peso en kg (para que el atleta no tenga que calcularlo),
 *  pero el atleta también quiere ver el % que le corresponde, no solo el kg resultante. */
export function loadLabel(set: SetItem, unit: WeightUnit): string {
  if (set.prescribed_weight && set.prescribed_percentage) {
    return `${formatWeight(set.prescribed_weight, unit)} (${Math.round(set.prescribed_percentage)}%)`;
  }
  if (set.prescribed_weight) return formatWeight(set.prescribed_weight, unit);
  if (set.prescribed_percentage) {
    const reference = set.reference_exercise ?? set.exercise?.name;
    return `${Math.round(set.prescribed_percentage)}% de tu 1RM de ${reference}`;
  }
  return "peso libre";
}

/** "4 x 5 @ 135 kg" — resumen compacto de un bloque de ejercicio. */
export function groupSummary(group: ExerciseGroup, unit: WeightUnit): string {
  const first = group.sets[0];
  if (!first) return "";
  const reps = new Set(group.sets.map((set) => set.prescribed_reps));
  const repsLabel = reps.size === 1 ? String(first.prescribed_reps) : [...reps].join("/");
  return `${group.sets.length} x ${repsLabel} @ ${loadLabel(first, unit)}`;
}
