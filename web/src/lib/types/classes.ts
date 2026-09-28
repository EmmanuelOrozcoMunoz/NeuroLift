// Clases del box y su registro.
import type { TrainingSession } from "./sessions";

/** GET /classes/ */
export interface BoxClass {
  id: string;
  name: string;
  description: string | null;
  coach_id: string | null;
  coach_name: string | null;
  /** 0 = lunes ... 6 = domingo */
  weekdays: number[];
  /** "HH:MM", hora local del box */
  start_time: string;
  duration_minutes: number;
  is_active: boolean;
  /** Quien pregunta puede programar su contenido (su profesor o el dueño) */
  can_program: boolean;
}

export interface BoxClassPayload {
  name: string;
  description: string | null;
  coach_id: string | null;
  weekdays: number[];
  start_time: string;
  duration_minutes: number;
}

/** GET /classes/schedule — una clase en un día concreto */
export interface ClassOccurrence {
  class_id: string;
  class_name: string;
  description: string | null;
  date: string; // YYYY-MM-DD
  start_time: string;
  duration_minutes: number;
  coach_id: string | null;
  coach_name: string | null;
  can_program: boolean;
  /** Contenido programado para ese día (null = todavía sin programar) */
  session: TrainingSession | null;
  program_mesocycle_id: string | null;
  program_name: string | null;
  /** Registro del atleta que pregunta, si ya registró esta clase */
  my_session_id: string | null;
  my_mesocycle_id: string | null;
  my_status: string | null;
}

export interface ClassProgram {
  id: string;
  name: string;
  start_date: string;
  end_date: string | null;
  sessions_count: number;
  skipped_dates: string[];
}

export interface ClassJoinResponse {
  mesocycle_id: string;
  session_id: string;
  missing_prs: string[];
}
