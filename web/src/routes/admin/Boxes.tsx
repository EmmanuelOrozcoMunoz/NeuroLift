import { useState } from "react";

import { PageHeader } from "@/components/AppShell";
import { BoxLogo } from "@/components/BoxLogo";
import { SUBSCRIPTION_LABEL, SUBSCRIPTION_TONE } from "@/components/Subscription";
import { Badge, Button, Card, EmptyState, ErrorState, LoadingList, Segmented, Toast } from "@/components/ui";
import { useAdminBoxes, usePricing, useRegisterPayment, useUpdateBoxPlan, useUpdateBoxStatus } from "@/lib/boxQueries";
import { formatPrice, monthYear, parseUtcDateTime } from "@/lib/dates";
import type { AdminBoxRow, BoxStatus, PlanCode } from "@/lib/types";

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
      <PageHeader title="Cuentas" subtitle={pendingCount ? `${pendingCount} por aprobar` : "Boxes y coaches independientes"} />

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
          <EmptyState title={filter === "pending" ? "No hay solicitudes pendientes" : "No hay cuentas aquí"} />
        )}
        {visible.map((box) => (
          <BoxRow key={box.id} box={box} onToast={(message, tone = "done") => setToast({ message, tone })} />
        ))}
      </div>

      {toast && <Toast message={toast.message} tone={toast.tone} onDismiss={() => setToast(null)} />}
    </>
  );
}

function shortDay(iso: string): string {
  return parseUtcDateTime(iso).toLocaleDateString("es", { day: "numeric", month: "short", year: "numeric" });
}

function BoxRow({ box, onToast }: { box: AdminBoxRow; onToast: (message: string, tone?: "done" | "danger") => void }) {
  const update = useUpdateBoxStatus();
  const updatePlan = useUpdateBoxPlan();
  const payment = useRegisterPayment();
  const { data: pricing } = usePricing();
  const isCoach = box.kind === "coach";
  const place = [box.city, box.state, box.country].filter(Boolean).join(", ");
  const plan = pricing?.plans.find((p) => p.code === box.plan);
  const overLimit = box.max_athletes !== null && box.athletes_count >= box.max_athletes;

  const subscriptionLine =
    box.subscription_status === "active" && box.paid_until
      ? `Pagado hasta el ${shortDay(box.paid_until)}`
      : box.subscription_status === "trial" && box.trial_ends_at
        ? `Prueba hasta el ${shortDay(box.trial_ends_at)}`
        : box.paid_until
          ? `Venció el ${shortDay(box.paid_until)}`
          : box.trial_ends_at
            ? `La prueba terminó el ${shortDay(box.trial_ends_at)}`
            : "Sin prueba ni pagos todavía";

  const onResult = {
    onSuccess: (res: { message: string }) => onToast(res.message),
    onError: (err: unknown) => onToast(err instanceof Error ? err.message : "No se pudo actualizar.", "danger"),
  };

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
          <p className="truncate text-sm text-muted">{isCoach ? "Coach independiente" : place || "Box"}</p>
          {!isCoach && (
            <p className="mt-1 truncate text-sm">
              {box.owner_name ?? "Sin dueño"} <span className="text-muted">· {box.owner_email}</span>
            </p>
          )}
          {isCoach && <p className="mt-1 truncate text-sm text-muted">{box.owner_email}</p>}
          <p className="mt-0.5 text-xs text-muted">
            {!isCoach && `${box.coaches_count} coaches · `}
            <span className={overLimit ? "font-semibold text-warn" : undefined}>
              {box.athletes_count}
              {box.max_athletes !== null && ` / ${box.max_athletes}`} atletas
            </span>
            {box.created_at && ` · desde ${monthYear(box.created_at)}`}
          </p>
        </div>
      </div>

      {box.status === "active" && (
        <div className="mt-3 rounded-xl bg-surface-2 p-3">
          <div className="flex items-center justify-between gap-2">
            <p className="text-sm font-semibold">Suscripción</p>
            <Badge tone={SUBSCRIPTION_TONE[box.subscription_status]}>{SUBSCRIPTION_LABEL[box.subscription_status]}</Badge>
          </div>
          <p className="mt-1 text-xs text-muted">{subscriptionLine}</p>
          <div className="mt-2 flex gap-2">
            <select
              value={box.plan}
              disabled={updatePlan.isPending}
              onChange={(event) => updatePlan.mutate({ boxId: box.id, plan: event.target.value as PlanCode }, onResult)}
              className="min-h-11 grow rounded-xl border border-line bg-surface px-3 text-sm disabled:opacity-60"
              aria-label={`Plan de ${box.name}`}
            >
              {pricing?.plans.map((p) => (
                <option key={p.code} value={p.code}>
                  {p.name} · {formatPrice(p.monthly_price)}
                </option>
              )) ?? <option value={box.plan}>{box.plan}</option>}
            </select>
            <Button
              variant="secondary"
              loading={payment.isPending}
              onClick={() => {
                const monto = plan ? ` de ${formatPrice(plan.monthly_price)} ${plan.currency}` : "";
                if (!window.confirm(`¿Registrar un pago de 1 mes${monto} para ${box.name}?`)) return;
                payment.mutate({ boxId: box.id, months: 1 }, onResult);
              }}
            >
              + 1 mes pagado
            </Button>
          </div>
        </div>
      )}

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
