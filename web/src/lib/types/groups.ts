// Grupos, programas de grupo y edición masiva.
import type { WodFormat } from "./sessions";

/** GET /groups/{id}/wod-days — una fecha del grupo con un WOD prescrito. `wod_name` no se
 *  guarda aparte: es el nombre del ejercicio del bloque metabólico de esa sesión. */
export interface WodDaySummary {
  scheduled_date: string;
  wod_format: WodFormat;
  wod_name: string | null;
  time_cap_seconds: number | null;
  participants_count: number;
}

/** GET /groups/{id}/wod-leaderboard — una fila por atleta, ya ordenadas por resultado. */
export interface WodLeaderboardRow {
  user_id: string;
  full_name: string;
  has_avatar: boolean;
  wod_format: WodFormat;
  wod_name: string | null;
  score_label: string | null;
  rank: number | null;
  completed: boolean;
}

/** Body de POST /groups/{id}/sessions/bulk-set-wod-format. */
export interface GroupBulkWodFormatPayload {
  program_name: string;
  program_start_date: string;
  scheduled_date: string;
  wod_format: WodFormat | null;
  time_cap_seconds: number | null;
}

/** Body de POST /groups/{id}/sessions/bulk-set-wod-notes. */
export interface GroupBulkWodNotesPayload {
  program_name: string;
  program_start_date: string;
  scheduled_date: string;
  wod_notes: string | null;
}

export interface GroupMember {
  id: string;
  full_name: string;
  email: string;
}

/** GET /groups/{id} */
export interface GroupDetail {
  id: string;
  name: string;
  created_at: string;
  /** true -> el cliente puede pedir GET /groups/{id}/cover */
  has_cover_image: boolean;
  members: GroupMember[];
}

/** GET /groups/ */
export interface GroupSummary {
  id: string;
  name: string;
  created_at: string;
  member_count: number;
  coach_name: string | null;
  has_cover_image: boolean;
}

export interface GroupMesocycleAthlete {
  user_id: string;
  full_name: string;
  mesocycle_id: string;
  is_active: boolean;
}

/** GET /groups/{id}/mesocycles */
export interface GroupMesocycleProgram {
  name: string;
  discipline: string;
  start_date: string;
  end_date: string | null;
  created_at: string;
  athletes: GroupMesocycleAthlete[];
  session_dates: string[];
}

export interface RegisterAthletePayload {
  full_name: string;
  email: string;
  password: string;
  role: "athlete";
  body_weight: number | null;
}

export interface CreateGroupPayload {
  name: string;
  athlete_ids: string[];
}

export interface GroupBulkAddPayload {
  program_name: string;
  program_start_date: string;
  scheduled_date: string;
  exercise_name: string;
  prescribed_sets: number;
  prescribed_reps: number;
  rpe: number | null;
  prescribed_weight: number | null;
  /** Pesos del WOD por categoría/género (bloque metcon) — opcionales. Si se manda cualquiera
   *  de estos, cada atleta recibe el que le corresponde según su categoría y sexo; si ninguno
   *  viene, se usa `prescribed_weight` para todos (mismo comportamiento de siempre). */
  prescribed_weight_rx_male?: number | null;
  prescribed_weight_rx_female?: number | null;
  prescribed_weight_scaled_male?: number | null;
  prescribed_weight_scaled_female?: number | null;
  /** Carga en % de 1RM (bloques de fuerza/weightlifting) — cada atleta recibe su propio peso
   *  calculado con SUS marcas ya registradas. `reference_exercise` vacío usa el mismo ejercicio. */
  prescribed_percentage?: number | null;
  reference_exercise?: string | null;
  block?: string | null;
  /** Nota del coach para el atleta; "" la borra. */
  coach_note?: string | null;
}

export interface GroupBulkUpdatePayload {
  program_name: string;
  program_start_date: string;
  scheduled_date: string;
  exercise_name: string;
  new_exercise_name: string;
  prescribed_sets: number;
  prescribed_reps: number;
  rpe: number | null;
  prescribed_weight: number | null;
  prescribed_weight_rx_male?: number | null;
  prescribed_weight_rx_female?: number | null;
  prescribed_weight_scaled_male?: number | null;
  prescribed_weight_scaled_female?: number | null;
  prescribed_percentage?: number | null;
  reference_exercise?: string | null;
  block?: string | null;
  /** Nota del coach para el atleta; "" la borra. */
  coach_note?: string | null;
}

/** Qué pasa con el mesociclo de un atleta que sale de un programa de grupo:
 *  "desvincular" lo conserva (con su historial) como programa individual; "eliminar" lo borra. */
export type AccionPrograma = "desvincular" | "eliminar";

export interface GroupProgramAthleteRemovePayload {
  program_name: string;
  program_start_date: string;
  user_id: string;
  action: AccionPrograma;
}

export interface GroupProgramDeletePayload {
  program_name: string;
  program_start_date: string;
}

export interface GroupBulkDeletePayload {
  program_name: string;
  program_start_date: string;
  scheduled_date: string;
  exercise_name: string;
}
