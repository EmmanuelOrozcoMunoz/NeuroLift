import { useState } from "react";
import { useParams } from "react-router-dom";

import { PageHeader } from "@/components/AppShell";
import { IconCheck, IconClock, IconSpark } from "@/components/icons";
import { SetRow } from "@/components/SetRow";
import { WodTimer } from "@/components/WodTimer";
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
import { formatSeconds, longDate, relativeDay } from "@/lib/dates";
import { useAdaptSession, useCompleteSession, useMesocycle } from "@/lib/queries";
import { groupByBlock, groupSummary, sessionProgress } from "@/lib/sessions";
import { useWeightUnit } from "@/lib/units";
import { WOD_FORMAT_LABELS, formatWodResult } from "@/lib/wod";
import type { SessionCompletePayload } from "@/lib/types";

type Vista = "normal" | "adaptada";

export default function SessionDetail() {
  const { mesocycleId, sessionId } = useParams<{ mesocycleId: string; sessionId: string }>();
  const { data, isPending, error, refetch } = useMesocycle(mesocycleId);
  const unit = useWeightUnit();

  const [vista, setVista] = useState<Vista>("normal");
  const [sheetAbierta, setSheetAbierta] = useState(false);
  const [minutos, setMinutos] = useState(60);
  const [toast, setToast] = useState<string | null>(null);

  // Resultado del WOD (no aplica a "1rm" — el peso real ya queda en las series de SetRow).
  const [wodSheetAbierta, setWodSheetAbierta] = useState(false);
  const [wodMin, setWodMin] = useState(0);
  const [wodSeg, setWodSeg] = useState(0);
  const [wodRondas, setWodRondas] = useState(0);
  const [wodRepsExtra, setWodRepsExtra] = useState(0);
  const [wodEmomCumplido, setWodEmomCumplido] = useState(true);
  const [wodCalorias, setWodCalorias] = useState(0);
  const [wodDistancia, setWodDistancia] = useState(0);
  const [wodVatios, setWodVatios] = useState(0);

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
  const bloques = groupByBlock(activa.sets, activa.block_order);

  function completarConResultado(wodResult?: SessionCompletePayload) {
    completar.mutate(
      {
        mesocycleId: mesocycleId!,
        sessionId: activa!.id,
        alsoCompleteId: activa!.id === original!.id ? undefined : original!.id,
        wodResult,
      },
      {
        onSuccess: () => {
          setWodSheetAbierta(false);
          setToast("¡Entrenamiento registrado! Buen trabajo 💪");
        },
      },
    );
  }

  function abrirRegistroDeResultado(segundosDelTimer?: number) {
    const segundos = segundosDelTimer ?? activa!.wod_time_seconds ?? 0;
    setWodMin(Math.floor(segundos / 60));
    setWodSeg(segundos % 60);
    setWodRondas(activa!.wod_rounds ?? 0);
    setWodRepsExtra(activa!.wod_extra_reps ?? 0);
    setWodEmomCumplido(activa!.wod_emom_completed ?? true);
    setWodCalorias(activa!.wod_calories ?? 0);
    setWodDistancia(activa!.wod_distance_meters ?? 0);
    setWodVatios(activa!.wod_watts ?? 0);
    setWodSheetAbierta(true);
  }

  // "1rm" no necesita un resultado aparte: el peso real ya se logueó por serie (SetRow).
  const pideResultadoAparte = activa.wod_format != null && activa.wod_format !== "1rm";

  const wodCard = activa.wod_format && (
    <Card className="mt-3">
      <p className="text-xs font-semibold tracking-wide text-muted uppercase">
        🔥 {WOD_FORMAT_LABELS[activa.wod_format]}
        {activa.wod_time_cap_seconds ? ` · Time cap ${formatSeconds(activa.wod_time_cap_seconds)}` : ""}
      </p>
      {completada ? (
        <p className="mt-1 text-sm font-bold">
          {formatWodResult(
            activa,
            activa.sets.map((s) => s.actual_weight).filter((w): w is number => w != null),
            unit,
          ) ?? "Sin resultado registrado"}
        </p>
      ) : (
        <WodTimer
          format={activa.wod_format}
          timeCapSeconds={activa.wod_time_cap_seconds}
          onDone={(segundos) => abrirRegistroDeResultado(segundos)}
          fallback={<p className="mt-1 text-sm font-bold">Registra tu resultado al terminar</p>}
        />
      )}
    </Card>
  );

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

      {activa.warmup_notes && (
        <Card className="mb-4">
          <p className="mb-1 text-xs font-semibold tracking-wide text-muted uppercase">
            🔥 Calentamiento y aproximaciones
          </p>
          <p className="text-sm leading-relaxed">{activa.warmup_notes}</p>
        </Card>
      )}

      {activa.sets.length === 0 ? (
        <EmptyState title="Sin ejercicios asignados">
          Tu coach todavía no cargó los ejercicios de este día.
        </EmptyState>
      ) : (
        <div className="space-y-5">
          {bloques.map((bloque, indiceBloque) => (
            <div key={bloque.key ?? `sin-bloque-${indiceBloque}`}>
              {bloque.label && (
                <p className="mb-2 px-1 text-xs font-semibold tracking-wide text-muted uppercase">
                  {bloque.label}
                </p>
              )}
              <div className="space-y-3">
                {bloque.groups.map((grupo, indiceGrupo) => (
                  <Card key={`${grupo.name}-${indiceGrupo}`} className="p-3">
                    <div className="mb-2.5 px-1">
                      <p className="leading-tight font-bold">{grupo.name}</p>
                      <p className="text-xs text-muted">{groupSummary(grupo, unit)}</p>
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
              {/* El timer/resultado del WOD va justo debajo del bloque METABÓLICO — ahí es
                  donde el atleta realmente lo necesita, no arriba de todo antes de calentar. */}
              {bloque.key === "metcon" && wodCard}
            </div>
          ))}
          {/* Respaldo: si la sesión tiene wod_format pero ningún set está etiquetado como
              "metcon" (ej. cargada a mano sin bloques), igual se muestra al final. */}
          {activa.wod_format && !bloques.some((b) => b.key === "metcon") && wodCard}
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

      {activa.sets.length > 0 && (
        <Button
          variant={completada ? "secondary" : "done"}
          full
          className="mt-3"
          loading={completar.isPending}
          onClick={() => {
            if (!completada && pideResultadoAparte) abrirRegistroDeResultado();
            else completarConResultado();
          }}
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

      <Sheet
        open={wodSheetAbierta}
        onClose={() => setWodSheetAbierta(false)}
        title={activa.wod_format ? `Resultado — ${WOD_FORMAT_LABELS[activa.wod_format]}` : "Resultado del WOD"}
      >
        {activa.wod_format === "for_time" && (
          <>
            <p className="mb-4 text-sm text-muted">¿Cuánto tiempo tardaste en completarlo?</p>
            <div className="flex items-center gap-2">
              <div className="grow">
                <Stepper value={wodMin} onChange={setWodMin} min={0} max={180} suffix="min" />
              </div>
              <div className="grow">
                <Stepper value={wodSeg} onChange={setWodSeg} min={0} max={59} suffix="seg" />
              </div>
            </div>
          </>
        )}

        {activa.wod_format === "amrap" && (
          <>
            <p className="mb-4 text-sm text-muted">¿Cuántas rondas completas hiciste, y cuántas reps extra?</p>
            <div className="flex items-center gap-2">
              <div className="grow">
                <Stepper value={wodRondas} onChange={setWodRondas} min={0} max={200} suffix="rondas" />
              </div>
              <div className="grow">
                <Stepper value={wodRepsExtra} onChange={setWodRepsExtra} min={0} max={500} suffix="reps" />
              </div>
            </div>
          </>
        )}

        {activa.wod_format === "amrap_reps" && (
          <>
            <p className="mb-4 text-sm text-muted">¿Cuántas reps totales hiciste?</p>
            <Stepper value={wodRepsExtra} onChange={setWodRepsExtra} min={0} max={2000} suffix="reps" />
          </>
        )}

        {activa.wod_format === "tabata" && (
          <>
            <p className="mb-4 text-sm text-muted">¿Cuántas reps hiciste en tu peor ronda?</p>
            <Stepper value={wodRepsExtra} onChange={setWodRepsExtra} min={0} max={100} suffix="reps" />
          </>
        )}

        {activa.wod_format === "emom" && (
          <>
            <p className="mb-4 text-sm text-muted">¿Mantuviste el ritmo todo el WOD, sin atrasarte?</p>
            <Segmented<"si" | "no">
              value={wodEmomCumplido ? "si" : "no"}
              onChange={(v) => setWodEmomCumplido(v === "si")}
              options={[
                { value: "si", label: "Sí, lo cumplí" },
                { value: "no", label: "No, me atrasé" },
              ]}
            />
          </>
        )}

        {activa.wod_format === "calories" && (
          <>
            <p className="mb-4 text-sm text-muted">¿Cuántas calorías hiciste?</p>
            <Stepper value={wodCalorias} onChange={setWodCalorias} min={0} max={5000} suffix="cal" />
          </>
        )}

        {activa.wod_format === "distance" && (
          <>
            <p className="mb-4 text-sm text-muted">¿Cuántos metros hiciste?</p>
            <Stepper value={wodDistancia} onChange={setWodDistancia} step={10} min={0} max={200_000} suffix="m" />
          </>
        )}

        {activa.wod_format === "watts" && (
          <>
            <p className="mb-4 text-sm text-muted">¿Cuántos vatios promedio lograste?</p>
            <Stepper value={wodVatios} onChange={setWodVatios} min={0} max={3000} suffix="W" />
          </>
        )}

        {completar.isError && (
          <p className="mt-3 text-sm font-medium text-danger">
            {completar.error instanceof Error ? completar.error.message : "No se pudo guardar. Intenta de nuevo."}
          </p>
        )}

        <Button
          full
          className="mt-4"
          loading={completar.isPending}
          onClick={() => {
            if (activa.wod_format === "for_time") {
              completarConResultado({ wod_time_seconds: wodMin * 60 + wodSeg });
            } else if (activa.wod_format === "amrap") {
              completarConResultado({ wod_rounds: wodRondas, wod_extra_reps: wodRepsExtra });
            } else if (activa.wod_format === "amrap_reps") {
              completarConResultado({ wod_extra_reps: wodRepsExtra });
            } else if (activa.wod_format === "tabata") {
              completarConResultado({ wod_extra_reps: wodRepsExtra });
            } else if (activa.wod_format === "emom") {
              completarConResultado({ wod_emom_completed: wodEmomCumplido });
            } else if (activa.wod_format === "calories") {
              completarConResultado({ wod_calories: wodCalorias });
            } else if (activa.wod_format === "distance") {
              completarConResultado({ wod_distance_meters: wodDistancia });
            } else if (activa.wod_format === "watts") {
              completarConResultado({ wod_watts: wodVatios });
            }
          }}
        >
          <IconCheck className="h-5 w-5" />
          Guardar resultado
        </Button>
      </Sheet>

      {toast && <Toast message={toast} onDismiss={() => setToast(null)} />}
    </>
  );
}
