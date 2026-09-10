import { useState } from "react";
import { useParams } from "react-router-dom";

import { PageHeader } from "@/components/AppShell";
import { SessionSetsEditor } from "@/components/SessionSetsEditor";
import { IconChevronRight, IconTrash } from "@/components/icons";
import { Button, Card, EmptyState, ErrorState, Field, LoadingList, Stepper, Toast } from "@/components/ui";
import { useGroupBulkAdd, useGroupBulkDelete, useGroupBulkUpdate, useGroupMesocycles } from "@/lib/coachQueries";
import { shortDate } from "@/lib/dates";
import { useMesocycle } from "@/lib/queries";
import { groupSets } from "@/lib/sessions";
import type { ExerciseGroup } from "@/lib/sessions";
import type { TrainingSession } from "@/lib/types";

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

  const first = group.sets[0];
  const [name, setName] = useState(group.name);
  const [series, setSeries] = useState(group.sets.length);
  const [reps, setReps] = useState(first.prescribed_reps);
  const [rpe, setRpe] = useState(first.rpe ?? 0);
  const [weight, setWeight] = useState(first.prescribed_weight ?? 0);

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
              prescribed_weight: weight > 0 ? weight : null,
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
  const [name, setName] = useState("");
  const [series, setSeries] = useState(3);
  const [reps, setReps] = useState(8);
  const [rpe, setRpe] = useState(7);
  const [weight, setWeight] = useState(0);
  const [error, setError] = useState<string | null>(null);

  return (
    <Card className="border-dashed">
      <p className="mb-3 font-bold">➕ Añadir para TODO el grupo</p>
      <Field label="Ejercicio" value={name} onChange={(e) => setName(e.target.value)} className="mb-3" />
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
              prescribed_weight: weight > 0 ? weight : null,
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
      {sessions.map((session) => {
        const groups = groupSets(session.sets);
        return (
          <DateAccordion key={session.id} label={shortDate(session.scheduled_date)}>
            {groups.length === 0 && <p className="text-sm text-muted">Sin ejercicios en esta fecha.</p>}
            {groups.map((group, index) => (
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
            <BulkAddForm
              groupId={groupId}
              programName={programName}
              programStartDate={programStartDate}
              scheduledDate={session.scheduled_date}
              onFeedback={onFeedback}
            />
          </DateAccordion>
        );
      })}
    </div>
  );
}

function AthleteTab({ mesocycleId, onFeedback }: { mesocycleId: string; onFeedback: (m: string) => void }) {
  const { data, isPending, error, refetch } = useMesocycle(mesocycleId);
  if (isPending) return <LoadingList rows={3} />;
  if (error) return <ErrorState error={error} onRetry={() => void refetch()} />;

  const sessions = [...(data?.sessions ?? [])].sort((a, b) => a.scheduled_date.localeCompare(b.scheduled_date));

  return (
    <div className="space-y-3">
      {sessions.map((session: TrainingSession) => (
        <DateAccordion key={session.id} label={shortDate(session.scheduled_date)}>
          <SessionSetsEditor mesocycleId={mesocycleId} session={session} onFeedback={onFeedback} />
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
  const decodedName = decodeURIComponent(programName ?? "");
  const programs = useGroupMesocycles(groupId);
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

  return (
    <>
      <PageHeader title={program.name} subtitle={program.discipline} back={`/coach/grupos/${groupId}`} />

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
      {selectedAthlete && <AthleteTab mesocycleId={selectedAthlete.mesocycle_id} onFeedback={setToast} />}

      {toast && <Toast message={toast} onDismiss={() => setToast(null)} />}
    </>
  );
}
