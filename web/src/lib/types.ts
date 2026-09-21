// Espejo de backend/schemas.py. Se mantiene a mano a propósito: el backend expone
// /openapi.json solo fuera de producción, así que generar tipos automáticamente ataría el
// build del frontend a tener el backend corriendo.

export type Role = "athlete" | "coach" | "admin";

export type WeightUnit = "kg" | "lb";

export interface User {
  id: string;
  full_name: string;
  email: string;
  body_weight: number | null;
  role: Role;
  /** true -> el cliente puede pedir GET /users/{id}/avatar */
  has_avatar: boolean;
  created_at: string | null;
  /** En qué unidad ESTE usuario prefiere ver/escribir cualquier peso. null = "kg". */
  weight_unit: WeightUnit | null;
  /** Para la calculadora de discos: define el peso de SU barra (20kg / 15kg). */
  sex: "male" | "female" | null;
  /** Si su box tiene discos de 25kg. null = true (por defecto sí tiene). */
  has_25kg_plates: boolean | null;
}

export interface LoginResponse {
  access_token: string;
  token_type: string;
}

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
  duration_minutes: number | null;
  day_offset: number | null;
  /** Orden de bloques que el coach eligió para esta sesión, ej. "warmup,strength,metcon" — null
   *  usa el orden canónico de BLOCK_KEYS. Ver groupByBlock() en lib/sessions.ts. */
  block_order: string | null;
  /** Pautas de calentamiento/aproximaciones del coach, mostradas antes del primer bloque. */
  warmup_notes: string | null;
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

/** GET /users/{id}/mesocycles/ — response_model=MesocycleSummaryResponse en el backend. */
export interface MesocycleSummary {
  id: string;
  user_id: string;
  group_id: string | null;
  name: string | null;
  discipline: string;
  start_date: string;
  end_date: string | null;
  is_active: boolean;
  created_at: string;
  description: string | null;
  level: string | null;
  /** true = lo creó el propio atleta a mano (sin coach), para su registro personal. */
  is_self_managed: boolean;
}

/** GET /mesocycles/{id} y GET /plans/{id} */
export interface MesocycleFull {
  id: string;
  user_id: string | null;
  name: string | null;
  discipline: string;
  start_date: string;
  end_date: string | null;
  description: string | null;
  level: string | null;
  /** Solo relevante en planes (is_template) — null en mesociclos normales. */
  price: number | null;
  is_template: boolean;
  /** true -> el cliente puede pedir GET /plans/{id}/cover (solo relevante si is_template) */
  has_cover_image: boolean;
  /** Siempre false aquí — esta es la forma COMPLETA. Ver PlanPreview para la otra mitad de la
   *  unión que puede devolver GET /plans/{id}. */
  is_preview?: false;
  /** true = el propio atleta lo creó a mano (sin coach), para su registro personal. */
  is_self_managed: boolean;
  sessions: TrainingSession[];
}

/** Un día de un plan tal como lo ve alguien que NO es su autor/admin: estructura (bloques +
 *  cuántos ejercicios), sin los ejercicios/series/pesos exactos. */
export interface PlanPreviewSession {
  id: string;
  day_offset: number | null;
  blocks: string[];
  exercise_count: number;
}

/** GET /plans/{id} para cualquiera que no sea el autor/admin del plan (típicamente un atleta
 *  viendo el catálogo antes de comprarlo) — vista previa sin revelar la programación completa. */
export interface PlanPreview {
  id: string;
  name: string | null;
  discipline: string;
  start_date: string;
  end_date: string | null;
  description: string | null;
  level: string | null;
  is_template: boolean;
  has_cover_image: boolean;
  is_preview: true;
  sessions: PlanPreviewSession[];
}

/** GET /plans/{id} devuelve una de las dos formas según quién pregunte — discrimina por
 *  `is_preview`. */
export type PlanDetailResponse = MesocycleFull | PlanPreview;

export interface PersonalRecord {
  id: string;
  exercise_name: string;
  max_weight_kg: number;
  last_updated: string;
}

export interface PlanSummary {
  id: string;
  name: string;
  description: string | null;
  discipline: string;
  level: string | null;
  price: number | null;
  weeks_count: number;
  sessions_count: number;
  sessions_per_week: number;
  coach_name: string | null;
  is_published: boolean;
  /** true -> el cliente puede pedir GET /plans/{id}/cover */
  has_cover_image: boolean;
  created_at: string;
}

