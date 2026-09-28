// Sesión y usuario.
import type { BoxSummary } from "./boxes";

/** owner = dueño del box: un coach con alcance sobre todo su box. admin = plataforma. */
export type Role = "athlete" | "coach" | "owner" | "admin";

/** Roles que programan entrenamientos (acceden a las pantallas de coach). */
export const COACHING_ROLES: Role[] = ["coach", "owner"];

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
  /** Coach directo (atletas). null = atleta "del box", sin coach. */
  coach_id: string | null;
  /** Box al que pertenece. null solo para el admin de plataforma. */
  box: BoxSummary | null;
}

/** Respuesta mínima de GET /users/search -- a propósito no es un User completo, ver
 *  AthleteLookupResponse en el backend. */
export interface AthleteLookup {
  id: string;
  full_name: string;
  email: string;
}

export interface LoginResponse {
  access_token: string;
  token_type: string;
}
