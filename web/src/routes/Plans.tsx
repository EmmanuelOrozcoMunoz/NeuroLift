import { Link } from "react-router-dom";

import { PageHeader } from "@/components/AppShell";
import { IconChevronRight, IconStore } from "@/components/icons";
import { Badge, EmptyState, ErrorState, LoadingList } from "@/components/ui";
import { formatPrice } from "@/lib/dates";
import { usePlanCatalog } from "@/lib/queries";

export default function Plans() {
  const { data, isPending, error, refetch } = usePlanCatalog();

  return (
    <>
      <PageHeader title="Planes disponibles" subtitle="Hechos por entrenadores, listos para seguir solo" />

      {isPending && <LoadingList rows={3} />}
      {!isPending && error && <ErrorState error={error} onRetry={() => void refetch()} />}

      {!isPending && !error && (data?.length ?? 0) === 0 && (
        <EmptyState icon={<IconStore className="h-10 w-10" />} title="Todavía no hay planes publicados">
          Vuelve pronto — los entrenadores están armando planes que podrás adquirir por tu cuenta.
        </EmptyState>
      )}

      <div className="space-y-3">
        {data?.map((plan) => (
          <Link
            key={plan.id}
            to={`/planes/${plan.id}`}
            className="block rounded-2xl border border-line bg-surface p-4 active:bg-surface-2"
          >
            <div className="flex items-start gap-3">
              <div className="min-w-0 grow">
                <div className="flex flex-wrap items-center gap-2">
                  <span className="font-bold">{plan.name}</span>
                  {plan.level && <Badge>{plan.level}</Badge>}
                </div>
                <p className="mt-1 text-sm text-muted">
                  {plan.discipline} · {plan.weeks_count} sem · {plan.sessions_per_week}/sem
                </p>
                <p className="mt-1.5 text-sm font-semibold text-brand">{formatPrice(plan.price)}</p>
              </div>
              <IconChevronRight className="mt-1 h-5 w-5 shrink-0 text-muted" />
            </div>
          </Link>
        ))}
      </div>
    </>
  );
}
