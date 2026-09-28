// Tablero del dueño del box.
import type { Role } from "./auth";

export interface CoachLoad {
  id: string;
  full_name: string;
  role: Role;
  athletes: number;
  trained_this_week: number;
  classes: number;
}

export interface AttentionAthlete {
  id: string;
  full_name: string;
  reason: "sin_coach" | "inactivo" | "nuevo";
  last_completed_at: string | null;
}

/** GET /boxes/me/dashboard */
export interface OwnerDashboard {
  athletes_total: number;
  max_athletes: number | null;
  athletes_trained_this_week: number;
  sessions_completed_this_week: number;
  athletes_without_coach: number;
  new_athletes_this_week: number;
  classes_today: number;
  unprogrammed_classes_next_7_days: number;
  coaches: CoachLoad[];
  attention: AttentionAthlete[];
}
