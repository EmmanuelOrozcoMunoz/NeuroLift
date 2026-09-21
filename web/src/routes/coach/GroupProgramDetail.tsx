import { useState } from "react";
import { useNavigate, useParams } from "react-router-dom";

import { PageHeader } from "@/components/AppShell";
import { BlockSelect } from "@/components/BlockSelect";
import { SessionSetsEditor } from "@/components/SessionSetsEditor";
import { IconChevronRight, IconTrash } from "@/components/icons";
import { Button, Card, EmptyState, ErrorState, Field, LoadingList, Segmented, Stepper, Toast, cx } from "@/components/ui";
import {
  useDeleteGroupProgram,
  useGroupBulkAdd,
  useGroupBulkDelete,
  useGroupBulkSetWodFormat,
  useGroupBulkSetWodNotes,
  useGroupBulkUpdate,
  useGroupMesocycles,
} from "@/lib/coachQueries";
import { shortDate } from "@/lib/dates";
import { useMesocycle } from "@/lib/queries";
import { groupByBlock } from "@/lib/sessions";
import { useWeightUnit, WeightStepper } from "@/lib/units";
import { WOD_OTHER_SCORE_TYPES, WOD_TIMER_TEMPLATES, wodFormatUsesTimeCap } from "@/lib/wod";
import type { ExerciseGroup } from "@/lib/sessions";
import type { TrainingSession, WodFormat } from "@/lib/types";

/** Dentro del bloque Metabólico, para TODO el grupo a la vez: el coach escribe el WOD tal cual
 *  en texto libre y elige cómo se puntúa -- convive con los ejercicios estructurados que ya
 *  tenga ese mismo bloque (ver BulkExerciseBlock), mismo criterio que WodBlockCard en
 *  SessionSetsEditor.tsx pero aplicado a todos los atletas del programa de una sola vez. */
