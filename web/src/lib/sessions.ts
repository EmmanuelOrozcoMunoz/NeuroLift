import { BLOCK_KEYS, blockLabel } from "@/lib/blocks";
import { parseApiDate } from "@/lib/dates";
import { formatWeight, kgTo } from "@/lib/units";
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

/** Los ejercicios de la sesión en el orden en que el atleta los va a hacer: por bloque, respetando
 *  el orden de bloques de ESA sesión (`block_order`). Es lo que deben mostrar las vistas previas;
 *  `groupSets` solo ordena por set_order y no sabe de bloques. */
export function gruposEnOrden(sets: SetItem[], blockOrder?: string | null): ExerciseGroup[] {
  return groupByBlock(sets, blockOrder).flatMap((bloque) => bloque.groups);
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
 *
 * `forceMetcon` asegura que el bloque "metcon" (Metabólico) exista en el resultado aunque
 * ningún Set real lleve ese bloque -- así el llamador puede mostrar ahí el texto libre + puntaje
 * de `Session.wod_notes`/`wod_format` (ver WodBlockCard) para una sesión que todavía no tiene
 * ejercicios estructurados en ese bloque, sin perder los que ya existan.
 */
export function groupByBlock(sets: SetItem[], blockOrder?: string | null, forceMetcon?: boolean): SessionBlockGroup[] {
  const ordered = [...sets].sort((a, b) => a.set_order - b.set_order);
  const anyBlocked = ordered.some((set) => set.block);
  if (!anyBlocked && !forceMetcon) {
    return [{ key: null, label: "", groups: groupSets(ordered) }];
  }

  const buckets = new Map<string | null, SetItem[]>();
  for (const set of ordered) {
    const key = set.block ?? null;
    const list = buckets.get(key);
    if (list) list.push(set);
    else buckets.set(key, [set]);
  }
  if (forceMetcon && !buckets.has("metcon")) {
    buckets.set("metcon", []);
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

/** La carga de una serie en pocas letras: "60%", "80 kg" o "libre". */
function shortLoad(set: SetItem, unit: WeightUnit): string {
  if (set.prescribed_percentage) return `${Math.round(set.prescribed_percentage)}%`;
  if (set.prescribed_weight) return formatWeight(set.prescribed_weight, unit);
  return "libre";
}

/** La serie tal como cuenta para el resumen: si ya está anotada, con lo que se hizo (reps y peso
 *  reales; el % prescrito deja de aplicar al peso real); si no, con lo prescrito. */
function serieEfectiva(set: SetItem): SetItem {
  if (!isSetLogged(set)) return set;
  const peso = set.actual_weight || set.prescribed_weight;
  return {
    ...set,
    prescribed_reps: set.actual_reps ?? set.prescribed_reps,
    prescribed_weight: peso,
    prescribed_percentage: set.actual_weight ? null : set.prescribed_percentage,
  };
}

/** Resumen compacto de un ejercicio. Con series iguales: "4 x 5 @ 135 kg". Con series distintas
 *  (una rampa): cada serie con su carga y sus repeticiones, "50%×3 · 60%×3 · 70%×1". Las series ya
 *  anotadas cuentan con lo que se hizo, no con lo prescrito. */
export function groupSummary(group: ExerciseGroup, unit: WeightUnit): string {
  const series = group.sets.map(serieEfectiva);
  const first = series[0];
  if (!first) return "";
  const iguales = series.every(
    (set) =>
      set.prescribed_reps === first.prescribed_reps &&
      set.prescribed_weight === first.prescribed_weight &&
      set.prescribed_percentage === first.prescribed_percentage,
  );
  if (iguales) return `${series.length} x ${first.prescribed_reps} @ ${loadLabel(first, unit)}`;
  return series.map((set) => `${shortLoad(set, unit)}×${set.prescribed_reps}`).join(" · ");
}

/** La carga de un ejercicio en cifra y unidad, para las vistas previas: el peso real de las series
 *  ya anotadas y el prescrito en las demás. En una rampa (series con
 *  cargas distintas) es el rango "mín–máx", no solo la carga de la primera serie. */
export function cargaDelGrupo(group: ExerciseGroup, unit: WeightUnit): { value: string; unit: string } | null {
  // Una serie ya anotada cuenta con el peso que se levantó, no con el prescrito.
  const pesos = group.sets
    .map((set) => (isSetLogged(set) && set.actual_weight ? set.actual_weight : set.prescribed_weight))
    .filter((peso): peso is number => Boolean(peso))
    .map((peso) => kgTo(peso, unit));
  const numero = (v: number) => (Number.isInteger(v) ? String(v) : v.toFixed(1));
  const rango = (valores: number[], formato: (v: number) => string) => {
    const [min, max] = [Math.min(...valores), Math.max(...valores)];
    return min === max ? formato(min) : `${formato(min)}–${formato(max)}`;
  };
  if (pesos.length > 0) return { value: rango(pesos, numero), unit };
  const porcentajes = group.sets.filter((set) => set.prescribed_percentage).map((set) => Math.round(set.prescribed_percentage!));
  if (porcentajes.length > 0) return { value: rango(porcentajes, String), unit: "%" };
  return null;
}
