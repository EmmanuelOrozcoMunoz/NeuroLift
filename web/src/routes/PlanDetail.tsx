import { useState } from "react";
import { useNavigate, useParams } from "react-router-dom";

import { PageHeader } from "@/components/AppShell";
import { Badge, Button, Card, EmptyState, ErrorState, Field, LoadingList, Toast } from "@/components/ui";
import { useCurrentUser } from "@/lib/auth";
import { formatPrice, todayIso } from "@/lib/dates";
import { useAcquirePlan, usePlanCatalog, usePlanDetail } from "@/lib/queries";
import { groupSets, groupSummary } from "@/lib/sessions";

export default function PlanDetail() {
  const { planId } = useParams<{ planId: string }>();
  const navigate = useNavigate();
  const user = useCurrentUser();

  const catalog = usePlanCatalog();
  const detail = usePlanDetail(planId);
  const acquire = useAcquirePlan(user.id);

  const [startDate, setStartDate] = useState(todayIso());
  const [toast, setToast] = useState<string | null>(null);

  const resumen = catalog.data?.find((plan) => plan.id === planId);

  if (detail.isPending || catalog.isPending) {
    return (
      <>
        <PageHeader title="Plan" back="/planes" />
        <LoadingList rows={4} />
      </>
    );
  }

  if (detail.error) {
    return (
      <>
        <PageHeader title="Plan" back="/planes" />
        <ErrorState error={detail.error} onRetry={() => void detail.refetch()} />
      </>
    );
  }

  const sesiones = [...(detail.data?.sessions ?? [])].sort(
    (a, b) => (a.day_offset ?? 0) - (b.day_offset ?? 0),
  );

  return (
    <>
      <PageHeader title={resumen?.name ?? detail.data?.name ?? "Plan"} back="/planes" />

      {resumen && (
        <Card className="mb-4">
          <div className="flex flex-wrap items-center gap-2">
            {resumen.level && <Badge>{resumen.level}</Badge>}
            <Badge tone="brand">{resumen.discipline}</Badge>
          </div>
          {resumen.description && <p className="mt-2 text-sm text-muted">{resumen.description}</p>}

          <div className="mt-3 grid grid-cols-3 gap-2 text-center">
            <div className="rounded-xl bg-surface-2 py-2.5">
              <p className="text-lg font-bold">{resumen.weeks_count}</p>
              <p className="text-xs text-muted">semanas</p>
            </div>
            <div className="rounded-xl bg-surface-2 py-2.5">
              <p className="text-lg font-bold">{resumen.sessions_per_week}</p>
              <p className="text-xs text-muted">sesiones/sem</p>
            </div>
            <div className="rounded-xl bg-surface-2 py-2.5">
              <p className="text-lg font-bold text-brand">{formatPrice(resumen.price)}</p>
              <p className="text-xs text-muted">precio</p>
            </div>
          </div>

          {resumen.coach_name && (
            <p className="mt-3 text-xs text-muted">Creado por {resumen.coach_name}</p>
          )}
        </Card>
      )}

      <h2 className="mt-2 mb-2 text-sm font-semibold tracking-wide text-muted uppercase">
        Contenido del plan
      </h2>

      {sesiones.length === 0 ? (
        <EmptyState title="Este plan todavía no tiene ejercicios cargados" />
      ) : (
        <div className="space-y-3">
          {sesiones.map((sesion) => {
            const grupos = groupSets(sesion.sets);
            const dia = (sesion.day_offset ?? 0) + 1;
            return (
              <Card key={sesion.id}>
                <p className="mb-2 font-bold">Día {dia}</p>
                {grupos.length === 0 ? (
                  <p className="text-sm text-muted">Sin ejercicios</p>
                ) : (
                  <div className="space-y-1.5">
                    {grupos.map((grupo, index) => (
                      <p key={`${grupo.name}-${index}`} className="text-sm">
                        <span className="font-semibold">{grupo.name}</span>{" "}
                        <span className="text-muted">— {groupSummary(grupo)}</span>
                      </p>
                    ))}
                  </div>
                )}
              </Card>
            );
          })}
        </div>
      )}

      <Card className="mt-5">
        <p className="mb-3 font-bold">Adquirir este plan</p>
        <Field
          label="¿Qué día quieres empezar?"
          type="date"
          value={startDate}
          onChange={(event) => setStartDate(event.target.value)}
        />
        <p className="mt-2 text-xs text-muted">
          La primera sesión caerá exactamente en esta fecha; las cargas se calculan con tus
          propias marcas registradas.
        </p>

        {acquire.isError && (
          <p className="mt-3 text-sm font-medium text-danger">
            {acquire.error instanceof Error ? acquire.error.message : "No se pudo adquirir el plan."}
          </p>
        )}

        <Button
          full
          className="mt-4"
          loading={acquire.isPending}
          onClick={() =>
            acquire.mutate(
              { planId: planId!, startDate },
              {
                onSuccess: (response) => {
                  setToast(response.message ?? "¡Plan adquirido!");
                  setTimeout(() => navigate("/entrenos"), 900);
                },
              },
            )
          }
        >
          Adquirir plan
        </Button>
      </Card>

      {toast && <Toast message={toast} onDismiss={() => setToast(null)} />}
    </>
  );
}
