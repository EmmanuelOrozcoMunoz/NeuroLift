import { useState } from "react";

import { ExerciseFormFields, useExerciseDraft } from "@/components/ExerciseFormFields";
import { ExerciseSummaryRow } from "@/components/ExerciseSummaryRow";
import { IconTrash } from "@/components/icons";
import { BlockOrderEditor, WarmupNotesCard } from "@/components/SessionMetaCards";
import type { MetaGuardado } from "@/components/SessionMetaCards";
import { Button, Card, Stepper, cx } from "@/components/ui";
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
  onClose,
}: {
  mesocycleId: string;
  sessionId: string;
  group: ExerciseGroup;
  onSaved: () => void;
  /** Cierra el formulario sin guardar y vuelve a la línea compacta del ejercicio. */
  onClose: () => void;
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

      <div className="mt-3 flex gap-2">
        <Button variant="ghost" className="grow" disabled={busy} onClick={onClose}>
          Cancelar
        </Button>
        <Button variant="secondary" className="grow" loading={busy} onClick={() => void handleSave()}>
          Guardar ajustes
        </Button>
      </div>
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

  // Sin tarjeta propia: va al pie de la tarjeta del día, separado de la lista por una línea,
  // igual que en el editor de planes.
  return (
    <div className="space-y-3 border-t border-line pt-3">
      <p className="text-sm font-semibold text-muted">➕ Añadir ejercicio</p>
      <ExerciseFormFields draft={draft} onChange={cambiar} tipos={["kg", "porcentaje", "libre"]} modo="porSerie" />

      {error && <p className="text-sm font-medium text-danger">{error}</p>}
      <Button full loading={addSet.isPending} onClick={() => void handleAdd()}>
        Añadir a la sesión
      </Button>
    </div>
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

/** Editor completo (ver + editar + añadir ejercicios) de UNA sesión. Se usa tanto en la
 *  pantalla dedicada del coach como embebido dentro de la pestaña individual de un atleta
 *  dentro de un programa de grupo, y en el entreno propio del atleta.
 *
 *  Mismo diseño que el editor de planes: arriba las pautas de calentamiento y el orden de los
 *  bloques; luego el día agrupado por bloques, con cada ejercicio en una línea compacta (el lápiz
 *  abre su formulario); el WOD y, al pie, el formulario para añadir ejercicios. */
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
  const updateMeta = useUpdateSessionMeta(mesocycleId);
  const deleteSet = useDeleteSet(mesocycleId);
  const [forzarMetcon, setForzarMetcon] = useState(Boolean(session.wod_notes) || session.wod_format != null);
  // El ejercicio cuyo formulario está abierto (por su firma: al guardar cambia y se cierra solo)
  const [editando, setEditando] = useState<string | null>(null);
  const bloques = groupByBlock(session.sets, session.block_order, forzarMetcon);
  const blockKeys = bloques.map((b) => b.key).filter((key): key is string => key !== null);
  const tieneMetcon = bloques.some((b) => b.key === "metcon");
  const vacia = session.sets.length === 0 && !tieneMetcon;

  const meta: MetaGuardado = {
    guardar: (body, alTerminar) => updateMeta.mutate({ sessionId: session.id, body }, { onSuccess: alTerminar }),
    guardando: updateMeta.isPending,
  };

  const botonWod = (
    <button
      type="button"
      onClick={() => setForzarMetcon(true)}
      className="w-full rounded-2xl border border-dashed border-line bg-surface p-3 text-left text-sm font-bold active:bg-surface-2"
    >
      🔥 Añadir WOD
    </button>
  );

  return (
    <div className="space-y-4">
      <WarmupNotesCard session={session} meta={meta} onSaved={() => onFeedback("¡Pautas de calentamiento guardadas!")} />
      <BlockOrderEditor blockKeys={blockKeys} meta={meta} onSaved={() => onFeedback("¡Orden de bloques actualizado!")} />

      <Card>
        {vacia ? (
          <p className="mb-3 text-sm text-muted">Esta sesión todavía no tiene ejercicios.</p>
        ) : (
          <div className="mb-3 space-y-3">
            {bloques.map((bloque, indiceBloque) => (
              <div key={bloque.key ?? `sin-bloque-${indiceBloque}`}>
                {bloque.label && (
                  <p className="mb-1.5 text-xs font-semibold tracking-wide text-muted uppercase">{bloque.label}</p>
                )}
                {bloque.key === "metcon" && (
                  <WodBlockCard
                    mesocycleId={mesocycleId}
                    session={session}
                    onSaved={() => onFeedback("¡WOD guardado!")}
                    onRemoved={() => setForzarMetcon(false)}
                  />
                )}
                <div className="space-y-2">
                  {bloque.groups.map((group) => {
                    const firma = firmaDeEjercicio(group);
                    return firma === editando ? (
                      <ExerciseBlock
                        key={firma}
                        mesocycleId={mesocycleId}
                        sessionId={session.id}
                        group={group}
                        onSaved={() => {
                          setEditando(null);
                          onFeedback("¡Ajustes guardados!");
                        }}
                        onClose={() => setEditando(null)}
                      />
                    ) : (
                      <ExerciseSummaryRow
                        key={firma}
                        group={group}
                        removing={deleteSet.isPending}
                        onEdit={() => setEditando(firma)}
                        onRemove={() => group.sets.forEach((s) => deleteSet.mutate(s.id))}
                      />
                    );
                  })}
                </div>
              </div>
            ))}
            {!tieneMetcon && botonWod}
          </div>
        )}
        {vacia && <div className="mb-3">{botonWod}</div>}

        <AddExerciseForm
          mesocycleId={mesocycleId}
          sessionId={session.id}
          onAdded={() => onFeedback("¡Ejercicio añadido!")}
        />
      </Card>
    </div>
  );
}
