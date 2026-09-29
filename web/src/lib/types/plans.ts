// Planes de la tienda.
import type { SerieEnPeticion } from "./sessions";
import type { Weekday } from "./common";
import type { MesocycleFull } from "./mesocycles";

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
  /** "box" = solo atletas del box del autor; "public" = toda la plataforma */
  visibility: PlanVisibility;
  /** Box del autor (el catálogo lo muestra en planes públicos de otro box) */
  box_name: string | null;
}

export type PlanVisibility = "box" | "public";

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
  /** Nota del coach para el atleta; "" la borra. */
  coach_note?: string | null;
  /** Series una por una (rampas). Si viene, manda sobre prescribed_sets/reps/carga. */
  series?: SerieEnPeticion[];
}
