import { IconCheck } from "@/components/icons";
import { Badge, Card, cx } from "@/components/ui";
import { usePricing } from "@/lib/boxQueries";
import { formatPrice, parseUtcDateTime } from "@/lib/dates";
import type { BoxDetail, PlanCode, SubscriptionStatus } from "@/lib/types";

export const SUBSCRIPTION_LABEL: Record<SubscriptionStatus, string> = {
  trial: "Prueba gratis",
  active: "Al día",
  expired: "Vencida",
};
export const SUBSCRIPTION_TONE: Record<SubscriptionStatus, "brand" | "done" | "warn"> = {
  trial: "brand",
  active: "done",
  expired: "warn",
};

function longDay(iso: string): string {
  return parseUtcDateTime(iso).toLocaleDateString("es", { day: "numeric", month: "long", year: "numeric" });
}

function daysLeft(iso: string): number {
  return Math.max(0, Math.ceil((parseUtcDateTime(iso).getTime() - Date.now()) / 86_400_000));
}

/** Tabla de planes (landing). Los precios salen del backend (core/billing.py). */
export function PricingGrid({ highlight = "pro" }: { highlight?: PlanCode }) {
  const { data } = usePricing();
  if (!data) return null;

  return (
    <>
      <div className="grid gap-3 md:grid-cols-3">
        {data.plans.map((plan) => (
          <div
            key={plan.code}
            className={cx(
              "rounded-2xl border bg-surface p-5",
              plan.code === highlight ? "border-brand" : "border-line",
            )}
          >
            <div className="flex items-center justify-between gap-2">
              <p className="font-bold">{plan.name}</p>
              {plan.code === highlight && <Badge tone="brand">Popular</Badge>}
            </div>
            <p className="mt-3">
              <span className="text-3xl font-bold tracking-tight">{formatPrice(plan.monthly_price)}</span>
              <span className="text-sm text-muted"> {plan.currency}/mes</span>
            </p>
            <p className="mt-2 text-sm text-muted">
              {plan.max_athletes ? `Hasta ${plan.max_athletes} atletas` : "Atletas ilimitados"}
            </p>
          </div>
        ))}
      </div>
      <p className="mt-3 flex items-center gap-2 text-sm text-muted">
        <IconCheck className="h-4 w-4 text-done" />
        {data.trial_days} días de prueba gratis. El mismo precio para boxes y coaches independientes.
      </p>
    </>
  );
}

/** Estado de la suscripción para el dueño de la cuenta (box o coach independiente). */
export function SubscriptionCard({ account }: { account: BoxDetail }) {
  const { data: pricing } = usePricing();
  if (!account.subscription_status || !account.plan) return null;

  const plan = pricing?.plans.find((p) => p.code === account.plan);
  const used = account.athletes_count ?? 0;
  const limit = account.max_athletes;
  const full = limit !== null && used >= limit;
  const status = account.subscription_status;

  let dateLine: string | null = null;
  if (status === "trial" && account.trial_ends_at) {
    const left = daysLeft(account.trial_ends_at);
    dateLine = `Te quedan ${left} ${left === 1 ? "día" : "días"} de prueba (hasta el ${longDay(account.trial_ends_at)}).`;
  } else if (status === "active" && account.paid_until) {
    dateLine = `Pagado hasta el ${longDay(account.paid_until)}.`;
  } else if (status === "expired") {
    dateLine = "Tus atletas actuales siguen entrenando, pero no se pueden sumar atletas nuevos hasta renovar.";
  }

  return (
    <Card>
      <div className="flex items-center justify-between gap-2">
        <p className="font-bold">Tu plan</p>
        <Badge tone={SUBSCRIPTION_TONE[status]}>{SUBSCRIPTION_LABEL[status]}</Badge>
      </div>
      <p className="mt-2 text-lg font-bold">
        {plan?.name ?? account.plan}
        {plan && (
          <span className="text-sm font-normal text-muted">
            {" "}
            · {formatPrice(plan.monthly_price)} {plan.currency}/mes
          </span>
        )}
      </p>
      {dateLine && <p className={cx("mt-1 text-sm", status === "expired" ? "text-warn" : "text-muted")}>{dateLine}</p>}

      <div className="mt-3">
        <div className="flex justify-between text-sm">
          <span className="text-muted">Atletas</span>
          <span className={cx("font-semibold tabular-nums", full && "text-warn")}>
            {used}
            {limit !== null ? ` / ${limit}` : ""}
          </span>
        </div>
        {limit !== null && (
          <div className="mt-1.5 h-2 overflow-hidden rounded-full bg-surface-2">
            <div
              className={cx("h-full rounded-full", full ? "bg-warn" : "bg-brand")}
              style={{ width: `${Math.min(100, (used / limit) * 100)}%` }}
            />
          </div>
        )}
        {full && (
          <p className="mt-2 text-sm text-warn">Llegaste al límite de tu plan: sube de plan para sumar más atletas.</p>
        )}
      </div>

      <p className="mt-3 text-xs text-muted">Para pagar o cambiar de plan, escríbele al equipo de NeuroLift.</p>
    </Card>
  );
}
