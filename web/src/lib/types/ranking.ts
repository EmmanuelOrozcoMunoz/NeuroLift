// Ranking del box entre atletas: marcas (1RM) y WODs.

/** GET /ranking/lifts — un levantamiento con marcas en el ranking */
export interface RankingLift {
  key: string;
  name: string;
  athletes_count: number;
}

/** GET /ranking/lifts/{key} */
export interface RankingLiftRow {
  rank: number;
  user_id: string;
  full_name: string;
  has_avatar: boolean;
  weight_kg: number;
  category: "rx" | "scaled" | null;
  is_me: boolean;
}

/** GET /ranking/wods — un WOD anotado con resultado, por nombre y formato */
export interface RankingWod {
  key: string;
  name: string;
  wod_format: string;
  athletes_count: number;
  last_date: string;
}

/** GET /ranking/wods/{key}?wod_format= */
export interface RankingWodRow {
  rank: number;
  user_id: string;
  full_name: string;
  has_avatar: boolean;
  score_label: string | null;
  date: string;
  category: "rx" | "scaled" | null;
  is_me: boolean;
}
