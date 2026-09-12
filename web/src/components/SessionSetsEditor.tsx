import { useState } from "react";

import { BlockSelect } from "@/components/BlockSelect";
import { IconTrash } from "@/components/icons";
import { Button, Card, EmptyState, Field, Stepper, cx } from "@/components/ui";
import { useAddSet, useDeleteSet, useUpdateSet } from "@/lib/coachQueries";
import { useSetWodFormat } from "@/lib/queries";
import { groupByBlock } from "@/lib/sessions";
import { WOD_FORMAT_OPTIONS } from "@/lib/wod";
import type { ExerciseGroup } from "@/lib/sessions";
import type { TrainingSession, WodFormat } from "@/lib/types";

/** El coach marca (o quita) el formato de WOD de esta sesión — el atleta lo ve al completarla
 *  y reporta el resultado que corresponda (tiempo, rondas+reps, o si cumplió el ritmo). */
function WodFormatCard({
  mesocycleId,
  session,
  onSaved,
}: {
  mesocycleId: string;
  session: TrainingSession;
  onSaved: () => void;
}) {
  const setWodFormat = useSetWodFormat(mesocycleId);
  const [seleccionado, setSeleccionado] = useState<WodFormat | "">(session.wod_format ?? "");

  function elegir(valor: WodFormat) {
    const nuevo = seleccionado === valor ? "" : valor;
    setSeleccionado(nuevo);
    setWodFormat.mutate(
      { sessionId: session.id, body: { wod_format: nuevo || null } },
      { onSuccess: onSaved },
    );
  }

  return (
    <Card>
      <p className="mb-2 text-sm font-semibold text-muted">🔥 Formato del WOD (opcional)</p>
      <div className="grid grid-cols-2 gap-2">
        {WOD_FORMAT_OPTIONS.map((opcion) => (
          <button
            key={opcion.value}
            type="button"
            disabled={setWodFormat.isPending}
            onClick={() => elegir(opcion.value)}
            className={cx(
              "rounded-xl border px-3 py-2.5 text-left disabled:opacity-60",
              seleccionado === opcion.value
                ? "border-brand bg-brand-soft text-brand"
                : "border-line bg-surface-2 text-fg",
            )}
          >
            <p className="text-sm font-bold">{opcion.label}</p>
            <p className="text-xs text-muted">{opcion.hint}</p>
          </button>
        ))}
      </div>
    </Card>
  );
}

function ExerciseBlock({
  mesocycleId,
  sessionId,
  group,
  onSaved,
}: {
  mesocycleId: string;
  sessionId: string;
  group: ExerciseGroup;
  onSaved: () => void;
}) {
  const updateSet = useUpdateSet(mesocycleId);
  const addSet = useAddSet(mesocycleId);
  const deleteSet = useDeleteSet(mesocycleId);

  const first = group.sets[0];
  const [name, setName] = useState(group.name);
  const [series, setSeries] = useState(group.sets.length);
  const [reps, setReps] = useState(first.prescribed_reps);
  const [rpe, setRpe] = useState(first.rpe ?? 0);
  const [weight, setWeight] = useState(first.prescribed_weight ?? 0);
  const [block, setBlock] = useState(first.block ?? "");
  const [error, setError] = useState<string | null>(null);

  const busy = updateSet.isPending || addSet.isPending || deleteSet.isPending;

  async function handleSave() {
    setError(null);
    const originalIds = group.sets.map((s) => s.id);
    const body = {
      exercise_name: name.trim() || group.name,
      prescribed_reps: reps,
      rpe: rpe > 0 ? rpe : null,
      prescribed_weight: weight > 0 ? weight : null,
      block: block || null,
    };

    try {
      const overlap = Math.min(originalIds.length, series);
      await Promise.all(originalIds.slice(0, overlap).map((setId) => updateSet.mutateAsync({ setId, body })));

      if (series < originalIds.length) {
        await Promise.all(originalIds.slice(series).map((setId) => deleteSet.mutateAsync(setId)));
      } else if (series > originalIds.length) {
        const faltantes = series - originalIds.length;
        for (let i = 0; i < faltantes; i++) {
          // secuencial a propósito: el backend calcula set_order por el conteo actual de la
          // sesión, así que crear en paralelo podría hacer que dos series compitan por el
          // mismo orden.
          // eslint-disable-next-line no-await-in-loop
          await addSet.mutateAsync({ sessionId, body });
        }
      }
      onSaved();
    } catch (err) {
      setError(err instanceof Error ? err.message : "No se pudo guardar.");
    }
  }

  async function handleRemoveAll() {
    await Promise.all(group.sets.map((s) => deleteSet.mutateAsync(s.id)));
  }

  return (
    <Card>
      <div className="mb-3 flex items-center justify-between gap-2">
        <p className="font-bold">{group.name}</p>
        <button
          type="button"
          onClick={() => void handleRemoveAll()}
          disabled={busy}
          className="rounded-lg p-1.5 text-danger active:bg-danger/10 disabled:opacity-40"
          aria-label="Quitar ejercicio"
        >
          <IconTrash className="h-4 w-4" />
        </button>
      </div>

      <Field label="Ejercicio" value={name} onChange={(e) => setName(e.target.value)} className="mb-3" />
      <BlockSelect value={block} onChange={setBlock} />

      <div className="grid grid-cols-2 gap-3">
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
        <div>
          <span className="mb-1.5 block text-xs font-medium text-muted">Peso (kg)</span>
          <Stepper value={weight} onChange={setWeight} step={2.5} min={0} max={1000} compact />
        </div>
      </div>

      {error && <p className="mt-2 text-sm font-medium text-danger">{error}</p>}

      <Button variant="secondary" full className="mt-3" loading={busy} onClick={() => void handleSave()}>
        Guardar ajustes
      </Button>
    </Card>
  );
}

