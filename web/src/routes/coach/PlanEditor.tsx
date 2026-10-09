import { useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { useParams } from "react-router-dom";

import { PageHeader } from "@/components/AppShell";
import { CoverUploader } from "@/components/CoverImage";
import { ExerciseFormFields, useExerciseDraft } from "@/components/ExerciseFormFields";
import { ExerciseSummaryRow } from "@/components/ExerciseSummaryRow";
import { IconTrash } from "@/components/icons";
import { BlockOrderEditor, WarmupNotesCard } from "@/components/SessionMetaCards";
import type { MetaGuardado } from "@/components/SessionMetaCards";
import { Button, Card, EmptyState, ErrorState, Field, LoadingList, Sheet, Stepper, Toast, cx } from "@/components/ui";
import {
  coachKeys,
  useAddPlanSet,
  useDeletePlanSet,
  useSetPlanSessionWodFormat,
  useUpdatePlan,
  useUpdatePlanExercise,
  useUpdatePlanSessionMeta,
} from "@/lib/coachQueries";
import { camposComunes, draftDeEjercicio, firmaDeEjercicio, nuevoDraft, seriesParaEnviar } from "@/lib/exerciseDraft";
import { usePlanDetail } from "@/lib/queries";
import { groupByBlock } from "@/lib/sessions";
import type { ExerciseGroup } from "@/lib/sessions";
import { WOD_OTHER_SCORE_TYPES, WOD_TIMER_TEMPLATES, wodFormatUsesTimeCap } from "@/lib/wod";
import type { MesocycleFull, PlanLevel, TrainingSession, WodFormat } from "@/lib/types";

const DISCIPLINAS = ["Powerbuilding", "Powerlifting", "Hipertrofia", "Weightlifting", "CrossFit"];
const NIVELES: PlanLevel[] = ["Principiante", "Intermedio", "Avanzado"];

/** Editar nombre/descripción/disciplina/nivel/precio — nunca el calendario (eso ya quedó fijo
 *  desde la creación, cambiarlo pediría recalcular los días ya armados). Funciona igual esté
 *  publicado o no: subir/bajar el precio de un plan ya publicado es normal. */
function EditPlanSheet({
  open,
  onClose,
  planId,
  plan,
  onSaved,
}: {
  open: boolean;
  onClose: () => void;
  planId: string;
  plan: MesocycleFull;
  onSaved: (message: string) => void;
}) {
  const updatePlan = useUpdatePlan(planId);
  const [name, setName] = useState(plan.name ?? "");
  const [description, setDescription] = useState(plan.description ?? "");
  const [discipline, setDiscipline] = useState(plan.discipline);
  const [level, setLevel] = useState<PlanLevel>((plan.level as PlanLevel) ?? "Intermedio");
  const [price, setPrice] = useState(plan.price != null ? String(plan.price) : "");
  const [error, setError] = useState<string | null>(null);

  function handleSubmit() {
    setError(null);
    if (!name.trim()) return setError("Dale un nombre al plan.");
    const precioNum = Number(price);

    updatePlan.mutate(
      {
        name: name.trim(),
        description: description.trim(),
        discipline,
        level,
        price: price && precioNum > 0 ? precioNum : null,
      },
      {
        onSuccess: () => {
          onSaved("¡Plan actualizado!");
          onClose();
        },
        onError: (err) => setError(err instanceof Error ? err.message : "No se pudo guardar."),
      },
    );
  }

  return (
    <Sheet open={open} onClose={onClose} title="Editar plan">
      <div className="space-y-4">
        <Field label="Nombre del plan" value={name} onChange={(e) => setName(e.target.value)} />

        <label className="block">
          <span className="mb-1.5 block text-sm font-medium text-muted">Descripción (para el catálogo)</span>
          <textarea
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            rows={3}
            maxLength={2000}
            className="w-full rounded-xl border border-line bg-surface-2 px-3.5 py-2.5 text-fg placeholder:text-muted/50 focus:border-brand focus:outline-none"
          />
        </label>

        <label className="block">
          <span className="mb-1.5 block text-sm font-medium text-muted">Disciplina</span>
          <select
            value={discipline}
            onChange={(e) => setDiscipline(e.target.value)}
            className="min-h-12 w-full rounded-xl border border-line bg-surface-2 px-3.5 text-fg"
          >
            {DISCIPLINAS.map((d) => (
              <option key={d} value={d}>
                {d}
              </option>
            ))}
          </select>
        </label>

        <label className="block">
          <span className="mb-1.5 block text-sm font-medium text-muted">Nivel</span>
          <select
            value={level}
            onChange={(e) => setLevel(e.target.value as PlanLevel)}
            className="min-h-12 w-full rounded-xl border border-line bg-surface-2 px-3.5 text-fg"
          >
            {NIVELES.map((n) => (
              <option key={n} value={n}>
                {n}
              </option>
            ))}
          </select>
        </label>

        <Field
          label="Precio (vacío = gratis)"
          type="number"
          inputMode="decimal"
          min="0"
          value={price}
          onChange={(e) => setPrice(e.target.value)}
        />

        {error && <p className="text-sm font-medium text-danger">{error}</p>}
        <Button full loading={updatePlan.isPending} onClick={handleSubmit}>
          Guardar cambios
        </Button>
      </div>
    </Sheet>
  );
}

/** Dentro del bloque Metabólico de un día del plan: en vez (o además) del esquema rígido de
 *  ejercicios/series, se escribe el WOD tal cual en texto libre y se elige cómo se puntúa --
 *  mismo criterio que WodBlockCard en SessionSetsEditor.tsx, pero contra los endpoints propios
 *  de planes (un plan no tiene dueño, así que no puede usar los endpoints generales de sesión). */
function PlanWodBlockCard({
  planId,
  session,
  onSaved,
  onRemoved,
}: {
  planId: string;
  session: TrainingSession;
  onSaved: () => void;
  onRemoved: () => void;
}) {
  const updateMeta = useUpdatePlanSessionMeta(planId);
  const setWodFormat = useSetPlanSessionWodFormat(planId);
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
    if (!window.confirm("¿Borrar la descripción libre y el puntaje del WOD de este día del plan?")) return;
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

/** Formulario para editar un ejercicio ya agregado a un día del plan: nombre, series (una por una,
 *  con rampas), repeticiones, carga, RPE, bloque y nota. Se guarda en UNA petición: todas las
 *  series del ejercicio cambian juntas o ninguna. */
function PlanExerciseEditor({
  planId,
  sessionId,
  group,
  onSaved,
  onClose,
}: {
  planId: string;
  sessionId: string;
  group: ExerciseGroup;
  onSaved: (message: string) => void;
  onClose: () => void;
}) {
  const updateExercise = useUpdatePlanExercise(planId);
  const deleteSet = useDeletePlanSet(planId);
  const [draft, cambiar] = useExerciseDraft(() => draftDeEjercicio(group, true));
  const [error, setError] = useState<string | null>(null);

  function guardar() {
    setError(null);
    if (!draft.name.trim()) return setError("Escribe el nombre del ejercicio.");
    updateExercise.mutate(
      {
        sessionId,
        body: {
          set_ids: group.sets.map((s) => s.id),
          exercise_name: draft.name.trim(),
          prescribed_sets: draft.filas.length,
          prescribed_reps: draft.filas[0].reps,
          ...camposComunes(draft),
          series: seriesParaEnviar(draft),
          coach_note: draft.nota.trim(),
        },
      },
      {
        onSuccess: (response) => onSaved(response.message ?? "Ejercicio actualizado."),
        onError: (err) => setError(err instanceof Error ? err.message : "No se pudo guardar."),
      },
    );
  }

  return (
    <div className="rounded-xl border border-line bg-surface-2/40 p-3">
      <div className="mb-3 flex items-center justify-between gap-2">
        <p className="font-bold">{group.name}</p>
        <button
          type="button"
          aria-label="Quitar ejercicio"
          disabled={deleteSet.isPending || updateExercise.isPending}
          onClick={() => group.sets.forEach((s) => deleteSet.mutate(s.id))}
          className="rounded-lg p-1.5 text-danger active:bg-danger/10 disabled:opacity-40"
        >
          <IconTrash className="h-4 w-4" />
        </button>
      </div>

      <ExerciseFormFields draft={draft} onChange={cambiar} tipos={["porcentaje", "kg", "libre"]} modo="porSerie" />

      {error && <p className="mt-2 text-sm font-medium text-danger">{error}</p>}
      <div className="mt-3 flex gap-2">
        <Button variant="ghost" className="grow" disabled={updateExercise.isPending} onClick={onClose}>
          Cancelar
        </Button>
        <Button variant="secondary" className="grow" loading={updateExercise.isPending} onClick={guardar}>
          Guardar ajustes
        </Button>
      </div>
    </div>
  );
}

function DayEditor({
  planId,
  session,
  dayNumber,
  onFeedback,
}: {
  planId: string;
  session: TrainingSession;
  dayNumber: number;
  onFeedback: (message: string) => void;
}) {
  const addSet = useAddPlanSet(planId);
  const deleteSet = useDeletePlanSet(planId);
  const updateMeta = useUpdatePlanSessionMeta(planId);
  const sessionId = session.id;
  const sets = session.sets;
  const [forzarMetcon, setForzarMetcon] = useState(Boolean(session.wod_notes) || session.wod_format != null);
  const [forzarCalentamiento, setForzarCalentamiento] = useState(Boolean(session.warmup_notes));
  // El ejercicio cuyo formulario está abierto (por su firma: al guardar cambia y se cierra solo)
  const [editando, setEditando] = useState<string | null>(null);
  // Los bloques con texto libre (WOD y calentamiento) se muestran aunque aún no tengan ejercicios.
  // Se respeta el orden de bloques guardado en este día (al adquirir el plan se copia tal cual).
  const forzados = [...(forzarMetcon ? ["metcon"] : []), ...(forzarCalentamiento ? ["warmup"] : [])];
  const bloques = groupByBlock(sets, session.block_order, forzados);
  const blockKeys = bloques.map((b) => b.key).filter((key): key is string => key !== null);
  const tieneMetcon = bloques.some((b) => b.key === "metcon");
  const tieneCalentamiento = bloques.some((b) => b.key === "warmup");
  const vacio = sets.length === 0 && !tieneMetcon && !tieneCalentamiento;

  const meta: MetaGuardado = {
    guardar: (body, alTerminar) => updateMeta.mutate({ sessionId, body }, { onSuccess: alTerminar }),
    guardando: updateMeta.isPending,
  };

  // Botones para agregar un bloque de texto libre que todavía no está en el día
  const botonesDeTexto = (
    <div className="space-y-2">
      {!tieneCalentamiento && (
        <button
          type="button"
          onClick={() => setForzarCalentamiento(true)}
          className="w-full rounded-2xl border border-dashed border-line bg-surface p-3 text-left text-sm font-bold active:bg-surface-2"
        >
          🔥 Añadir calentamiento
        </button>
      )}
      {!tieneMetcon && (
        <button
          type="button"
          onClick={() => setForzarMetcon(true)}
          className="w-full rounded-2xl border border-dashed border-line bg-surface p-3 text-left text-sm font-bold active:bg-surface-2"
        >
          🔥 Añadir WOD
        </button>
      )}
    </div>
  );

  const [draft, cambiar] = useExerciseDraft(() => nuevoDraft({ reps: 5, tipo: "porcentaje" }));
  const [error, setError] = useState<string | null>(null);

  function handleAdd() {
    setError(null);
    if (!draft.name.trim()) return setError("Escribe el nombre del ejercicio.");

    addSet.mutate(
      {
        sessionId,
        body: {
          exercise_name: draft.name.trim(),
          prescribed_sets: draft.filas.length,
          prescribed_reps: draft.filas[0].reps,
          ...camposComunes(draft),
          series: seriesParaEnviar(draft),
          coach_note: draft.nota.trim() || null,
        },
      },
      {
        onSuccess: (response) => {
          onFeedback(response.message ?? "Ejercicio agregado.");
          cambiar({ name: "", referencia: "", nota: "" });
        },
        onError: (err) => setError(err instanceof Error ? err.message : "No se pudo agregar."),
      },
    );
  }

  return (
    <Card>
      <p className="mb-3 font-bold">📆 Día {dayNumber}</p>

      <div className="mb-3 space-y-3">
        <BlockOrderEditor blockKeys={blockKeys} meta={meta} integrado onSaved={() => onFeedback("¡Orden de bloques actualizado!")} />
      </div>

      {vacio ? (
        <p className="mb-3 text-sm text-muted">Todavía sin ejercicios.</p>
      ) : (
        <div className="mb-3 space-y-3">
          {bloques.map((bloque, indiceBloque) => (
            <div key={bloque.key ?? `sin-bloque-${indiceBloque}`}>
              {bloque.label && (
                <p className="mb-1.5 text-xs font-semibold tracking-wide text-muted uppercase">{bloque.label}</p>
              )}
              {bloque.key === "warmup" && (
                <WarmupNotesCard
                  session={session}
                  meta={meta}
                  onSaved={() => onFeedback("¡Pautas de calentamiento guardadas!")}
                  onRemoved={() => setForzarCalentamiento(false)}
                />
              )}
              {bloque.key === "metcon" && (
                <PlanWodBlockCard
                  planId={planId}
                  session={session}
                  onSaved={() => onFeedback("¡WOD guardado!")}
                  onRemoved={() => setForzarMetcon(false)}
                />
              )}
              <div className="space-y-2">
                {bloque.groups.map((group) => {
                  const firma = firmaDeEjercicio(group);
                  return firma === editando ? (
                    <PlanExerciseEditor
                      key={firma}
                      planId={planId}
                      sessionId={sessionId}
                      group={group}
                      onSaved={(mensaje) => {
                        setEditando(null);
                        onFeedback(mensaje);
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
          {botonesDeTexto}
        </div>
      )}
      {vacio && <div className="mb-3">{botonesDeTexto}</div>}

      <div className="space-y-3 border-t border-line pt-3">
        <p className="text-sm font-semibold text-muted">➕ Agregar ejercicio</p>
        <ExerciseFormFields draft={draft} onChange={cambiar} tipos={["porcentaje", "kg", "libre"]} modo="porSerie" />

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
  const queryClient = useQueryClient();
  const { data, isPending, error, refetch } = usePlanDetail(planId);
  const [toast, setToast] = useState<string | null>(null);
  const [editOpen, setEditOpen] = useState(false);

  // El backend solo manda el contenido completo (con ejercicios/series) al autor/admin — si
  // esto viniera en modo "vista previa" es que este plan no es tuyo, no hay nada que editar.
  const full = data && !data.is_preview ? data : undefined;
  const sessions = [...(full?.sessions ?? [])].sort((a, b) => (a.day_offset ?? 0) - (b.day_offset ?? 0));

  return (
    <>
      <PageHeader
        title={data?.name ?? "Plan"}
        subtitle="Contenido del plan"
        back="/coach/planes"
        action={
          full && (
            <button
              type="button"
              onClick={() => setEditOpen(true)}
              className="min-h-10 rounded-xl bg-surface-2 px-3 text-sm font-semibold text-fg active:bg-line"
            >
              ✏️ Editar
            </button>
          )
        }
      />

      {full && (
        <CoverUploader
          coverPath={`/plans/${planId}/cover`}
          uploadPath={`/plans/${planId}/cover`}
          hasImage={full.has_cover_image}
          onChanged={() => {
            void refetch();
            void queryClient.invalidateQueries({ queryKey: coachKeys.myPlans });
          }}
          label="Foto de portada"
        />
      )}

      <p className="mb-4 text-sm text-muted">
        Las cargas en % de 1RM se convierten a kilos automáticamente cuando alguien adquiere el
        plan, usando SUS propias marcas. Usa kg fijos solo para cargas absolutas.
      </p>

      {isPending && <LoadingList rows={3} />}
      {!isPending && error && <ErrorState error={error} onRetry={() => void refetch()} />}
      {!isPending && !error && data?.is_preview && (
        <EmptyState title="Este plan no te pertenece">
          Solo el coach que lo creó (o un admin) puede editar su contenido.
        </EmptyState>
      )}
      {!isPending && !error && full && sessions.length === 0 && (
        <EmptyState title="Este plan no tiene días configurados" />
      )}

      <div className="space-y-3">
        {sessions.map((session) => (
          <DayEditor
            key={session.id}
            planId={planId!}
            session={session}
            dayNumber={(session.day_offset ?? 0) + 1}
            onFeedback={setToast}
          />
        ))}
      </div>

      {full && (
        <EditPlanSheet
          open={editOpen}
          onClose={() => setEditOpen(false)}
          planId={planId!}
          plan={full}
          onSaved={setToast}
        />
      )}

      {toast && <Toast message={toast} onDismiss={() => setToast(null)} />}
    </>
  );
}
