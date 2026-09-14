import { useState } from "react";

import { PageHeader } from "@/components/AppShell";
import { Badge, Button, Card, ErrorState, LoadingList, Toast } from "@/components/ui";
import { useAllUsers, useRevokeUserSessions, useUpdateUserRole } from "@/lib/adminQueries";
import { useCurrentUser } from "@/lib/auth";
import type { Role, User } from "@/lib/types";

const ROLES: Role[] = ["athlete", "coach", "admin"];
const ROLE_LABEL: Record<Role, string> = { athlete: "Atleta", coach: "Coach", admin: "Admin" };

type ToastFn = (message: string, tone?: "done" | "danger") => void;

function UserRow({ user, onToast }: { user: User; onToast: ToastFn }) {
  const me = useCurrentUser();
  const [draftRole, setDraftRole] = useState<Role>(user.role);
  const updateRole = useUpdateUserRole();
  const revokeSessions = useRevokeUserSessions();
  const dirty = draftRole !== user.role;

  return (
    <Card className="space-y-3">
      <div className="flex items-center justify-between gap-3">
        <div className="min-w-0">
          <p className="truncate font-semibold">{user.full_name}</p>
          <p className="truncate text-sm text-muted">{user.email}</p>
        </div>
        <Badge tone="brand">{ROLE_LABEL[user.role]}</Badge>
      </div>

      <div className="flex items-center gap-2">
        <select
          value={draftRole}
          onChange={(e) => setDraftRole(e.target.value as Role)}
          disabled={user.id === me.id}
          className="min-h-11 grow rounded-xl border border-line bg-surface-2 px-3.5 text-sm disabled:opacity-50"
        >
          {ROLES.map((role) => (
            <option key={role} value={role}>
              {ROLE_LABEL[role]}
            </option>
          ))}
        </select>

        {dirty && (
          <Button
            variant="secondary"
            loading={updateRole.isPending}
            onClick={() =>
              updateRole.mutate(
                { userId: user.id, role: draftRole },
                {
                  onSuccess: () => onToast(`Rol de ${user.full_name} actualizado a '${ROLE_LABEL[draftRole]}'`),
                  onError: (err) => {
                    setDraftRole(user.role);
                    onToast(err instanceof Error ? err.message : "Error al actualizar el rol.", "danger");
                  },
                },
              )
            }
          >
            Guardar
          </Button>
        )}

        <Button
          variant="danger"
          loading={revokeSessions.isPending}
          onClick={() =>
            revokeSessions.mutate(user.id, {
              onSuccess: (res) => onToast(res.message),
              onError: () => onToast("Error al revocar las sesiones.", "danger"),
            })
          }
        >
          Revocar sesiones
        </Button>
      </div>
    </Card>
  );
}

export default function AdminUsers() {
  const { data, isPending, error, refetch } = useAllUsers();
  const [toast, setToast] = useState<{ message: string; tone: "done" | "danger" } | null>(null);
  const showToast: ToastFn = (message, tone = "done") => setToast({ message, tone });

  return (
    <>
      <PageHeader title="Todos los usuarios" subtitle="Cambia roles o revoca sesiones activas" />

      {isPending && <LoadingList rows={4} />}
      {!isPending && error && <ErrorState error={error} onRetry={() => void refetch()} />}

      <div className="space-y-3">
        {data?.map((user) => <UserRow key={user.id} user={user} onToast={showToast} />)}
      </div>

      {toast && <Toast message={toast.message} tone={toast.tone} onDismiss={() => setToast(null)} />}
    </>
  );
}