export type FitCategory = "halterofilia" | "gimnasia" | "metcon";

export type WodCategory = "rx" | "scaled";

export interface FitnessLevel {
  body_weight: number | null;
  sex: "male" | "female" | null;
  age: number | null;
  /** Con qué categoría compite el atleta en los WODs — resuelve qué peso (de los 4 que el
   *  coach prescribe por género/categoría) le corresponde en el bloque metabólico. */
  category: WodCategory | null;
  values: Record<string, number>;
  category_scores: Partial<Record<FitCategory, number>>;
  category_levels: Partial<Record<FitCategory, string>>;
  overall_score: number | null;
  overall_level: string | null;
}

export interface MessageResponse {
  message: string;
}

/** GET /coach/leaderboard — una fila por atleta, ya ordenadas por actividad de esta semana. */
export interface AthleteActivity {
  user_id: string;
  full_name: string;
  has_avatar: boolean;
  completed_total: number;
  completed_this_week: number;
  last_completed_at: string | null;
  /** Ya viene formateado del backend, ej. "Por tiempo: 12:34" — null si no tiene ningún WOD
   *  con resultado registrado todavía. */
  last_wod_summary: string | null;
}

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

// ============================================================ panel de coach

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

export type Weekday = 0 | 1 | 2 | 3 | 4 | 5 | 6; // 0 = lunes ... 6 = domingo

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

export interface ManualMesocyclePayload {
  user_id: string;
  name: string;
  discipline: string;
  start_date: string;
  weeks_count: number;
  training_days: Weekday[];
}

export interface ManualMesocycleGroupPayload {
  group_id: string;
  name: string;
  discipline: string;
  start_date: string;
  weeks_count: number;
  training_days: Weekday[];
}

export interface AIGenerateSmartPayload {
  user_id: string;
  name: string;
  discipline: string;
  start_date: string;
  weeks_count: number;
  training_days: Weekday[];
  context: string;
  session_duration_minutes: number | null;
  /** Guía opcional por día de la semana (0=Lunes..6=Domingo) de lo que prescribir ESE día. */
  day_focus?: Partial<Record<Weekday, string>>;
}

export interface AIGenerateSmartGroupPayload {
  group_id: string;
  name: string;
  discipline: string;
  start_date: string;
  weeks_count: number;
  training_days: Weekday[];
  context: string;
  session_duration_minutes: number | null;
  day_focus?: Partial<Record<Weekday, string>>;
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
}

export interface SetUpdatePayload {
  exercise_name: string | null;
  prescribed_reps: number;
  rpe: number | null;
  prescribed_weight: number | null;
  prescribed_percentage?: number | null;
  reference_exercise?: string | null;
  block?: string | null;
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

export interface BulkResultRow {
  full_name: string;
  status: string;
}

export interface BulkResponse {
  message: string;
  results: BulkResultRow[];
}

export type PlanLevel = "Principiante" | "Intermedio" | "Avanzado";

export interface PlanCreatePayload {
  name: string;
  description: string;
  discipline: string;
  level: PlanLevel;
  price: number | null;
  weeks_count: number;
  training_days: Weekday[];
}

/** PUT /plans/{id} — igual a PlanCreatePayload sin el calendario (weeks_count/training_days),
 *  que ya quedó fijo desde la creación. */
export interface PlanUpdatePayload {
  name: string;
  description: string;
  discipline: string;
  level: PlanLevel;
  price: number | null;
}

export interface PlanSetCreatePayload {
  exercise_name: string;
  prescribed_sets: number;
  prescribed_reps: number;
  rpe: number | null;
  prescribed_weight: number | null;
  prescribed_percentage: number | null;
  reference_exercise: string | null;
  block?: string | null;
}

// ------------------------------------------------------------------- admin

/** GET /admin/overview */
export interface AdminOverview {
  total_users: number;
  total_coaches: number;
  total_athletes: number;
  total_admins: number;
  total_groups: number;
  total_mesocycles: number;
  total_sessions: number;
  sessions_completed: number;
  sessions_pending: number;
}

/** PUT /admin/users/{id}/role */
export interface UserRoleUpdatePayload {
  role: Role;
}

/** GET /admin/logs */
export interface AuditLog {
  id: string;
  created_at: string | null;
  level: string;
  message: string;
}
