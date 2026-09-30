import { Link } from "react-router-dom";
import type { ReactNode } from "react";

import { PageHeader } from "@/components/AppShell";
import { IconChevronRight, IconClock, IconUsers } from "@/components/icons";
import { ProgressRing } from "@/components/ProgressRing";
import { SUBSCRIPTION_LABEL } from "@/components/Subscription";
import { ErrorState, Skeleton, cx } from "@/components/ui";
import { useMyBox } from "@/lib/boxQueries";
import { useOwnerDashboard } from "@/lib/classQueries";
import { parseUtcDateTime } from "@/lib/dates";

/** Aviso solo cuando hace falta actuar: vencida, o prueba con 3 días o menos. */
function subscriptionNeedsAttention(box: { subscription_status: string | null; trial_ends_at: string | null }): boolean {
  if (box.subscription_status === "expired") return true;
  if (box.subscription_status === "trial" && box.trial_ends_at) {
    return parseUtcDateTime(box.trial_ends_at).getTime() - Date.now() <= 3 * 86_400_000;
  }
  return false;
}

const REASON: Record<string, string> = {
  nuevo: "Se unió esta semana",
  inactivo: "Sin entrenar hace 2+ semanas",
  sin_coach: "Sin coach",
};

/**
 * Inicio del dueño del box: cómo va el negocio. La configuración (foto, color, link de
 * invitación, datos) vive en Box → Ajustes.
 */
export default function BoxDashboard() {
  const dashboard = useOwnerDashboard();
  const box = useMyBox();
  const d = dashboard.data;

  return (
    <>
      <PageHeader title={box.data?.name ?? "Tu box"} subtitle="Resumen de esta semana" />

      {dashboard.isPending && <DashboardSkeleton />}
      {dashboard.error && <ErrorState error={dashboard.error} onRetry={() => void dashboard.refetch()} />}

      {d && (
        <div className="space-y-8">
          {/* Cifra principal: cuántos atletas entrenaron de los que tiene */}
          <section className="flex items-center gap-5 rounded-3xl bg-surface p-5">
            <ProgressRing
              value={d.athletes_trained_this_week}
              max={Math.max(1, d.athletes_total)}
              size={104}
              label={`${d.athletes_trained_this_week} de ${d.athletes_total} atletas entrenaron esta semana`}
            >
              <span className="num text-metric-sm">
                {d.athletes_trained_this_week}
                <span className="text-muted">/{d.athletes_total}</span>
              </span>
            </ProgressRing>
            <div className="min-w-0">
              <p className="label-caps">Entrenaron esta semana</p>
              <p className="mt-2 text-sm text-muted">
                <span className="num text-lg font-extrabold text-fg">{d.sessions_completed_this_week}</span>{" "}
                {d.sessions_completed_this_week === 1 ? "sesión completada" : "sesiones completadas"}
              </p>
            </div>
          </section>

          <section className="grid grid-cols-2 gap-3">
            <Metric
              value={d.athletes_total}
              suffix={d.max_athletes ? `/${d.max_athletes}` : undefined}
              label="Atletas en el plan"
              warn={d.max_athletes !== null && d.athletes_total >= d.max_athletes}
            />
            <Metric value={d.classes_today} label="Clases hoy" to="/clases" />
            <Metric
              value={d.unprogrammed_classes_next_7_days}
              label="Clases sin programar (7 días)"
              warn={d.unprogrammed_classes_next_7_days > 0}
              to="/clases"
            />
            <Metric value={d.athletes_without_coach} label="Sin coach personal" to="/box/equipo" />
          </section>

          {box.data && subscriptionNeedsAttention(box.data) && (
            <Link to="/box/ajustes" className="press flex items-center gap-3 rounded-2xl bg-warn-soft p-4 text-warn">
              <IconClock className="h-5 w-5 shrink-0" />
              <span className="grow text-sm font-semibold">
                {box.data.subscription_status === "expired"
                  ? "Tu suscripción venció: no entran atletas nuevos"
                  : `${SUBSCRIPTION_LABEL.trial}: quedan pocos días`}
              </span>
              <IconChevronRight className="h-5 w-5" />
            </Link>
          )}

          <section>
            <div className="mb-3 flex items-center justify-between">
              <h2 className="label-caps">Equipo</h2>
              <Link to="/box/equipo" className="flex min-h-touch items-center text-sm font-semibold text-muted active:text-fg">
                Gestionar
              </Link>
            </div>
            <div className="overflow-hidden rounded-2xl bg-surface">
              {d.coaches.map((c) => (
                <div key={c.id} className="flex items-center gap-3 px-4 py-3 [&+div]:border-t [&+div]:border-line">
                  <div className="min-w-0 grow">
                    <p className="truncate font-semibold">
                      {c.full_name}
                      {c.role === "owner" && <span className="font-normal text-muted"> · dueño</span>}
                    </p>
                    <p className="text-sm text-muted">
                      {c.classes} {c.classes === 1 ? "clase" : "clases"}
                    </p>
                  </div>
                  <div className="text-right">
                    <p className="num text-lg font-extrabold">
                      {c.trained_this_week}
                      <span className="text-sm text-muted">/{c.athletes}</span>
                    </p>
                    <p className="text-xs text-muted">atletas activos</p>
                  </div>
                </div>
              ))}
            </div>
          </section>

          {d.attention.length > 0 && (
            <section>
              <h2 className="label-caps mb-3">Para revisar</h2>
              <div className="overflow-hidden rounded-2xl bg-surface">
                {d.attention.map((a) => (
                  <Link
                    key={a.id}
                    to={`/coach/atletas/${a.id}`}
                    className="press flex min-h-touch items-center gap-3 px-4 py-3 active:bg-surface-2 [&+a]:border-t [&+a]:border-line"
                  >
                    <IconUsers className="h-5 w-5 shrink-0 text-muted" />
                    <span className="min-w-0 grow">
                      <span className="block truncate font-semibold">{a.full_name}</span>
                      <span className={cx("block text-sm", a.reason === "inactivo" ? "text-warn" : "text-muted")}>
                        {REASON[a.reason]}
                        {a.last_completed_at &&
                          ` · última el ${parseUtcDateTime(a.last_completed_at).toLocaleDateString("es", { day: "numeric", month: "short" })}`}
                      </span>
                    </span>
                    <IconChevronRight className="h-5 w-5 shrink-0 text-muted" />
                  </Link>
                ))}
              </div>
            </section>
          )}
        </div>
      )}
    </>
  );
}

