// Marcas personales y nivel de fitness.

export interface PersonalRecord {
  id: string;
  exercise_name: string;
  max_weight_kg: number;
  last_updated: string;
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
