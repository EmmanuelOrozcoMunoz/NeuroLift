import { useState } from "react";
import { useNavigate, useParams } from "react-router-dom";

import { PageHeader } from "@/components/AppShell";
import { CoverThumbnail } from "@/components/CoverImage";
import { Badge, Button, Card, EmptyState, ErrorState, Field, LoadingList, Toast } from "@/components/ui";
import { useCurrentUser } from "@/lib/auth";
import { blockLabel } from "@/lib/blocks";
import { formatPrice, todayIso } from "@/lib/dates";
import { useAcquirePlan, usePlanCatalog, usePlanDetail } from "@/lib/queries";
import { groupSets, groupSummary } from "@/lib/sessions";
import { useWeightUnit } from "@/lib/units";

export default function PlanDetail() {
  const { planId } = useParams<{ planId: string }>();
  const navigate = useNavigate();
  const user = useCurrentUser();

  const catalog = usePlanCatalog();
  const detail = usePlanDetail(planId);
  const acquire = useAcquirePlan(user.id);
  const unit = useWeightUnit();

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

  // Si el plan no es tuyo (el caso normal para un atleta navegando el catálogo), el backend
  // manda una VISTA PREVIA sin ejercicios/series/pesos — mostrar la programación completa antes
  // de comprarlo no tendría sentido comercial. Solo el autor/admin recibe el detalle completo.
  const esVistaPrevia = detail.data?.is_preview ?? true;
  const totalDias = detail.data?.sessions.length ?? 0;

  return (
    <>
      <PageHeader title={resumen?.name ?? detail.data?.name ?? "Plan"} back="/planes" />

      {resumen?.has_cover_image && (
        <CoverThumbnail
          coverPath={`/plans/${planId}/cover`}
          hasImage
          className="mb-4 h-40 w-full rounded-2xl"
        />
      )}

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

      <h2 className="mt-2 mb-1 text-sm font-semibold tracking-wide text-muted uppercase">
        Contenido del plan
      </h2>
      {esVistaPrevia && (
        <p className="mb-2 text-xs text-muted">
          Vista previa — al adquirirlo verás cada ejercicio, serie y peso exacto.
        </p>
      )}

      {totalDias === 0 ? (
        <EmptyState title="Este plan todavía no tiene ejercicios cargados" />
      ) : detail.data && detail.data.is_preview ? (
        <div className="space-y-3">
          {[...detail.data.sessions]
            .sort((a, b) => (a.day_offset ?? 0) - (b.day_offset ?? 0))
            .map((sesion) => {
              const dia = (sesion.day_offset ?? 0) + 1;
              return (
                <Card key={sesion.id}>
                  <div className="flex items-center justify-between gap-2">
                    <p className="font-bold">Día {dia}</p>
                    <span className="text-xs text-muted">
                      {sesion.exercise_count} ejercicio{sesion.exercise_count === 1 ? "" : "s"}
                    </span>
                  </div>
                  {sesion.blocks.length > 0 && (
                    <div className="mt-2 flex flex-wrap gap-1.5">
                      {sesion.blocks.map((b) => (
                        <Badge key={b}>{blockLabel(b)}</Badge>
                      ))}
                    </div>
                  )}
                </Card>
              );
            })}
        </div>
      ) : detail.data ? (
        <div className="space-y-3">
          {[...detail.data.sessions]
            .sort((a, b) => (a.day_offset ?? 0) - (b.day_offset ?? 0))
            .map((sesion) => {
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
                          <span className="text-muted">— {groupSummary(grupo, unit)}</span>
                        </p>
                      ))}
                    </div>
                  )}
                </Card>
              );
            })}
        </div>
      ) : null}

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