function BulkWodBlockCard({
  groupId,
  programName,
  programStartDate,
  scheduledDate,
  currentNotes,
  currentFormat,
  currentTimeCapSeconds,
  onFeedback,
  onRemoved,
}: {
  groupId: string;
  programName: string;
  programStartDate: string;
  scheduledDate: string;
  currentNotes: string | null;
  currentFormat: WodFormat | null;
  currentTimeCapSeconds: number | null;
  onFeedback: (message: string) => void;
  onRemoved: () => void;
}) {
  const bulkSetWodNotes = useGroupBulkSetWodNotes(groupId);
  const bulkSetWodFormat = useGroupBulkSetWodFormat(groupId);
  const [texto, setTexto] = useState(currentNotes ?? "");
  const [seleccionado, setSeleccionado] = useState<WodFormat | "">(currentFormat ?? "");
  const [timerMin, setTimerMin] = useState(Math.round((currentTimeCapSeconds ?? 0) / 60));

  const base = { program_name: programName, program_start_date: programStartDate, scheduled_date: scheduledDate };

  function guardarTexto() {
    if (texto === (currentNotes ?? "")) return;
    bulkSetWodNotes.mutate({ ...base, wod_notes: texto.trim() || "" }, { onSuccess: (r) => onFeedback(r.message) });
  }

  function guardarFormato(formato: WodFormat | "", minutos: number) {
    bulkSetWodFormat.mutate(
      {
        ...base,
        wod_format: formato || null,
        time_cap_seconds: formato && wodFormatUsesTimeCap(formato) && minutos > 0 ? minutos * 60 : null,
      },
      { onSuccess: (r) => onFeedback(r.message) },
    );
  }

  function elegir(valor: WodFormat) {
    const nuevo = seleccionado === valor ? "" : valor;
    setSeleccionado(nuevo);
    guardarFormato(nuevo, timerMin);
  }

  function quitar() {
    if (!window.confirm("¿Borrar la descripción libre y el puntaje del WOD para todo el grupo?")) return;
    bulkSetWodNotes.mutate({ ...base, wod_notes: "" });
    bulkSetWodFormat.mutate({ ...base, wod_format: null, time_cap_seconds: null });
    onRemoved();
  }

  return (
    <Card>
      <div className="mb-2 flex items-center justify-between gap-2">
        <p className="text-sm font-semibold text-muted">📋 Escribir el WOD como texto, para TODO el grupo (opcional)</p>
        <button
          type="button"
          onClick={quitar}
          className="rounded-lg p-1.5 text-danger active:bg-danger/10"
          aria-label="Borrar descripción y puntaje del WOD para todo el grupo"
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
              disabled={bulkSetWodFormat.isPending}
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
              disabled={bulkSetWodFormat.isPending}
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

function BulkExerciseBlock({
  groupId,
  programName,
  programStartDate,
  scheduledDate,
  group,
  onFeedback,
}: {
  groupId: string;
  programName: string;
  programStartDate: string;
  scheduledDate: string;
  group: ExerciseGroup;
  onFeedback: (message: string) => void;
}) {
  const bulkUpdate = useGroupBulkUpdate(groupId);
  const bulkDelete = useGroupBulkDelete(groupId);
  const unit = useWeightUnit();

  const first = group.sets[0];
  const [name, setName] = useState(group.name);
  const [series, setSeries] = useState(group.sets.length);
  const [reps, setReps] = useState(first.prescribed_reps);
  const [rpe, setRpe] = useState(first.rpe ?? 0);
  const [tipoCarga, setTipoCarga] = useState<"kg" | "porcentaje">(first.prescribed_percentage ? "porcentaje" : "kg");
  const [weight, setWeight] = useState(first.prescribed_weight ?? 0);
  const [porcentaje, setPorcentaje] = useState(first.prescribed_percentage ?? 75);
  const [referencia, setReferencia] = useState(first.reference_exercise ?? "");
  const [wRxMale, setWRxMale] = useState(0);
  const [wRxFemale, setWRxFemale] = useState(0);
  const [wScaledMale, setWScaledMale] = useState(0);
  const [wScaledFemale, setWScaledFemale] = useState(0);
  const [block, setBlock] = useState(first.block ?? "");
  const esMetcon = block === "metcon";

  const base = { program_name: programName, program_start_date: programStartDate, scheduled_date: scheduledDate };

  return (
    <Card>
      <div className="mb-3 flex items-center justify-between gap-2">
        <p className="font-bold">{group.name}</p>
        <button
          type="button"
          aria-label="Quitar de todo el grupo"
          disabled={bulkDelete.isPending}
          onClick={() =>
            bulkDelete.mutate(
              { ...base, exercise_name: group.name },
              { onSuccess: (r) => onFeedback(r.message) },
            )
          }
          className="rounded-lg p-1.5 text-danger active:bg-danger/10 disabled:opacity-40"
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
      </div>

      {!esMetcon && (
        <div className="mt-3 border-t border-line pt-3">
          <span className="mb-1.5 block text-xs font-medium text-muted">Carga</span>
          <Segmented<"kg" | "porcentaje">
            value={tipoCarga}
            onChange={setTipoCarga}
            options={[
              { value: "kg", label: `${unit === "lb" ? "Lb" : "Kg"} fijos` },
              { value: "porcentaje", label: "% de 1RM" },
            ]}
          />
          <div className="mt-2">
            {tipoCarga === "porcentaje" ? (
              <>
                <span className="mb-1.5 block text-xs font-medium text-muted">Porcentaje (%)</span>
                <Stepper value={porcentaje} onChange={setPorcentaje} step={5} min={0} max={150} compact />
              </>
            ) : (
              <>
                <span className="mb-1.5 block text-xs font-medium text-muted">Peso ({unit})</span>
                <WeightStepper valueKg={weight} onChangeKg={setWeight} compact />
              </>
            )}
          </div>
          {tipoCarga === "porcentaje" && (
            <Field
              label="1RM de referencia (opcional)"
              placeholder="Ej. Back Squat — vacío usa el mismo ejercicio"
              value={referencia}
              onChange={(e) => setReferencia(e.target.value)}
              className="mt-2"
            />
          )}
          <p className="mt-2 text-xs text-muted">
            Cada atleta recibe su propio peso, calculado con sus marcas ya registradas.
          </p>
        </div>
      )}

      {esMetcon && (
        <div className="mt-3 border-t border-line pt-3">
          <p className="mb-2 text-xs font-medium text-muted">Pesos del WOD ({unit}) — por categoría y género</p>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <span className="mb-1 block text-[11px] text-muted">RX Hombres</span>
              <WeightStepper valueKg={wRxMale} onChangeKg={setWRxMale} compact />
            </div>
            <div>
              <span className="mb-1 block text-[11px] text-muted">RX Mujeres</span>
              <WeightStepper valueKg={wRxFemale} onChangeKg={setWRxFemale} compact />
            </div>
            <div>
              <span className="mb-1 block text-[11px] text-muted">Scaled Hombres</span>
              <WeightStepper valueKg={wScaledMale} onChangeKg={setWScaledMale} compact />
            </div>
            <div>
              <span className="mb-1 block text-[11px] text-muted">Scaled Mujeres</span>
              <WeightStepper valueKg={wScaledFemale} onChangeKg={setWScaledFemale} compact />
            </div>
          </div>
        </div>
      )}

      <Button
        variant="secondary"
        full
        className="mt-3"
        loading={bulkUpdate.isPending}
        onClick={() =>
          bulkUpdate.mutate(
            {
              ...base,
              exercise_name: group.name,
              new_exercise_name: name.trim() || group.name,
              prescribed_sets: series,
              prescribed_reps: reps,
              rpe: rpe > 0 ? rpe : null,
              prescribed_weight: !esMetcon && tipoCarga === "kg" && weight > 0 ? weight : null,
              prescribed_percentage: !esMetcon && tipoCarga === "porcentaje" ? porcentaje : null,
              reference_exercise:
                !esMetcon && tipoCarga === "porcentaje" && referencia.trim() ? referencia.trim() : null,
              prescribed_weight_rx_male: esMetcon && wRxMale > 0 ? wRxMale : null,
              prescribed_weight_rx_female: esMetcon && wRxFemale > 0 ? wRxFemale : null,
              prescribed_weight_scaled_male: esMetcon && wScaledMale > 0 ? wScaledMale : null,
              prescribed_weight_scaled_female: esMetcon && wScaledFemale > 0 ? wScaledFemale : null,
              block: block || null,
            },
            { onSuccess: (r) => onFeedback(r.message) },
          )
        }
      >
        Guardar para TODO el grupo
      </Button>
    </Card>
  );
}

function BulkAddForm({
  groupId,
  programName,
  programStartDate,
  scheduledDate,
  onFeedback,
}: {
  groupId: string;
  programName: string;
  programStartDate: string;
  scheduledDate: string;
  onFeedback: (message: string) => void;
}) {
  const bulkAdd = useGroupBulkAdd(groupId);
  const unit = useWeightUnit();
  const [name, setName] = useState("");
  const [series, setSeries] = useState(3);
  const [reps, setReps] = useState(8);
  const [rpe, setRpe] = useState(7);
  const [tipoCarga, setTipoCarga] = useState<"kg" | "porcentaje">("kg");
  const [weight, setWeight] = useState(0);
  const [porcentaje, setPorcentaje] = useState(75);
  const [referencia, setReferencia] = useState("");
  const [wRxMale, setWRxMale] = useState(0);
  const [wRxFemale, setWRxFemale] = useState(0);
  const [wScaledMale, setWScaledMale] = useState(0);
  const [wScaledFemale, setWScaledFemale] = useState(0);
  const [block, setBlock] = useState("");
  const [error, setError] = useState<string | null>(null);
  const esMetcon = block === "metcon";

  return (
    <Card className="border-dashed">
      <p className="mb-3 font-bold">➕ Añadir para TODO el grupo</p>
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
      </div>

      {!esMetcon && (
        <div className="mt-3 border-t border-line pt-3">
          <span className="mb-1.5 block text-xs font-medium text-muted">Carga</span>
          <Segmented<"kg" | "porcentaje">
            value={tipoCarga}
            onChange={setTipoCarga}
            options={[
              { value: "kg", label: `${unit === "lb" ? "Lb" : "Kg"} fijos` },
              { value: "porcentaje", label: "% de 1RM" },
            ]}
          />
          <div className="mt-2">
            {tipoCarga === "porcentaje" ? (
              <>
                <span className="mb-1.5 block text-xs font-medium text-muted">Porcentaje (%)</span>
                <Stepper value={porcentaje} onChange={setPorcentaje} step={5} min={0} max={150} compact />
              </>
            ) : (
              <>
                <span className="mb-1.5 block text-xs font-medium text-muted">Peso ({unit})</span>
                <WeightStepper valueKg={weight} onChangeKg={setWeight} compact />
              </>
            )}
          </div>
          {tipoCarga === "porcentaje" && (
            <Field
              label="1RM de referencia (opcional)"
              placeholder="Ej. Back Squat — vacío usa el mismo ejercicio"
              value={referencia}
              onChange={(e) => setReferencia(e.target.value)}
              className="mt-2"
            />
          )}
          <p className="mt-2 text-xs text-muted">
            Cada atleta recibe su propio peso, calculado con sus marcas ya registradas.
          </p>
        </div>
      )}

      {esMetcon && (
        <div className="mt-3 border-t border-line pt-3">
          <p className="mb-2 text-xs font-medium text-muted">Pesos del WOD ({unit}) — por categoría y género</p>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <span className="mb-1 block text-[11px] text-muted">RX Hombres</span>
              <WeightStepper valueKg={wRxMale} onChangeKg={setWRxMale} compact />
            </div>
            <div>
              <span className="mb-1 block text-[11px] text-muted">RX Mujeres</span>
              <WeightStepper valueKg={wRxFemale} onChangeKg={setWRxFemale} compact />
            </div>
            <div>
              <span className="mb-1 block text-[11px] text-muted">Scaled Hombres</span>
              <WeightStepper valueKg={wScaledMale} onChangeKg={setWScaledMale} compact />
            </div>
            <div>
              <span className="mb-1 block text-[11px] text-muted">Scaled Mujeres</span>
              <WeightStepper valueKg={wScaledFemale} onChangeKg={setWScaledFemale} compact />
            </div>
          </div>
        </div>
      )}
      {error && <p className="mt-2 text-sm font-medium text-danger">{error}</p>}
      <Button
        full
        className="mt-3"
        loading={bulkAdd.isPending}
        onClick={() => {
          if (!name.trim()) return setError("Escribe el nombre del ejercicio.");
          setError(null);
          bulkAdd.mutate(
            {
              program_name: programName,
              program_start_date: programStartDate,
              scheduled_date: scheduledDate,
              exercise_name: name.trim(),
              prescribed_sets: series,
              prescribed_reps: reps,
              rpe: rpe > 0 ? rpe : null,
              prescribed_weight: !esMetcon && tipoCarga === "kg" && weight > 0 ? weight : null,
              prescribed_percentage: !esMetcon && tipoCarga === "porcentaje" ? porcentaje : null,
              reference_exercise:
                !esMetcon && tipoCarga === "porcentaje" && referencia.trim() ? referencia.trim() : null,
              prescribed_weight_rx_male: esMetcon && wRxMale > 0 ? wRxMale : null,
              prescribed_weight_rx_female: esMetcon && wRxFemale > 0 ? wRxFemale : null,
              prescribed_weight_scaled_male: esMetcon && wScaledMale > 0 ? wScaledMale : null,
              prescribed_weight_scaled_female: esMetcon && wScaledFemale > 0 ? wScaledFemale : null,
              block: block || null,
            },
            { onSuccess: (r) => { onFeedback(r.message); setName(""); } },
          );
        }}
      >
        Añadir a todo el grupo
      </Button>
    </Card>
  );
}

function DateAccordion({ label, children }: { label: string; children: React.ReactNode }) {
  const [open, setOpen] = useState(false);
  return (
    <div className="rounded-2xl border border-line bg-surface">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="flex w-full items-center justify-between px-4 py-3.5 text-left"
      >
        <span className="font-bold">{label}</span>
        <IconChevronRight className={`h-5 w-5 text-muted transition-transform ${open ? "rotate-90" : ""}`} />
      </button>
      {open && <div className="space-y-3 border-t border-line p-3">{children}</div>}
    </div>
  );
}

/** Una fecha del programa, para TODO el grupo -- lleva su propio estado de si el bloque
 *  Metabólico/WOD está "activado" para poder mostrarlo aunque todavía no tenga ejercicios
 *  estructurados ni descripción guardada (mismo criterio que SessionSetsEditor). */
function GroupDateSection({
  groupId,
  programName,
  programStartDate,
  session,
  onFeedback,
}: {
  groupId: string;
  programName: string;
  programStartDate: string;
  session: TrainingSession;
  onFeedback: (message: string) => void;
}) {
  const [forzarMetcon, setForzarMetcon] = useState(Boolean(session.wod_notes) || session.wod_format != null);
  const bloques = groupByBlock(session.sets, session.block_order, forzarMetcon);
  const tieneMetcon = bloques.some((b) => b.key === "metcon");

  return (
    <DateAccordion label={shortDate(session.scheduled_date)}>
      {session.sets.length === 0 && !tieneMetcon && (
        <p className="text-sm text-muted">Sin ejercicios en esta fecha.</p>
      )}
      {bloques.map((bloque, indiceBloque) => (
        <div key={bloque.key ?? `sin-bloque-${indiceBloque}`} className="space-y-3">
          {bloque.label && (
            <p className="text-xs font-semibold tracking-wide text-muted uppercase">{bloque.label}</p>
          )}
          {bloque.key === "metcon" && (
            <BulkWodBlockCard
              groupId={groupId}
              programName={programName}
              programStartDate={programStartDate}
              scheduledDate={session.scheduled_date}
              currentNotes={session.wod_notes}
              currentFormat={session.wod_format}
              currentTimeCapSeconds={session.wod_time_cap_seconds}
              onFeedback={onFeedback}
              onRemoved={() => setForzarMetcon(false)}
            />
          )}
          {bloque.groups.map((group, index) => (
            <BulkExerciseBlock
              key={`${group.name}-${index}`}
              groupId={groupId}
              programName={programName}
              programStartDate={programStartDate}
              scheduledDate={session.scheduled_date}
              group={group}
              onFeedback={onFeedback}
            />
          ))}
        </div>
      ))}
      <BulkAddForm
        groupId={groupId}
        programName={programName}
        programStartDate={programStartDate}
        scheduledDate={session.scheduled_date}
        onFeedback={onFeedback}
      />
      {!tieneMetcon && (
        <button
          type="button"
          onClick={() => setForzarMetcon(true)}
          className="w-full rounded-2xl border border-dashed border-line bg-surface p-4 text-left font-bold active:bg-surface-2"
        >
          🔥 Añadir bloque metabólico (WOD) para todo el grupo
        </button>
      )}
    </DateAccordion>
  );
}

function GroupWideTab({
  groupId,
  programName,
  programStartDate,
  referenceMesocycleId,
  onFeedback,
}: {
  groupId: string;
  programName: string;
  programStartDate: string;
  referenceMesocycleId: string;
  onFeedback: (message: string) => void;
}) {
  const { data, isPending, error, refetch } = useMesocycle(referenceMesocycleId);

  if (isPending) return <LoadingList rows={3} />;
  if (error) return <ErrorState error={error} onRetry={() => void refetch()} />;

  const sessions = [...(data?.sessions ?? [])].sort((a, b) => a.scheduled_date.localeCompare(b.scheduled_date));

  return (
    <div className="space-y-3">
      <p className="text-xs text-muted">
        Vista de referencia. Los cambios aquí se aplican a todos los atletas del grupo que
        tengan ese ejercicio en esa fecha — cada quien conserva su propio peso salvo que lo
        cambies explícitamente aquí.
      </p>
      {sessions.map((session) => (
        <GroupDateSection
          key={session.id}
          groupId={groupId}
          programName={programName}
          programStartDate={programStartDate}
          session={session}
          onFeedback={onFeedback}
        />
      ))}
    </div>
  );
}

function AthleteTab({
  mesocycleId,
  discipline,
  onFeedback,
}: {
  mesocycleId: string;
  discipline: string;
  onFeedback: (m: string) => void;
}) {
  const { data, isPending, error, refetch } = useMesocycle(mesocycleId);
  if (isPending) return <LoadingList rows={3} />;
  if (error) return <ErrorState error={error} onRetry={() => void refetch()} />;

  // Una sesión "adaptada al tiempo" (el atleta tocó "¿Tienes menos tiempo hoy?") vive el mismo
  // día que su original y apunta a ella con parent_session_id — sin filtrarla aquí, el coach ve
  // dos tarjetas con la misma fecha y parece un día duplicado. El coach edita la original; la
  // adaptada la genera y regenera la IA a demanda, no tiene sentido editarla aparte.
  const sessions = [...(data?.sessions ?? [])]
    .filter((s) => !s.parent_session_id)
    .sort((a, b) => a.scheduled_date.localeCompare(b.scheduled_date));

  return (
    <div className="space-y-3">
      {sessions.map((session: TrainingSession) => (
        <DateAccordion key={session.id} label={shortDate(session.scheduled_date)}>
          <SessionSetsEditor
            mesocycleId={mesocycleId}
            discipline={discipline}
            session={session}
            onFeedback={onFeedback}
          />
        </DateAccordion>
      ))}
    </div>
  );
}

export default function GroupProgramDetail() {
  const { groupId, programName, startDate } = useParams<{
    groupId: string;
    programName: string;
    startDate: string;
  }>();
  const navigate = useNavigate();
  const decodedName = decodeURIComponent(programName ?? "");
  const programs = useGroupMesocycles(groupId);
  const deleteProgram = useDeleteGroupProgram(groupId!);
  const [toast, setToast] = useState<string | null>(null);
  const [tab, setTab] = useState<string>("grupo");

  if (programs.isPending) {
    return (
      <>
        <PageHeader title="Programa" back={`/coach/grupos/${groupId}`} />
        <LoadingList rows={4} />
      </>
    );
  }
  if (programs.error) {
    return (
      <>
        <PageHeader title="Programa" back={`/coach/grupos/${groupId}`} />
        <ErrorState error={programs.error} onRetry={() => void programs.refetch()} />
      </>
    );
  }

  const program = programs.data?.find((p) => p.name === decodedName && p.start_date === startDate);
  if (!program) {
    return (
      <>
        <PageHeader title="Programa" back={`/coach/grupos/${groupId}`} />
        <EmptyState title="No se encontró este programa" />
      </>
    );
  }

  const referenceId = program.athletes[0]?.mesocycle_id;
  const selectedAthlete = program.athletes.find((a) => a.user_id === tab);

  function handleDeleteProgram() {
    const confirmado = window.confirm(
      `¿Eliminar el programa "${program!.name}" para ${program!.athletes.length} atleta(s)? Se borrarán todas sus sesiones y series registradas. Esta acción no se puede deshacer.`,
    );
    if (!confirmado) return;

    deleteProgram.mutate(
      { program_name: program!.name, program_start_date: program!.start_date },
      {
        onSuccess: () => navigate(`/coach/grupos/${groupId}`),
        onError: (err) => setToast(err instanceof Error ? err.message : "No se pudo eliminar el programa."),
      },
    );
  }

  return (
    <>
      <PageHeader
        title={program.name}
        subtitle={program.discipline}
        back={`/coach/grupos/${groupId}`}
        action={
          <button
            type="button"
            aria-label="Eliminar programa"
            onClick={handleDeleteProgram}
            disabled={deleteProgram.isPending}
            className="rounded-lg p-2 text-danger active:bg-danger/10 disabled:opacity-40"
          >
            <IconTrash className="h-5 w-5" />
          </button>
        }
      />

      <div className="-mx-4 mb-4 flex gap-2 overflow-x-auto px-4 pb-1">
        <button
          type="button"
          onClick={() => setTab("grupo")}
          className={`shrink-0 rounded-full px-4 py-2 text-sm font-semibold ${
            tab === "grupo" ? "bg-brand text-white" : "bg-surface-2 text-muted"
          }`}
        >
          👥 Grupo completo
        </button>
        {program.athletes.map((athlete) => (
          <button
            key={athlete.user_id}
            type="button"
            onClick={() => setTab(athlete.user_id)}
            className={`shrink-0 rounded-full px-4 py-2 text-sm font-semibold ${
              tab === athlete.user_id ? "bg-brand text-white" : "bg-surface-2 text-muted"
            }`}
          >
            {athlete.full_name}
          </button>
        ))}
      </div>

      {tab === "grupo" && referenceId && (
        <GroupWideTab
          groupId={groupId!}
          programName={program.name}
          programStartDate={program.start_date}
          referenceMesocycleId={referenceId}
          onFeedback={setToast}
        />
      )}
      {selectedAthlete && (
        <AthleteTab
          mesocycleId={selectedAthlete.mesocycle_id}
          discipline={program.discipline}
          onFeedback={setToast}
        />
      )}

      {toast && <Toast message={toast} onDismiss={() => setToast(null)} />}
    </>
  );
}
