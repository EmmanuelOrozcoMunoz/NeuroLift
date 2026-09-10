// Espejo de backend/schemas.py. Se mantiene a mano a propósito: el backend expone
// /openapi.json solo fuera de producción, así que generar tipos automáticamente ataría el
// build del frontend a tener el backend corriendo.

export type Role = "athlete" | "coach" | "admin";

export interface User {
  id: string;
  full_name: string;
  email: string;
  body_weight: number | null;
  role: Role;
  /** true -> el cliente puede pedir GET /users/{id}/avatar */
  has_avatar: boolean;
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
  sets: SetItem[];
}

/** GET /users/{id}/mesocycles/ — el backend devuelve el modelo ORM crudo (sin response_model). */
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
  is_template: boolean;
  sessions: TrainingSession[];
}

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
  created_at: string;
}

export type FitCategory = "halterofilia" | "gimnasia" | "metcon";

export interface FitnessLevel {
  body_weight: number | null;
  sex: "male" | "female" | null;
  age: number | null;
  values: Record<string, number>;
  category_scores: Partial<Record<FitCategory, number>>;
  category_levels: Partial<Record<FitCategory, string>>;
  overall_score: number | null;
  overall_level: string | null;
}

export interface MessageResponse {
  message: string;
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
  members: GroupMember[];
}

/** GET /groups/ */
export interface GroupSummary {
  id: string;
  name: string;
  created_at: string;
  member_count: number;
  coach_name: string | null;
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
}

export interface SetCreatePayload {
  exercise_name: string;
  prescribed_reps: number;
  rpe: number | null;
  prescribed_weight: number | null;
}

export interface SetUpdatePayload {
  exercise_name: string | null;
  prescribed_reps: number;
  rpe: number | null;
  prescribed_weight: number | null;
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

export interface PlanSetCreatePayload {
  exercise_name: string;
  prescribed_sets: number;
  prescribed_reps: number;
  rpe: number | null;
  prescribed_weight: number | null;
  prescribed_percentage: number | null;
  reference_exercise: string | null;
}