function AddExerciseForm({
  mesocycleId,
  sessionId,
  onAdded,
}: {
  mesocycleId: string;
  sessionId: string;
  onAdded: () => void;
}) {
  const addSet = useAddSet(mesocycleId);
  const [name, setName] = useState("");
  const [series, setSeries] = useState(3);
  const [reps, setReps] = useState(10);
  const [rpe, setRpe] = useState(7);
  const [weight, setWeight] = useState(0);
  const [block, setBlock] = useState("");
  const [error, setError] = useState<string | null>(null);

  async function handleAdd() {
    setError(null);
    if (!name.trim()) return setError("Escribe el nombre del ejercicio.");
    const body = {
      exercise_name: name.trim(),
      prescribed_reps: reps,
      rpe: rpe > 0 ? rpe : null,
      prescribed_weight: weight > 0 ? weight : null,
      block: block || null,
    };
    try {
      for (let i = 0; i < series; i++) {
        // eslint-disable-next-line no-await-in-loop
        await addSet.mutateAsync({ sessionId, body });
      }
      setName("");
      onAdded();
    } catch (err) {
      setError(err instanceof Error ? err.message : "No se pudo añadir el ejercicio.");
    }
  }

  return (
    <Card className="border-dashed">
      <p className="mb-3 font-bold">➕ Añadir ejercicio</p>
      <Field label="Ejercicio" value={name} onChange={(e) => setName(e.target.value)} className="mb-3" />
      <BlockSelect value={block} onChange={setBlock} />
      <div className="grid grid-cols-2 gap-3">
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
        <div>
          <span className="mb-1.5 block text-xs font-medium text-muted">Peso (kg)</span>
          <Stepper value={weight} onChange={setWeight} step={2.5} min={0} max={1000} compact />
        </div>
      </div>
      {error && <p className="mt-2 text-sm font-medium text-danger">{error}</p>}
      <Button full className="mt-3" loading={addSet.isPending} onClick={() => void handleAdd()}>
        Añadir a la sesión
      </Button>
    </Card>
  );
}

/** Editor completo (ver + editar + añadir ejercicios) de UNA sesión. Se usa tanto en la
 *  pantalla dedicada del coach como embebido dentro de la pestaña individual de un atleta
 *  dentro de un programa de grupo. */
export function SessionSetsEditor({
  mesocycleId,
  session,
  onFeedback,
}: {
  mesocycleId: string;
  session: TrainingSession;
  onFeedback: (message: string) => void;
}) {
  const bloques = groupByBlock(session.sets);

  return (
    <div className="space-y-4">
      <WodFormatCard
        mesocycleId={mesocycleId}
        session={session}
        onSaved={() => onFeedback("Formato de WOD actualizado.")}
      />
      {session.sets.length === 0 && <EmptyState title="Esta sesión todavía no tiene ejercicios" />}
      {bloques.map((bloque, indiceBloque) => (
        <div key={bloque.key ?? `sin-bloque-${indiceBloque}`} className="space-y-3">
          {bloque.label && (
            <p className="px-1 text-xs font-semibold tracking-wide text-muted uppercase">{bloque.label}</p>
          )}
          {bloque.groups.map((group, index) => (
            <ExerciseBlock
              key={`${group.name}-${index}`}
              mesocycleId={mesocycleId}
              sessionId={session.id}
              group={group}
              onSaved={() => onFeedback("¡Ajustes guardados!")}
            />
          ))}
        </div>
      ))}
      <AddExerciseForm
        mesocycleId={mesocycleId}
        sessionId={session.id}
        onAdded={() => onFeedback("¡Ejercicio añadido!")}
      />
    </div>
  );
}
