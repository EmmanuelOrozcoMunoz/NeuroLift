// Sesiones de entrenamiento, series y WOD.

export interface Exercise {
  id: string;
  name: string;
  category: string | null;
}

export interface SetItem {
  id: string;
  set_order: number;
  /** Parte de la sesión (calentamiento, fuerza, weightlifting, skills, metcon...). Ver lib/blocks.ts. */
  block: string | null;
  prescribed_reps: number;
  rpe: number | null;
  prescribed_weight: number | null;
  prescribed_percentage: number | null;
  reference_exercise: string | null;
  actual_reps: number | null;
  actual_weight: number | null;
  technique_feedback: string | null;
  /** Anotación del coach para el ejercicio (la misma en todas sus series). */
  coach_note?: string | null;
  exercise: Exercise;
}

export type SessionStatus = "pending" | "completed" | string;

/** Formatos estándar de WOD que el coach puede prescribir para una sesión. */
export type WodFormat =
  | "for_time"
  | "amrap"
  | "amrap_reps"
  | "emom"
  | "tabata"
  | "1rm"
  | "calories"
  | "distance"
  | "watts";

export interface TrainingSession {
  id: string;
  mesocycle_id: string;
  scheduled_date: string; // YYYY-MM-DD
  completed_date: string | null;
  athlete_notes: string | null;
  status: SessionStatus;
  /** Si viene poblado, esta sesión es la versión corta de `parent_session_id`. */
  parent_session_id: string | null;
  /** Registro de una clase del box: la sesión de la clase de la que es copia */
  class_session_id?: string | null;
  duration_minutes: number | null;
  day_offset: number | null;
  /** Orden de bloques que el coach eligió para esta sesión, ej. "warmup,strength,metcon" — null
   *  usa el orden canónico de BLOCK_KEYS. Ver groupByBlock() en lib/sessions.ts. */
  block_order: string | null;
  /** Pautas de calentamiento/aproximaciones del coach, mostradas antes del primer bloque. */
  warmup_notes: string | null;
  /** Descripción libre del WOD en texto plano (ej. "21-15-9 thrusters 42kg, pull-ups") — para
   *  cuando el esquema de ejercicios/series (nombre + reps/peso fijos) no alcanza. */
  wod_notes: string | null;
  /** El coach lo prescribe (PUT /sessions/{id}/wod-format); el atleta reporta el resultado al
   *  completar la sesión. null = esta sesión no tiene un WOD con formato de puntaje formal. */
  wod_format: WodFormat | null;
  /** Timer que fijó el coach: cap duro para "for_time", duración de la ventana para
   *  amrap/amrap_reps/calories/distance/watts. null si no aplica o no se fijó. */
  wod_time_cap_seconds: number | null;
  wod_time_seconds: number | null;
  wod_rounds: number | null;
  wod_extra_reps: number | null;
  wod_emom_completed: boolean | null;
  wod_calories: number | null;
  wod_distance_meters: number | null;
  wod_watts: number | null;
  sets: SetItem[];
}

/** Body de PUT /sessions/{id}/wod-format. */
export interface WodFormatPayload {
  wod_format: WodFormat | null;
  time_cap_seconds?: number | null;
}

/** Body opcional de POST /sessions/{id}/complete — solo aplica si la sesión tenía wod_format. */
export interface SessionCompletePayload {
  wod_time_seconds?: number | null;
  wod_rounds?: number | null;
  wod_extra_reps?: number | null;
  wod_emom_completed?: boolean | null;
  wod_calories?: number | null;
  wod_distance_meters?: number | null;
  wod_watts?: number | null;
}

/** GET /users/{id}/recent-activity — una sesión ya completada, con lo REALMENTE hecho. */
export interface RecentSessionExercise {
  exercise_name: string;
  block: string | null;
  sets_logged: number;
  actual_reps: number[];
  actual_weight: number[];
}

export interface RecentSessionSummary {
  session_id: string;
  scheduled_date: string;
  completed_date: string | null;
  mesocycle_name: string | null;
  discipline: string;
  wod_format: WodFormat | null;
  wod_time_cap_seconds: number | null;
  wod_time_seconds: number | null;
  wod_rounds: number | null;
  wod_extra_reps: number | null;
  wod_emom_completed: boolean | null;
  wod_calories: number | null;
  wod_distance_meters: number | null;
  wod_watts: number | null;
  exercises: RecentSessionExercise[];
}

/** Una serie con sus propias repeticiones y su propia carga (planes y programas de grupo). */
export interface SerieEnPeticion {
  prescribed_reps: number;
  prescribed_weight: number | null;
  prescribed_percentage: number | null;
}

export interface SetCreatePayload {
  exercise_name: string;
  prescribed_reps: number;
  rpe: number | null;
  prescribed_weight: number | null;
  /** Carga en % de 1RM en vez de kg fijos — si viene, el backend la calcula con las marcas
   *  YA registradas del atleta. `reference_exercise` vacío usa el mismo ejercicio. */
  prescribed_percentage?: number | null;
  reference_exercise?: string | null;
  block?: string | null;
  /** Nota del coach para el atleta; "" la borra. */
  coach_note?: string | null;
}

export interface SetUpdatePayload {
  exercise_name: string | null;
  prescribed_reps: number;
  rpe: number | null;
  prescribed_weight: number | null;
  prescribed_percentage?: number | null;
  reference_exercise?: string | null;
  block?: string | null;
  /** Nota del coach para el atleta; "" la borra. */
  coach_note?: string | null;
}
