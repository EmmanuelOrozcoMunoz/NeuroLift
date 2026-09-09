import { useState } from "react";
import { useParams } from "react-router-dom";

import { PageHeader } from "@/components/AppShell";
import { IconCheck, IconClock, IconSpark } from "@/components/icons";
import { SetRow } from "@/components/SetRow";
import {
  Badge,
  Button,
  Card,
  EmptyState,
  ErrorState,
  LoadingList,
  Segmented,
  Sheet,
  Stepper,
  Toast,
} from "@/components/ui";
import { longDate, relativeDay } from "@/lib/dates";
import { useAdaptSession, useCompleteSession, useMesocycle } from "@/lib/queries";
import { groupSets, groupSummary, sessionProgress } from "@/lib/sessions";

type Vista = "normal" | "adaptada";

export default function SessionDetail() {
  const { mesocycleId, sessionId } = useParams<{ mesocycleId: string; sessionId: string }>();
  const { data, isPending, error, refetch } = useMesocycle(mesocycleId);

  const [vista, setVista] = useState<Vista>("normal");
  const [sheetAbierta, setSheetAbierta] = useState(false);
  const [minutos, setMinutos] = useState(60);
  const [toast, setToast] = useState<string | null>(null);

  const adaptar = useAdaptSession();
  const completar = useCompleteSession();

  const sesiones = data?.sessions ?? [];
  const objetivo = sesiones.find((session) => session.id === sessionId);
  // Los enlaces siempre apuntan a la sesión original, pero si llegara el id de una adaptada
  // (un enlace viejo, un refresh) se resuelve hacia su original igual.
  const original = objetivo?.parent_session_id
    ? (sesiones.find((session) => session.id === objetivo.parent_session_id) ?? objetivo)
    : objetivo;
  const adaptada = original
    ? sesiones.find((session) => session.parent_session_id === original.id)
    : undefined;

  const activa = vista === "adaptada" && adaptada ? adaptada : original;

  if (isPending) {
    return (
      <>
        <PageHeader title="Sesión" back={`/entrenos/${mesocycleId}`} />
        <LoadingList rows={3} />
      </>
    );
  }

  if (error) {
    return (
      <>
        <PageHeader title="Sesión" back={`/entrenos/${mesocycleId}`} />
        <ErrorState error={error} onRetry={() => void refetch()} />
      </>
    );
  }

  if (!original || !activa) {
    return (
      <>
        <PageHeader title="Sesión" back={`/entrenos/${mesocycleId}`} />
        <EmptyState title="No encontramos esta sesión">
          Puede que tu coach la haya eliminado o reprogramado.
        </EmptyState>
      </>
    );
  }

  const { logged, total } = sessionProgress(activa);
  const completada = activa.status === "completed";
  const grupos = groupSets(activa.sets);

  return (
    <>
      <PageHeader
        title={longDate(activa.scheduled_date)}
        subtitle={`${data?.name ?? "Mi rutina"} · ${relativeDay(activa.scheduled_date)}`}
        back={`/entrenos/${mesocycleId}`}
        action={
          total > 0 ? (
            <Badge tone={completada ? "done" : logged ? "warn" : "neutral"}>
              {logged}/{total}
            </Badge>
          ) : undefined
        }
      />

      {adaptada && (
        <div className="mb-4">
          <Segmented<Vista>
            value={vista}
            onChange={setVista}
            options={[
              { value: "normal", label: "Normal" },
              { value: "adaptada", label: `⏱ ${adaptada.duration_minutes ?? "?"} min` },
            ]}
          />
        </div>
      )}

      {activa.athlete_notes && (
        <Card className="mb-4 border-brand/30 bg-brand-soft/30">
          <p className="text-sm leading-relaxed">{activa.athlete_notes}</p>
        </Card>
      )}

      {grupos.length === 0 ? (
        <EmptyState title="Sin ejercicios asignados">
          Tu coach todavía no cargó los ejercicios de este día.
        </EmptyState>
      ) : (
        <div className="space-y-4">
          {grupos.map((grupo, indiceGrupo) => (
            <Card key={`${grupo.name}-${indiceGrupo}`} className="p-3">
              <div className="mb-2.5 px-1">
                <p className="leading-tight font-bold">{grupo.name}</p>
                <p className="text-xs text-muted">{groupSummary(grupo)}</p>
              </div>
              <div className="space-y-2">
                {grupo.sets.map((set, indiceSerie) => (
                  <SetRow
                    key={set.id}
                    set={set}
                    index={indiceSerie + 1}
                    mesocycleId={mesocycleId!}
                  />
                ))}
              </div>
            </Card>
          ))}
        </div>
      )}

      {/* Adaptar al tiempo disponible: solo desde la sesión original (el backend rechaza
          adaptar una adaptada), y solo si ya hay ejercicios que recortar. */}
      {vista === "normal" && original.sets.length > 0 && (
        <Button variant="secondary" full className="mt-4" onClick={() => setSheetAbierta(true)}>
          <IconClock className="h-5 w-5" />
          {adaptada ? "Cambiar la versión corta" : "¿Tienes menos tiempo hoy?"}
        </Button>
      )}

      {grupos.length > 0 && (
        <Button
          variant={completada ? "secondary" : "done"}
          full
          className="mt-3"
          loading={completar.isPending}
          onClick={() =>
            completar.mutate(
              {
                mesocycleId: mesocycleId!,
                sessionId: activa.id,
                alsoCompleteId: activa.id === original.id ? undefined : original.id,
              },
              { onSuccess: () => setToast("¡Entrenamiento registrado! Buen trabajo 💪") },
            )
          }
        >
          {completada ? (
            <>
              <IconCheck className="h-5 w-5" /> Sesión completada
            </>
          ) : (
            "Terminar entrenamiento"
          )}
        </Button>
      )}

      {logged < total && !completada && (
        <p className="mt-2 text-center text-xs text-muted">
          Te faltan {total - logged} series por registrar. Puedes terminar igual.
        </p>
      )}

      <Sheet open={sheetAbierta} onClose={() => setSheetAbierta(false)} title="¿Cuánto tiempo tienes?">
        <p className="mb-4 text-sm text-muted">
          La IA recorta y reordena la sesión para que quepa en ese tiempo, priorizando lo
          importante. Tu sesión original queda intacta: podrás elegir cuál seguir.
        </p>

        <Stepper value={minutos} onChange={setMinutos} step={5} min={10} max={180} suffix="min" />

        {adaptar.isError && (
          <p className="mt-3 text-sm font-medium text-danger">
            {adaptar.error instanceof Error
              ? adaptar.error.message
              : "No se pudo adaptar la sesión. Intenta de nuevo."}
          </p>
        )}

        <Button
          full
          className="mt-4"
          loading={adaptar.isPending}
          onClick={() =>
            adaptar.mutate(
              { mesocycleId: mesocycleId!, sessionId: original.id, minutes: minutos },
              {
                onSuccess: () => {
                  setSheetAbierta(false);
                  setVista("adaptada");
                  setToast(`Listo: tienes una versión de ${minutos} min.`);
                },
              },
            )
          }
        >
          <IconSpark className="h-5 w-5" />
          {adaptar.isPending ? "Adaptando…" : "Adaptar sesión"}
        </Button>

        {adaptar.isPending && (
          <p className="mt-2 text-center text-xs text-muted">
            Esto puede tardar unos segundos: la IA está rearmando la sesión.
          </p>
        )}
      </Sheet>

      {toast && <Toast message={toast} onDismiss={() => setToast(null)} />}
    </>
  );
}
