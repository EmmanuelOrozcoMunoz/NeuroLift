import { useState } from "react";

import { PageHeader } from "@/components/AppShell";
import { BoxLogo } from "@/components/BoxLogo";
import { Badge, Button, Card, EmptyState, ErrorState, LoadingList, Segmented, Toast } from "@/components/ui";
import { useAdminBoxes, useUpdateBoxStatus } from "@/lib/boxQueries";
import { monthYear } from "@/lib/dates";
import type { AdminBoxRow, BoxStatus } from "@/lib/types";

const STATUS_LABEL: Record<BoxStatus, string> = {
  pending: "Pendiente",
  active: "Activo",
  rejected: "Rechazado",
  suspended: "Suspendido",
};
const STATUS_TONE: Record<BoxStatus, "warn" | "done" | "neutral"> = {
  pending: "warn",
  active: "done",
  rejected: "neutral",
  suspended: "neutral",
};

type Filter = "pending" | "active" | "all";
type ToastState = { message: string; tone: "done" | "danger" } | null;

export default function AdminBoxes() {
  const { data, isPending, error, refetch } = useAdminBoxes();
  const [filter, setFilter] = useState<Filter>("pending");
  const [toast, setToast] = useState<ToastState>(null);

  const pendingCount = data?.filter((b) => b.status === "pending").length ?? 0;
  const visible = (data ?? []).filter((b) => filter === "all" || b.status === filter);

  return (
    <>
      <PageHeader title="Boxes" subtitle={pendingCount ? `${pendingCount} por aprobar` : "Clientes de la plataforma"} />

      <Segmented
        options={[
          { value: "pending", label: `Pendientes${pendingCount ? ` (${pendingCount})` : ""}` },
          { value: "active", label: "Activos" },
          { value: "all", label: "Todos" },
        ]}
        value={filter}
        onChange={setFilter}
      />

      <div className="mt-4 space-y-3">
        {isPending && <LoadingList rows={3} />}
        {!isPending && error && <ErrorState error={error} onRetry={() => void refetch()} />}
        {!isPending && !error && visible.length === 0 && (
          <EmptyState title={filter === "pending" ? "No hay solicitudes pendientes" : "No hay boxes aquí"} />
        )}
        {visible.map((box) => (
          <BoxRow key={box.id} box={box} onToast={(message, tone = "done") => setToast({ message, tone })} />
        ))}
      </div>

      {toast && <Toast message={toast.message} tone={toast.tone} onDismiss={() => setToast(null)} />}
    </>
  );
}

function BoxRow({ box, onToast }: { box: AdminBoxRow; onToast: (message: string, tone?: "done" | "danger") => void }) {
  const update = useUpdateBoxStatus();
  const place = [box.city, box.state, box.country].filter(Boolean).join(", ");

  function change(status: BoxStatus, confirmText?: string) {
    if (confirmText && !window.confirm(confirmText)) return;
    update.mutate(
      { boxId: box.id, status },
      {
        onSuccess: (res) => onToast(res.message),
        onError: (err) => onToast(err instanceof Error ? err.message : "No se pudo actualizar.", "danger"),
      },
    );
  }

  return (
    <Card>
      <div className="flex items-start gap-3">
        <BoxLogo boxId={box.id} name={box.name} hasLogo={box.has_logo} className="h-12 w-12" />
        <div className="min-w-0 grow">
          <div className="flex items-center justify-between gap-2">
            <p className="truncate font-bold">{box.name}</p>
            <Badge tone={STATUS_TONE[box.status]}>{STATUS_LABEL[box.status]}</Badge>
          </div>
          {place && <p className="truncate text-sm text-muted">{place}</p>}
          <p className="mt-1 truncate text-sm">
            {box.owner_name ?? "Sin dueño"} <span className="text-muted">· {box.owner_email}</span>
          </p>
          <p className="mt-0.5 text-xs text-muted">
            {box.coaches_count} coaches · {box.athletes_count} atletas
            {box.created_at && ` · desde ${monthYear(box.created_at)}`}
          </p>
        </div>
      </div>

      <div className="mt-3 flex gap-2">
        {box.status !== "active" && (
          <Button variant="done" className="grow" loading={update.isPending} onClick={() => change("active")}>
            {box.status === "pending" ? "Aprobar" : "Activar"}
          </Button>
        )}
        {box.status === "pending" && (
          <Button variant="danger" disabled={update.isPending} onClick={() => change("rejected", `¿Rechazar la solicitud de ${box.name}?`)}>
            Rechazar
          </Button>
        )}
        {box.status === "active" && (
          <Button
            variant="danger"
            className="grow"
            loading={update.isPending}
            onClick={() =>
              change("suspended", `Sus ${box.coaches_count} coaches y ${box.athletes_count} atletas perderán acceso de inmediato. ¿Suspender ${box.name}?`)
            }
          >
            Suspender
          </Button>
        )}
      </div>
    </Card>
  );
}
