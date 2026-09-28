// Boxes, planes de suscripción y miembros.
import type { Role } from "./auth";

export type BoxStatus = "pending" | "active" | "rejected" | "suspended";

/** "box" = gimnasio | "coach" = cuenta de un coach independiente | "athlete" = cuenta personal
 *  de un atleta solo (gratis). Para el usuario, ni el coach ni el atleta solo "tienen box". */
export type BoxKind = "box" | "coach" | "athlete";

export type PlanCode = "basic" | "pro" | "unlimited";

export type SubscriptionStatus = "trial" | "active" | "expired";

/** GET /boxes/pricing */
export interface PricingPlan {
  code: PlanCode;
  name: string;
  max_athletes: number | null;
  monthly_price: number;
  currency: string;
}

export interface Pricing {
  trial_days: number;
  plans: PricingPlan[];
}

/** Lo que cualquier miembro ve de su box (viene embebido en /auth/me). */
export interface BoxSummary {
  id: string;
  name: string;
  city: string | null;
  status: BoxStatus;
  kind: BoxKind;
  /** "#rrggbb" o null = acento por defecto de la app */
  accent_color: string | null;
  has_logo: boolean;
}

/** GET /boxes/me */
export interface BoxDetail extends BoxSummary {
  address: string | null;
  state: string | null;
  country: string | null;
  /** Solo lo reciben el dueño y los coaches */
  invite_code: string | null;
  created_at: string | null;
  /** Suscripción: solo la recibe el dueño de la cuenta (null para los demás) */
  plan: PlanCode | null;
  subscription_status: SubscriptionStatus | null;
  trial_ends_at: string | null;
  paid_until: string | null;
  athletes_count: number | null;
  max_athletes: number | null;
}

export interface BoxUpdatePayload {
  name?: string;
  address?: string | null;
  city?: string | null;
  state?: string | null;
  country?: string | null;
  /** "" = volver al acento por defecto */
  accent_color?: string;
}

export interface BoxRegisterPayload {
  box_name: string;
  address: string | null;
  city: string;
  state: string | null;
  country: string | null;
  owner_name: string;
  email: string;
  password: string;
}

/** GET /boxes/me/members */
export interface BoxMember {
  id: string;
  full_name: string;
  email: string;
  role: Role;
  has_avatar: boolean;
  coach_id: string | null;
  coach_name: string | null;
  created_at: string | null;
}
