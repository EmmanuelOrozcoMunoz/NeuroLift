import { useState } from "react";
import { useParams } from "react-router-dom";

import { PageHeader } from "@/components/AppShell";
import { IconTrash } from "@/components/icons";
import { Button, Card, EmptyState, ErrorState, Field, LoadingList, Segmented, Stepper, Toast } from "@/components/ui";
import { useAddPlanSet, useDeletePlanSet } from "@/lib/coachQueries";
import { usePlanDetail } from "@/lib/queries";
import { groupSets, groupSummary } from "@/lib/sessions";
import type { ExerciseGroup } from "@/lib/sessions";

type TipoCarga = "porcentaje" | "kg" | "libre";

function DayEditor({
  planId,
  sessionId,
  dayNumber,
  groups,
  onFeedback,
}: {
  planId: string;
  sessionId: string;
  dayNumber: number;
  groups: ExerciseGroup[];
  onFeedback: (message: string) => void;
}) {
  const addSet = useAddPlanSet(planId);
  const deleteSet = useDeletePlanSet(planId);

  const [name, setName] = useState("");
  const [series, setSeries] = useState(3);
  const [reps, setReps] = useState(5);
  const [rpe, setRpe] = useState(7);
  const [tipo, setTipo] = useState<TipoCarga>("porcentaje");
  const [valor, setValor] = useState(75);
  const [referencia, setReferencia] = useState("");
  const [error, setError] = useState<string | null>(null);

  function handleAdd() {
    setError(null);
    if (!name.trim()) return setError("Escribe el nombre del ejercicio.");

    addSet.mutate(
      {
        sessionId,
        body: {
          exercise_name: name.trim(),
          prescribed_sets: series,
          prescribed_reps: reps,
          rpe: rpe > 0 ? rpe : null,
          prescribed_weight: tipo === "kg" ? valor : null,
          prescribed_percentage: tipo === "porcentaje" ? valor : null,
          reference_exercise: tipo === "porcentaje" && referencia.trim() ? referencia.trim() : null,
        },
      },
      {
        onSuccess: (response) => {
          onFeedback(response.message ?? "Ejercicio agregado.");
          setName("");
          setReferencia("");
        },
        onError: (err) => setError(err instanceof Error ? err.message : "No se pudo agregar."),
      },
    );
  }

  return (
    <Card>
      <p className="mb-3 font-bold">📆 Día {dayNumber}</p>

      {groups.length === 0 ? (
        <p className="mb-3 text-sm text-muted">Todavía sin ejercicios.</p>
      ) : (
        <div className="mb-3 space-y-2">
          {groups.map((group, index) => (
            <div
              key={`${group.name}-${index}`}
              className="flex items-center justify-between gap-2 rounded-xl bg-surface-2 px-3 py-2.5"
            >
              <div className="min-w-0">
                <p className="truncate text-sm font-semibold">🏋️ {group.name}</p>
                <p className="truncate text-xs text-muted">{groupSummary(group)}</p>
              </div>
              <button
                type="button"
                aria-label="Quitar ejercicio"
                disabled={deleteSet.isPending}
                onClick={() => group.sets.forEach((s) => deleteSet.mutate(s.id))}
                className="shrink-0 rounded-lg p-1.5 text-danger active:bg-danger/10 disabled:opacity-40"
              >
                <IconTrash className="h-4 w-4" />
              </button>
            </div>
          ))}
        </div>
      )}

      <div className="space-y-3 border-t border-line pt-3">
        <p className="text-sm font-semibold text-muted">➕ Agregar ejercicio</p>
        <Field label="Ejercicio" value={name} onChange={(e) => setName(e.target.value)} />

        <div className="grid grid-cols-3 gap-3">
          <div>
            <span className="mb-1.5 block text-xs font-medium text-muted">Series</span>
            <Stepper value={series} onChange={setSeries} min={1} max={20} compact />
          </div>
          <div>
            <span className="mb-1.5 block text-xs font-medium text-muted">Reps</span>
            <Stepper value={reps} onChange={setReps} min={1} max={100} compact />
          </div>
          <div>
            <span className="mb-1.5 block text-xs font-medium text-muted">RPE</span>
            <Stepper value={rpe} onChange={setRpe} min={0} max={10} compact />
          </div>
        </div>

        <Segmented<TipoCarga>
          value={tipo}
          onChange={setTipo}
          options={[
            { value: "porcentaje", label: "% de 1RM" },
            { value: "kg", label: "Kg fijos" },
            { value: "libre", label: "Sin carga" },
          ]}
        />

        {tipo !== "libre" && (
          <div>
            <span className="mb-1.5 block text-xs font-medium text-muted">
              {tipo === "porcentaje" ? "Porcentaje (%)" : "Peso (kg)"}
            </span>
            <Stepper
              value={valor}
              onChange={setValor}
              step={tipo === "porcentaje" ? 5 : 2.5}
              min={0}
              max={tipo === "porcentaje" ? 150 : 1000}
            />
          </div>
        )}

        {tipo === "porcentaje" && (
          <Field
            label="1RM de referencia (opcional)"
            placeholder="Ej. Back Squat — vacío usa el mismo ejercicio"
            value={referencia}
            onChange={(e) => setReferencia(e.target.value)}
          />
        )}

        {error && <p className="text-sm font-medium text-danger">{error}</p>}
        <Button full loading={addSet.isPending} onClick={handleAdd}>
          Agregar al plan
        </Button>
      </div>
    </Card>
  );
}

export default function PlanEditor() {
  const { planId } = useParams<{ planId: string }>();
  const { data, isPending, error, refetch } = usePlanDetail(planId);
  const [toast, setToast] = useState<string | null>(null);

  const sessions = [...(data?.sessions ?? [])].sort((a, b) => (a.day_offset ?? 0) - (b.day_offset ?? 0));

  return (
    <>
      <PageHeader title={data?.name ?? "Plan"} subtitle="Contenido del plan" back="/coach/planes" />

      <p className="mb-4 text-sm text-muted">
        Las cargas en % de 1RM se convierten a kilos automáticamente cuando alguien adquiere el
        plan, usando SUS propias marcas. Usa kg fijos solo para cargas absolutas.
      </p>

      {isPending && <LoadingList rows={3} />}
      {!isPending && error && <ErrorState error={error} onRetry={() => void refetch()} />}
      {!isPending && !error && sessions.length === 0 && (
        <EmptyState title="Este plan no tiene días configurados" />
      )}

      <div className="space-y-3">
        {sessions.map((session) => (
          <DayEditor
            key={session.id}
            planId={planId!}
            sessionId={session.id}
            dayNumber={(session.day_offset ?? 0) + 1}
            groups={groupSets(session.sets)}
            onFeedback={setToast}
          />
        ))}
      </div>

      {toast && <Toast message={toast} onDismiss={() => setToast(null)} />}
    </>
  );
}
