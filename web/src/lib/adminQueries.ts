import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import type { UseQueryResult } from "@tanstack/react-query";

import { apiFetch } from "@/lib/api";
import type { AdminOverview, AuditLog, MessageResponse, User, UserRoleUpdatePayload } from "@/lib/types";

export const adminKeys = {
  overview: ["admin", "overview"] as const,
  users: ["admin", "users"] as const,
  logs: ["admin", "logs"] as const,
};

/** Vista completa de la app: conteos globales sin importar de qué coach o atleta sean. */
export function useAdminOverview(): UseQueryResult<AdminOverview> {
  return useQuery({
    queryKey: adminKeys.overview,
    queryFn: () => apiFetch<AdminOverview>("/admin/overview"),
  });
}

/** Listado global de usuarios (todos los roles) — solo un admin lo necesita. */
export function useAllUsers(): UseQueryResult<User[]> {
  return useQuery({
    queryKey: adminKeys.users,
    queryFn: () => apiFetch<User[]>("/users/"),
  });
}

export function useUpdateUserRole() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ userId, role }: { userId: string } & UserRoleUpdatePayload) =>
      apiFetch<User>(`/admin/users/${userId}/role`, { method: "PUT", body: { role } }),
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: adminKeys.users }),
  });
}

/** Fuerza la revocación de TODOS los tokens de un usuario (todos sus dispositivos). */
export function useRevokeUserSessions() {
  return useMutation({
    mutationFn: (userId: string) =>
      apiFetch<MessageResponse>(`/admin/users/${userId}/revoke-sessions`, { method: "POST" }),
  });
}

/** Historial de eventos de seguridad (logins fallidos, cambios de rol, revocaciones...),
 *  más reciente primero. */
export function useAuditLogs(): UseQueryResult<AuditLog[]> {
  return useQuery({
    queryKey: adminKeys.logs,
    queryFn: () => apiFetch<AuditLog[]>("/admin/logs"),
  });
}
