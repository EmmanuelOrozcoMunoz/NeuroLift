// Panel de administración de la plataforma.
import type { Role } from "./auth";
import type { BoxKind, BoxStatus, PlanCode, SubscriptionStatus } from "./boxes";

/** GET /admin/boxes */
export interface AdminBoxRow {
  id: string;
  name: string;
  city: string | null;
  state: string | null;
  country: string | null;
  status: BoxStatus;
  kind: BoxKind;
  plan: PlanCode;
  subscription_status: SubscriptionStatus;
  trial_ends_at: string | null;
  paid_until: string | null;
  max_athletes: number | null;
  has_logo: boolean;
  owner_name: string | null;
  owner_email: string | null;
  coaches_count: number;
  athletes_count: number;
  created_at: string | null;
}

/** GET /admin/overview */
export interface AdminOverview {
  total_users: number;
  total_coaches: number;
  total_athletes: number;
  total_admins: number;
  total_boxes: number;
  boxes_pending: number;
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
