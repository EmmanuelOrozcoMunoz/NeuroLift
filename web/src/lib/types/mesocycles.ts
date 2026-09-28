// Mesociclos y su creación (manual o con IA).
import type { Weekday } from "./common";
import type { TrainingSession } from "./sessions";

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
  /** Mesociclo "Clases del box" del atleta: junta sus registros de clases */
  is_class_log: boolean;
  /** Programación de una clase del box (sin atleta) */
  class_id: string | null;
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
  /** Mesociclo "Clases del box" del atleta: junta sus registros de clases */
  is_class_log: boolean;
  /** Programación de una clase del box (sin atleta) */
  class_id: string | null;
  sessions: TrainingSession[];
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
