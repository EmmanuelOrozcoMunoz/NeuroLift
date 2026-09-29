import { useState } from "react";

import { ExerciseFormFields, useExerciseDraft } from "@/components/ExerciseFormFields";
import { blockLabel } from "@/lib/blocks";
import { IconChevronRight, IconTrash } from "@/components/icons";
import { Button, Card, EmptyState, Stepper, cx } from "@/components/ui";
import { useAddSet, useDeleteSet, useUpdateSessionMeta, useUpdateSet } from "@/lib/coachQueries";
import { camposDeFila, draftDeEjercicio, firmaDeEjercicio, nuevoDraft } from "@/lib/exerciseDraft";
import { useSetWodFormat } from "@/lib/queries";
import { groupByBlock } from "@/lib/sessions";
import { WOD_OTHER_SCORE_TYPES, WOD_TIMER_TEMPLATES, wodFormatUsesTimeCap } from "@/lib/wod";
import type { ExerciseGroup } from "@/lib/sessions";
import type { TrainingSession, WodFormat } from "@/lib/types";

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

  const [draft, cambiar] = useExerciseDraft(() => draftDeEjercicio(group, true));
  const [error, setError] = useState<string | null>(null);

  const busy = updateSet.isPending || addSet.isPending || deleteSet.isPending;

  async function handleSave() {
    setError(null);
    const originalIds = group.sets.map((s) => s.id);
    const series = draft.filas.length;
    // Cada serie lleva sus propias repeticiones y su propia carga (rampas: 50%×3, 60%×3, 70%×1…)
    const bodyDe = (i: number) => ({
      exercise_name: draft.name.trim() || group.name,
      ...camposDeFila(draft, i),
      coach_note: draft.nota.trim(),
    });

    try {
      const overlap = Math.min(originalIds.length, series);
      await Promise.all(originalIds.slice(0, overlap).map((setId, i) => updateSet.mutateAsync({ setId, body: bodyDe(i) })));

      if (series < originalIds.length) {
        await Promise.all(originalIds.slice(series).map((setId) => deleteSet.mutateAsync(setId)));
      } else if (series > originalIds.length) {
        for (let i = originalIds.length; i < series; i++) {
          // secuencial a propósito: cada serie nueva se acomoda junto a las de su ejercicio y
          // eso depende del orden actual de la sesión, así que no se pueden crear en paralelo.
          // eslint-disable-next-line no-await-in-loop
          await addSet.mutateAsync({ sessionId, body: bodyDe(i) });
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

      <ExerciseFormFields draft={draft} onChange={cambiar} tipos={["kg", "porcentaje", "libre"]} modo="porSerie" />

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
  const [draft, cambiar] = useExerciseDraft(() => nuevoDraft({ reps: 10 }));
  const [error, setError] = useState<string | null>(null);

  async function handleAdd() {
    setError(null);
    if (!draft.name.trim()) return setError("Escribe el nombre del ejercicio.");
    try {
      for (let i = 0; i < draft.filas.length; i++) {
        // eslint-disable-next-line no-await-in-loop
        await addSet.mutateAsync({
          sessionId,
          body: { exercise_name: draft.name.trim(), ...camposDeFila(draft, i), coach_note: draft.nota.trim() },
        });
      }
      cambiar({ name: "", nota: "" });
      onAdded();
    } catch (err) {
      setError(err instanceof Error ? err.message : "No se pudo añadir el ejercicio.");
    }
  }

  return (
    <Card className="border-dashed">
      <p className="mb-3 font-bold">➕ Añadir ejercicio</p>
      <ExerciseFormFields draft={draft} onChange={cambiar} tipos={["kg", "porcentaje", "libre"]} modo="porSerie" />

      {error && <p className="mt-2 text-sm font-medium text-danger">{error}</p>}
      <Button full className="mt-3" loading={addSet.isPending} onClick={() => void handleAdd()}>
        Añadir a la sesión
      </Button>
    </Card>
  );
}

/** Pautas de calentamiento/aproximaciones que el coach escribe para esta sesión — se muestran
 *  al atleta antes del primer bloque. Guarda al perder el foco, sin botón aparte. */
function WarmupNotesCard({
  mesocycleId,
  session,
  onSaved,
}: {
  mesocycleId: string;
  session: TrainingSession;
  onSaved: () => void;
}) {
  const updateMeta = useUpdateSessionMeta(mesocycleId);
  const [texto, setTexto] = useState(session.warmup_notes ?? "");

  function guardar() {
    if (texto === (session.warmup_notes ?? "")) return;
    updateMeta.mutate(
      { sessionId: session.id, body: { warmup_notes: texto.trim() || "" } },
      { onSuccess: onSaved },
    );
  }

  return (
    <Card>
      <p className="mb-2 text-sm font-semibold text-muted">🔥 Calentamiento y aproximaciones (opcional)</p>
      <textarea
        rows={3}
        maxLength={1000}
        value={texto}
        onChange={(e) => setTexto(e.target.value)}
        onBlur={guardar}
        placeholder="Ej. 5 min de movilidad de cadera, 3 series de aproximación subiendo desde 40% hasta el primer set de trabajo..."
        className="w-full rounded-xl border border-line bg-surface-2 p-3 text-sm text-fg placeholder:text-muted/50 focus:border-brand focus:outline-none"
      />
    </Card>
  );
}

/** Dentro del bloque Metabólico: en vez (o además) del esquema rígido de ejercicios/series
 *  (nombre + reps/peso fijos), se puede escribir el WOD tal cual en texto libre y elegir cómo se
 *  puntúa -- respaldado por Session.wod_notes/wod_format directamente, no por Sets. Convive con
 *  los ejercicios estructurados que ya tenga ese mismo bloque (ver SessionSetsEditor). */
function WodBlockCard({
  mesocycleId,
  session,
  onSaved,
  onRemoved,
}: {
  mesocycleId: string;
  session: TrainingSession;
  onSaved: () => void;
  onRemoved: () => void;
}) {
  const updateMeta = useUpdateSessionMeta(mesocycleId);
  const setWodFormat = useSetWodFormat(mesocycleId);
  const [texto, setTexto] = useState(session.wod_notes ?? "");
  const [seleccionado, setSeleccionado] = useState<WodFormat | "">(session.wod_format ?? "");
  const [timerMin, setTimerMin] = useState(Math.round((session.wod_time_cap_seconds ?? 0) / 60));

  function guardarTexto() {
    if (texto === (session.wod_notes ?? "")) return;
    updateMeta.mutate({ sessionId: session.id, body: { wod_notes: texto.trim() || "" } }, { onSuccess: onSaved });
  }

  function guardarFormato(formato: WodFormat | "", minutos: number) {
    setWodFormat.mutate(
      {
        sessionId: session.id,
        body: {
          wod_format: formato || null,
          time_cap_seconds: formato && wodFormatUsesTimeCap(formato) && minutos > 0 ? minutos * 60 : null,
        },
      },
      { onSuccess: onSaved },
    );
  }

  function elegir(valor: WodFormat) {
    const nuevo = seleccionado === valor ? "" : valor;
    setSeleccionado(nuevo);
    guardarFormato(nuevo, timerMin);
  }

  function quitar() {
    if (!window.confirm("¿Borrar la descripción libre y el puntaje del WOD?")) return;
    updateMeta.mutate({ sessionId: session.id, body: { wod_notes: "" } });
    setWodFormat.mutate({ sessionId: session.id, body: { wod_format: null, time_cap_seconds: null } });
    onRemoved();
  }

  return (
    <Card>
      <div className="mb-2 flex items-center justify-between gap-2">
        <p className="text-sm font-semibold text-muted">📋 Escribir el WOD como texto (opcional)</p>
        <button
          type="button"
          onClick={quitar}
          className="rounded-lg p-1.5 text-danger active:bg-danger/10"
          aria-label="Borrar descripción y puntaje del WOD"
        >
          <IconTrash className="h-4 w-4" />
        </button>
      </div>

      <textarea
        rows={3}
        maxLength={2000}
        value={texto}
        onChange={(e) => setTexto(e.target.value)}
        onBlur={guardarTexto}
        placeholder="Ej. 21-15-9 thrusters (42/30kg), pull-ups."
        className="w-full rounded-xl border border-line bg-surface-2 p-3 text-sm text-fg placeholder:text-muted/50 focus:border-brand focus:outline-none"
      />

      <div className="mt-3 border-t border-line pt-3">
        <p className="mb-1.5 text-xs font-semibold tracking-wide text-muted uppercase">
          Puntuación (opcional)
        </p>
        <div className="mb-2 grid grid-cols-2 gap-2">
          {WOD_TIMER_TEMPLATES.map((opcion) => (
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
        <div className="grid grid-cols-2 gap-2">
          {WOD_OTHER_SCORE_TYPES.map((opcion) => (
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

        {seleccionado && wodFormatUsesTimeCap(seleccionado) && (
          <div className="mt-3 border-t border-line pt-3">
            <p className="mb-1.5 text-xs font-medium text-muted">⏱ Timer / time cap (min) — opcional</p>
            <Stepper
              value={timerMin}
              onChange={(v) => {
                setTimerMin(v);
                guardarFormato(seleccionado, v);
              }}
              min={0}
              max={90}
              suffix="min"
              compact
            />
          </div>
        )}
      </div>
    </Card>
  );
}

/** El orden en que se muestran los bloques de ESTA sesión — el coach lo sube/baja con flechas
 *  (nada de drag-and-drop: más fácil de acertar con el dedo). Solo aparece si hay 2+ bloques. */
function BlockOrderEditor({
  mesocycleId,
  session,
  blockKeys,
  onSaved,
}: {
  mesocycleId: string;
  session: TrainingSession;
  blockKeys: string[];
  onSaved: () => void;
}) {
  const updateMeta = useUpdateSessionMeta(mesocycleId);

  function move(index: number, delta: number) {
    const target = index + delta;
    if (target < 0 || target >= blockKeys.length) return;
    const next = [...blockKeys];
    [next[index], next[target]] = [next[target], next[index]];
    updateMeta.mutate({ sessionId: session.id, body: { block_order: next.join(",") } }, { onSuccess: onSaved });
  }

  if (blockKeys.length < 2) return null;

  return (
    <Card>
      <p className="mb-2 text-sm font-semibold text-muted">🔀 Orden de los bloques</p>
      <div className="space-y-1.5">
        {blockKeys.map((key, index) => (
          <div key={key} className="flex items-center justify-between rounded-xl bg-surface-2 px-3 py-2">
            <span className="text-sm font-medium">{blockLabel(key)}</span>
            <div className="flex gap-1">
              <button
                type="button"
                aria-label={`Subir ${blockLabel(key)}`}
                disabled={index === 0 || updateMeta.isPending}
                onClick={() => move(index, -1)}
                className="rounded-lg p-1.5 text-muted disabled:opacity-30 active:bg-line"
              >
                <IconChevronRight className="h-4 w-4 -rotate-90" />
              </button>
              <button
                type="button"
                aria-label={`Bajar ${blockLabel(key)}`}
                disabled={index === blockKeys.length - 1 || updateMeta.isPending}
                onClick={() => move(index, 1)}
                className="rounded-lg p-1.5 text-muted disabled:opacity-30 active:bg-line"
              >
                <IconChevronRight className="h-4 w-4 rotate-90" />
              </button>
            </div>
          </div>
        ))}
      </div>
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
  discipline: string;
  session: TrainingSession;
  onFeedback: (message: string) => void;
}) {
  const [forzarMetcon, setForzarMetcon] = useState(Boolean(session.wod_notes) || session.wod_format != null);
  const bloques = groupByBlock(session.sets, session.block_order, forzarMetcon);
  const blockKeys = bloques.map((b) => b.key).filter((key): key is string => key !== null);
  const tieneMetcon = bloques.some((b) => b.key === "metcon");

  return (
    <div className="space-y-4">
      <WarmupNotesCard
        mesocycleId={mesocycleId}
        session={session}
        onSaved={() => onFeedback("¡Pautas de calentamiento guardadas!")}
      />
      <BlockOrderEditor
        mesocycleId={mesocycleId}
        session={session}
        blockKeys={blockKeys}
        onSaved={() => onFeedback("¡Orden de bloques actualizado!")}
      />
      {session.sets.length === 0 && !tieneMetcon && (
        <EmptyState title="Esta sesión todavía no tiene ejercicios" />
      )}
      {bloques.map((bloque, indiceBloque) => (
        <div key={bloque.key ?? `sin-bloque-${indiceBloque}`} className="space-y-3">
          {bloque.label && (
            <p className="px-1 text-xs font-semibold tracking-wide text-muted uppercase">{bloque.label}</p>
          )}
          {bloque.key === "metcon" && (
            <WodBlockCard
              mesocycleId={mesocycleId}
              session={session}
              onSaved={() => onFeedback("¡WOD guardado!")}
              onRemoved={() => setForzarMetcon(false)}
            />
          )}
          {bloque.groups.map((group) => (
            <ExerciseBlock
              key={firmaDeEjercicio(group)}
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
      {!tieneMetcon && (
        <button
          type="button"
          onClick={() => setForzarMetcon(true)}
          className="w-full rounded-2xl border border-dashed border-line bg-surface p-4 text-left font-bold active:bg-surface-2"
        >
          🔥 Añadir WOD
        </button>
      )}
    </div>
  );
}
