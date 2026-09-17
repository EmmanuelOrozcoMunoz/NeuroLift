import { useQueries } from "@tanstack/react-query";
import { useState } from "react";
import { Link, useParams } from "react-router-dom";

import { PageHeader } from "@/components/AppShell";
import { FitLevelCriteria } from "@/components/FitLevelCriteria";
import { IconChevronRight, IconTrash } from "@/components/icons";
import { Button, Card, EmptyState, ErrorState, Field, LoadingList, Toast } from "@/components/ui";
import { CreateMesocycleSheet } from "@/components/CreateMesocycleSheet";
import { apiFetch } from "@/lib/api";
import { useAthletes, useGroups } from "@/lib/coachQueries";
import { shortDate } from "@/lib/dates";
import { COMMON_PR_EXERCISES } from "@/lib/exercises";
import { formatWeight, kgTo, toKg, useWeightUnit } from "@/lib/units";
import {
  usePersonalRecords,
  useUpsertPersonalRecord,
  useDeletePersonalRecord,
  useMesocycles,
  useRecentActivity,
  useFitnessLevel,
} from "@/lib/queries";
import { formatWodResult } from "@/lib/wod";
import type { GroupDetail } from "@/lib/types";

export default function AthleteDetail() {
  const { athleteId } = useParams<{ athleteId: string }>();
  const athletes = useAthletes();
  const athlete = athletes.data?.find((a) => a.id === athleteId);

  const groups = useGroups();
  const groupDetails = useQueries({
    queries: (groups.data ?? []).map((group) => ({
      queryKey: ["group", group.id],
      queryFn: () => apiFetch<GroupDetail>(`/groups/${group.id}`),
    })),
  });
  const myGroup = (groups.data ?? []).find((_group, index) =>
    groupDetails[index]?.data?.members.some((m) => m.id === athleteId),
  );

  const mesocycles = useMesocycles(athleteId ?? "");
  const fitLevel = useFitnessLevel(athleteId ?? "");
  const prs = usePersonalRecords(athleteId ?? "");
  const upsertPr = useUpsertPersonalRecord(athleteId ?? "");
  const deletePr = useDeletePersonalRecord(athleteId ?? "");
  const recent = useRecentActivity(athleteId ?? "");
  const unit = useWeightUnit();

  const [exercise, setExercise] = useState<string>(COMMON_PR_EXERCISES[0]);
  const [weight, setWeight] = useState("");
  const [sheetOpen, setSheetOpen] = useState(false);
  const [toast, setToast] = useState<string | null>(null);

  function handleDeletePr(id: string, exerciseName: string) {
    if (!window.confirm(`¿Eliminar la marca de ${exerciseName}?`)) return;
    deletePr.mutate(id, {
      onSuccess: () => setToast("Marca eliminada."),
      onError: (err) => setToast(err instanceof Error ? err.message : "No se pudo eliminar la marca."),
    });
  }

  function handleSubmitPr(event: React.FormEvent) {
    event.preventDefault();
    const entered = Number(weight);
    if (!exercise.trim() || !(entered > 0)) return;
    const kg = toKg(entered, unit);
    upsertPr.mutate(
      { exercise_name: exercise.trim(), max_weight_kg: kg },
      {
        onSuccess: (response) => {
          setToast(response.message ?? "¡Marca guardada!");
          setExercise(COMMON_PR_EXERCISES[0]);
          setWeight("");
        },
      },
    );
  }

  return (
    <>
      <PageHeader title={athlete?.full_name ?? "Atleta"} subtitle={athlete?.email} back="/coach/atletas" />

      <Card className="mb-4">
        <p className="mb-3 font-bold">📈 Récords (PRs)</p>
        {prs.isPending && <LoadingList rows={1} />}
        {!prs.isPending && prs.error && <ErrorState error={prs.error} onRetry={() => void prs.refetch()} />}
        {!prs.isPending && !prs.error && (prs.data?.length ?? 0) === 0 && (
          <p className="text-sm text-muted">Todavía no tiene marcas registradas.</p>
        )}
        {!prs.isPending && (prs.data?.length ?? 0) > 0 && (
          <div className="mb-3 grid grid-cols-2 gap-2">
            {prs.data!.map((pr) => (
              <div key={pr.id} className="relative rounded-xl bg-surface-2 p-2.5">
                <button
                  type="button"
                  onClick={() => handleDeletePr(pr.id, pr.exercise_name)}
                  disabled={deletePr.isPending}
                  aria-label={`Eliminar marca de ${pr.exercise_name}`}
                  className="absolute top-1.5 right-1.5 rounded-lg p-1 text-danger active:bg-danger/10 disabled:opacity-40"
                >
                  <IconTrash className="h-3.5 w-3.5" />
                </button>
                <p className="truncate pr-5 text-xs font-semibold text-muted">{pr.exercise_name}</p>
                <p className="text-base font-bold">{formatWeight(pr.max_weight_kg, unit)}</p>
              </div>
            ))}
          </div>
        )}

        <form onSubmit={handleSubmitPr} className="flex items-end gap-2">
          <label className="block grow">
            <span className="mb-1.5 block text-sm font-medium text-muted">Ejercicio</span>
            <select
              value={exercise}
              onChange={(e) => setExercise(e.target.value)}
              className="min-h-12 w-full rounded-xl border border-line bg-surface-2 px-3.5 text-fg"
            >
              {COMMON_PR_EXERCISES.map((name) => (
                <option key={name} value={name}>
                  {name}
                </option>
              ))}
            </select>
          </label>
          <Field
            label={unit}
            type="number"
            inputMode="decimal"
            step={unit === "lb" ? "5" : "2.5"}
            min="0"
            value={weight}
            onChange={(e) => setWeight(e.target.value)}
            className="w-20"
          />
          <Button type="submit" loading={upsertPr.isPending}>
            Guardar
          </Button>
        </form>
      </Card>

      <Card className="mb-4">
        <p className="mb-3 font-bold">🎯 Fit Level</p>
        {fitLevel.isPending && <LoadingList rows={1} />}
        {!fitLevel.isPending && fitLevel.data?.overall_level ? (
          <>
            <p className="text-sm font-semibold text-muted">Nivel general</p>
            <p className="mt-0.5 text-2xl font-bold">
              {fitLevel.data.overall_level}{" "}
              <span className="text-base font-semibold text-muted">{fitLevel.data.overall_score}/4</span>
            </p>
            <div className="mt-3 grid grid-cols-3 gap-2">
              {(
                [
                  ["halterofilia", "🏋️ Halterofilia"],
                  ["gimnasia", "🤸 Gimnasia"],
                  ["metcon", "🔥 Metcon"],
                ] as const
              ).map(([cat, label]) => (
                <div key={cat} className="rounded-xl bg-surface-2 p-2.5 text-center">
                  <p className="text-xs text-muted">{label}</p>
                  <p className="mt-0.5 font-bold">{fitLevel.data!.category_levels[cat] ?? "—"}</p>
                </div>
              ))}
            </div>
          </>
        ) : (
          !fitLevel.isPending && (
            <p className="text-sm text-muted">Todavía no tiene marcas para calcular su Fit Level.</p>
          )
        )}
      </Card>

      <FitLevelCriteria />

      <Card className="mb-4">
        <p className="mb-3 font-bold">📋 Actividad reciente</p>
        {recent.isPending && <LoadingList rows={2} />}
        {!recent.isPending && recent.error && (
          <ErrorState error={recent.error} onRetry={() => void recent.refetch()} />
        )}
        {!recent.isPending && !recent.error && (recent.data?.length ?? 0) === 0 && (
          <p className="text-sm text-muted">Todavía no ha completado ningún entrenamiento.</p>
        )}
        {!recent.isPending && (recent.data?.length ?? 0) > 0 && (
          <div className="space-y-2.5">
            {recent.data!.map((sesion) => {
              const resultado = formatWodResult(
                sesion,
                sesion.exercises.flatMap((e) => e.actual_weight),
                unit,
              );
              return (
                <div key={sesion.session_id} className="rounded-xl bg-surface-2 p-3">
                  <div className="flex items-center justify-between gap-2">
                    <p className="text-sm font-semibold">{shortDate(sesion.scheduled_date)}</p>
                    {resultado && <span className="text-xs font-bold text-brand">{resultado}</span>}
                  </div>
                  {sesion.exercises.length === 0 ? (
                    <p className="mt-1 text-xs text-muted">Sin series registradas.</p>
                  ) : (
                    <div className="mt-1.5 space-y-1">
                      {sesion.exercises.map((ej, index) => (
                        <p key={`${ej.exercise_name}-${index}`} className="text-xs text-muted">
                          <span className="font-medium text-fg">{ej.exercise_name}</span>
                          {ej.actual_weight.length > 0 &&
                            ` — ${ej.actual_weight.map((w) => Math.round(kgTo(w, unit) * 10) / 10).join(", ")} ${unit}`}
                          {ej.actual_reps.length > 0 && ` (${ej.actual_reps.join(", ")} reps)`}
                        </p>
                      ))}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </Card>

      <div className="mb-2 flex items-baseline justify-between">
        <p className="text-sm font-semibold tracking-wide text-muted uppercase">Mesociclos</p>
        {!myGroup && <Button onClick={() => setSheetOpen(true)}>+ Crear</Button>}
      </div>

      {myGroup ? (
        <Card className="border-brand/30 bg-brand-soft/30">
          <p className="text-sm">
            Este atleta pertenece al grupo <strong>{myGroup.name}</strong>. Programa y edita su
            mesociclo desde ahí para que los cambios se puedan aplicar a todo el equipo.
          </p>
          <Link to={`/coach/grupos/${myGroup.id}`} className="mt-3 inline-block text-sm font-semibold text-brand">
            Ir al grupo →
          </Link>
        </Card>
      ) : (
        <>
          {mesocycles.isPending && <LoadingList rows={2} />}
          {!mesocycles.isPending && mesocycles.error && (
            <ErrorState error={mesocycles.error} onRetry={() => void mesocycles.refetch()} />
          )}
          {!mesocycles.isPending && !mesocycles.error && (mesocycles.data?.length ?? 0) === 0 && (
            <EmptyState title="Todavía no tiene mesociclos">
              Créale uno con el botón de arriba.
            </EmptyState>
          )}
          <div className="space-y-3">
            {mesocycles.data
              ?.filter((m) => !m.group_id)
              .map((meso) => (
                <Link
                  key={meso.id}
                  to={`/coach/mesociclos/${meso.id}`}
                  className="flex items-center gap-3 rounded-2xl border border-line bg-surface p-4 active:bg-surface-2"
                >
                  <div className="min-w-0 grow">
                    <p className="truncate font-bold">{meso.name ?? "Rutina"}</p>
                    <p className="text-sm text-muted">
                      {meso.discipline} · desde {shortDate(meso.start_date)}
                    </p>
                  </div>
                  <IconChevronRight className="h-5 w-5 shrink-0 text-muted" />
                </Link>
              ))}
          </div>
        </>
      )}

      <CreateMesocycleSheet
        open={sheetOpen}
        onClose={() => setSheetOpen(false)}
        target={{ type: "athlete", id: athleteId! }}
        onCreated={(message) => setToast(message)}
      />

      {toast && <Toast message={toast} onDismiss={() => setToast(null)} />}
    </>
  );
}