function Metric({
  value,
  suffix,
  label,
  warn = false,
  to,
}: {
  value: number;
  suffix?: string;
  label: string;
  warn?: boolean;
  to?: string;
}) {
  const body: ReactNode = (
    <>
      <p className={cx("num text-metric", warn && "text-warn")}>
        {value}
        {suffix && <span className="text-metric-sm text-muted">{suffix}</span>}
      </p>
      <p className="mt-2 text-sm leading-snug text-muted">{label}</p>
    </>
  );
  return to ? (
    <Link to={to} className="press block rounded-2xl bg-surface p-4 active:bg-surface-2">
      {body}
    </Link>
  ) : (
    <div className="rounded-2xl bg-surface p-4">{body}</div>
  );
}

function DashboardSkeleton() {
  return (
    <div className="space-y-8" aria-busy="true" aria-label="Cargando resumen">
      <div className="flex items-center gap-5 rounded-3xl bg-surface p-5">
        <Skeleton className="h-[104px] w-[104px] rounded-full" />
        <div className="grow space-y-3">
          <Skeleton className="h-3 w-32" />
          <Skeleton className="h-5 w-40" />
        </div>
      </div>
      <div className="grid grid-cols-2 gap-3">
        {[0, 1, 2, 3].map((i) => (
          <div key={i} className="space-y-3 rounded-2xl bg-surface p-4">
            <Skeleton className="h-9 w-16" />
            <Skeleton className="h-4 w-24" />
          </div>
        ))}
      </div>
    </div>
  );
}
