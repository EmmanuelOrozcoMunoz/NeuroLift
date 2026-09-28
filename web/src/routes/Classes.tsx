import { useMemo, useState } from "react";

import { PageHeader } from "@/components/AppShell";
import { ClassCard, formatClassTime } from "@/components/ClassCard";
import { IconChevronRight } from "@/components/icons";
import { EmptyState, ErrorState, Field, Sheet, Skeleton, Toast, cx } from "@/components/ui";
import { WeekdayPicker, WEEKDAY_NAMES } from "@/components/WeekdayPicker";
import { ApiError } from "@/lib/api";
import { useCurrentUser } from "@/lib/auth";
import { useBoxMembers } from "@/lib/boxQueries";
import {
  useClasses,
  useClassSchedule,
  useCreateClassProgram,
  useDeactivateClass,
  useSaveClass,
} from "@/lib/classQueries";
import { parseApiDate, todayIso, toApiDate } from "@/lib/dates";
import type { BoxClass, Weekday } from "@/lib/types";

const WEEKDAY_INITIALS = ["L", "M", "X", "J", "V", "S", "D"];
type ToastState = { message: string; tone: "done" | "danger" } | null;

function addDays(iso: string, days: number): string {
  const d = parseApiDate(iso);
  d.setDate(d.getDate() + days);
  return toApiDate(d);
}

/**
 * Horario de clases del box. La misma pantalla para todos, con distinto alcance:
 * - atleta: ve horario, profesor y contenido, y registra la clase del día;
 * - profesor: además programa el contenido de SUS clases (día a día o por bloque);
 * - dueño: además crea, edita y desactiva clases y programa cualquiera.
 */
export default function Classes() {
  const user = useCurrentUser();
  const hoy = todayIso();
  const [selected, setSelected] = useState(hoy);
  const [toast, setToast] = useState<ToastState>(null);
  const notify = (message: string, tone: "done" | "danger" = "done") => setToast({ message, tone });

  const dias = useMemo(() => Array.from({ length: 7 }, (_, i) => addDays(hoy, i)), [hoy]);
  const schedule = useClassSchedule(hoy, 7);
  const esDueno = user.role === "owner";
  const puedeProgramar = user.role === "owner" || user.role === "coach";

  const delDia = (schedule.data ?? []).filter((o) => o.date === selected);
  const conClases = new Set((schedule.data ?? []).map((o) => o.date));

  return (
    <>
      <PageHeader title="Clases" subtitle={user.box?.name} />

      {/* Semana: 7 días sin scroll horizontal */}
      <nav aria-label="Día" className="mb-6 grid grid-cols-7 gap-1.5">
        {dias.map((iso) => {
          const d = parseApiDate(iso);
          const activo = iso === selected;
          return (
            <button
              key={iso}
              type="button"
              aria-pressed={activo}
              aria-label={d.toLocaleDateString("es", { weekday: "long", day: "numeric" })}
              onClick={() => setSelected(iso)}
              className={cx(
                "press flex min-h-touch-lg flex-col items-center justify-center rounded-2xl",
                activo ? "bg-fg text-ink" : "bg-surface text-fg",
              )}
            >
              <span className={cx("text-[11px] font-semibold", activo ? "text-ink/70" : "text-muted")}>
                {WEEKDAY_INITIALS[(d.getDay() + 6) % 7]}
              </span>
              <span className="num text-lg font-extrabold">{d.getDate()}</span>
              <span
                aria-hidden
                className={cx("mt-0.5 h-1 w-1 rounded-full", conClases.has(iso) ? (activo ? "bg-ink" : "bg-muted") : "bg-transparent")}
              />
            </button>
          );
        })}
      </nav>

      {schedule.isPending && (
        <div className="space-y-4" aria-busy="true" aria-label="Cargando clases">
          {[0, 1].map((i) => (
            <div key={i} className="space-y-3 rounded-3xl bg-surface p-5">
              <div className="flex gap-4">
                <Skeleton className="h-8 w-16" />
                <div className="grow space-y-2">
                  <Skeleton className="h-5 w-40" />
                  <Skeleton className="h-4 w-28" />
                </div>
              </div>
              <Skeleton className="h-4 w-full" />
            </div>
          ))}
        </div>
      )}
      {schedule.error && <ErrorState error={schedule.error} onRetry={() => void schedule.refetch()} />}

      {schedule.data && delDia.length === 0 && (
        <EmptyState title={selected === hoy ? "Hoy no hay clases" : "No hay clases este día"}>
          {esDueno ? "Crea las clases del box en Horarios, más abajo." : "Revisa otro día de la semana."}
        </EmptyState>
      )}

      <div className="space-y-4">
        {delDia.map((o) => (
          <ClassCard key={`${o.class_id}-${o.date}`} occurrence={o} role={user.role} onFeedback={notify} />
        ))}
      </div>

      {puedeProgramar && <ClassesAdmin isOwner={esDueno} onFeedback={notify} />}

      {toast && <Toast message={toast.message} tone={toast.tone} onDismiss={() => setToast(null)} />}
    </>
  );
}

// ------------------------------------------------ horarios (dueño/profesor)

function ClassesAdmin({ isOwner, onFeedback }: { isOwner: boolean; onFeedback: (m: string, t?: "done" | "danger") => void }) {
  const classes = useClasses();
  const [editing, setEditing] = useState<BoxClass | "new" | null>(null);
  const [programming, setProgramming] = useState<BoxClass | null>(null);
  const mias = (classes.data ?? []).filter((c) => isOwner || c.can_program);

  return (
    <section className="mt-10">
      <div className="mb-3 flex items-center justify-between">
        <h2 className="label-caps">{isOwner ? "Horarios del box" : "Mis clases"}</h2>
        {isOwner && (
          <button
            type="button"
            onClick={() => setEditing("new")}
            className="press flex min-h-touch items-center rounded-xl px-3 text-sm font-semibold text-brand"
          >
            + Clase
          </button>
        )}
      </div>

      {classes.data && mias.length === 0 && (
        <EmptyState title={isOwner ? "Todavía no hay clases" : "No tienes clases asignadas"}>
          {isOwner ? "Crea la primera clase y asígnale un profesor." : "El dueño del box te asigna las clases que dictas."}
        </EmptyState>
      )}

      <div className="space-y-2">
        {mias.map((c) => (
          <div key={c.id} className="rounded-2xl bg-surface p-4">
            <div className="flex items-start justify-between gap-3">
              <div className="min-w-0">
                <p className="font-bold">{c.name}</p>
                <p className="mt-0.5 text-sm text-muted">
                  <span className="num">{formatClassTime(c.start_time)}</span> ·{" "}
                  {c.weekdays.map((d) => WEEKDAY_INITIALS[d]).join(" ")} · {c.coach_name ?? "sin profesor"}
                </p>
              </div>
              {isOwner && (
                <button
                  type="button"
                  onClick={() => setEditing(c)}
                  className="press min-h-touch shrink-0 rounded-xl px-3 text-sm font-semibold text-muted active:text-fg"
                >
                  Editar
                </button>
              )}
            </div>
            {c.can_program && (
              <button
                type="button"
                onClick={() => setProgramming(c)}
                className="press mt-3 flex min-h-touch w-full items-center justify-between rounded-xl bg-surface-2 px-4 text-sm font-semibold"
              >
                Programar por semanas
                <IconChevronRight className="h-5 w-5" />
              </button>
            )}
          </div>
        ))}
      </div>

      {editing && (
        <ClassSheet
          initial={editing === "new" ? null : editing}
          onClose={() => setEditing(null)}
          onFeedback={onFeedback}
        />
      )}
      {programming && (
        <ProgramSheet boxClass={programming} onClose={() => setProgramming(null)} onFeedback={onFeedback} />
      )}
    </section>
  );
}

function ClassSheet({
  initial,
  onClose,
  onFeedback,
}: {
  initial: BoxClass | null;
  onClose: () => void;
  onFeedback: (m: string, t?: "done" | "danger") => void;
}) {
  const me = useCurrentUser();
  const members = useBoxMembers();
  const save = useSaveClass();
  const deactivate = useDeactivateClass();

  const [name, setName] = useState(initial?.name ?? "");
  const [description, setDescription] = useState(initial?.description ?? "");
  const [coachId, setCoachId] = useState(initial?.coach_id ?? "");
  const [weekdays, setWeekdays] = useState<Weekday[]>((initial?.weekdays ?? [0, 1, 2, 3, 4]) as Weekday[]);
  const [time, setTime] = useState(initial?.start_time ?? "06:00");
  const [duration, setDuration] = useState(String(initial?.duration_minutes ?? 60));
  const [error, setError] = useState<string | null>(null);

  const profesores = (members.data ?? []).filter((m) => m.role === "coach" || m.role === "owner");

  function submit(event: React.FormEvent) {
    event.preventDefault();
    setError(null);
    if (weekdays.length === 0) return setError("Elige al menos un día.");
    save.mutate(
      {
        id: initial?.id,
        body: {
          name: name.trim(),
          description: description.trim() || null,
          coach_id: coachId || null,
          clear_coach: Boolean(initial) && !coachId,
          weekdays,
          start_time: time,
          duration_minutes: Number(duration) || 60,
        },
      },
      {
        onSuccess: () => {
          onFeedback(initial ? "Clase actualizada." : "Clase creada.");
          onClose();
        },
        onError: (err) => setError(err instanceof Error ? err.message : "No se pudo guardar."),
      },
    );
  }

  return (
    <Sheet open onClose={onClose} title={initial ? "Editar clase" : "Nueva clase"}>
      <form onSubmit={submit} className="space-y-4 pb-4">
        <Field label="Nombre" placeholder="Ej. CrossFit" required maxLength={100} value={name} onChange={(e) => setName(e.target.value)} />
        <label className="block">
          <span className="mb-1.5 block text-sm font-medium text-muted">Profesor</span>
          <select
            value={coachId}
            onChange={(e) => setCoachId(e.target.value)}
            className="min-h-touch w-full rounded-xl bg-surface-2 px-3.5 text-fg"
          >
            <option value="">Sin asignar</option>
            {profesores.map((p) => (
              <option key={p.id} value={p.id}>
                {p.full_name}
                {p.id === me.id ? " (tú)" : ""}
              </option>
            ))}
          </select>
        </label>
        <div>
          <p className="mb-1.5 text-sm font-medium text-muted">Días</p>
          <WeekdayPicker value={weekdays} onChange={setWeekdays} />
        </div>
        <div className="grid grid-cols-2 gap-3">
          <Field label="Hora" type="time" required value={time} onChange={(e) => setTime(e.target.value)} />
          <Field
            label="Duración (min)"
            type="number"
            inputMode="numeric"
            min={15}
            max={240}
            step={5}
            value={duration}
            onChange={(e) => setDuration(e.target.value)}
          />
        </div>
        <label className="block">
          <span className="mb-1.5 block text-sm font-medium text-muted">Descripción (opcional)</span>
          <textarea
            rows={2}
            maxLength={1000}
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="Ej. Fuerza + metcon, todos los niveles"
            className="w-full rounded-xl bg-surface-2 px-3.5 py-3 text-fg placeholder:text-muted/60"
          />
        </label>
        {error && <p className="text-sm font-medium text-danger">{error}</p>}
        <button
          type="submit"
          disabled={save.isPending}
          className="press flex h-touch-lg w-full items-center justify-center rounded-2xl bg-brand text-lg font-bold text-on-brand disabled:opacity-60"
        >
          {initial ? "Guardar cambios" : "Crear clase"}
        </button>
        {initial && (
          <button
            type="button"
            disabled={deactivate.isPending}
            onClick={() => {
              if (!window.confirm(`"${initial.name}" saldrá del horario. Lo ya programado y registrado se conserva. ¿Continuar?`)) return;
              deactivate.mutate(initial.id, {
                onSuccess: (res) => {
                  onFeedback(res.message);
                  onClose();
                },
              });
            }}
            className="press min-h-touch w-full rounded-2xl text-sm font-semibold text-danger"
          >
            Quitar del horario
          </button>
        )}
      </form>
    </Sheet>
  );
}

/** Programar la clase "como un mesociclo": varias semanas de golpe. */
function ProgramSheet({
  boxClass,
  onClose,
  onFeedback,
}: {
  boxClass: BoxClass;
  onClose: () => void;
  onFeedback: (m: string, t?: "done" | "danger") => void;
}) {
  const create = useCreateClassProgram();
  const [name, setName] = useState("");
  const [start, setStart] = useState(todayIso());
  const [weeks, setWeeks] = useState("4");
  const [error, setError] = useState<string | null>(null);
  const dias = boxClass.weekdays.map((d) => WEEKDAY_NAMES[d as Weekday].toLowerCase()).join(", ");

  function submit(event: React.FormEvent) {
    event.preventDefault();
    setError(null);
    create.mutate(
      { classId: boxClass.id, name: name.trim(), start_date: start, weeks_count: Number(weeks) || 1 },
      {
        onSuccess: (res) => {
          const saltadas = res.skipped_dates.length ? ` (${res.skipped_dates.length} fecha(s) ya tenían contenido)` : "";
          onFeedback(`Bloque creado: ${res.sessions_count} clases listas para programar${saltadas}.`);
          onClose();
        },
        onError: (err) => setError(err instanceof ApiError ? err.message : "No se pudo crear el bloque."),
      },
    );
  }

  return (
    <Sheet open onClose={onClose} title={`Programar ${boxClass.name}`}>
      <form onSubmit={submit} className="space-y-4 pb-4">
        <p className="text-sm text-muted">
          Crea una clase por cada {dias} del bloque, lista para que le cargues ejercicios. Para programar un solo día, usa
          "Programar este día" en el horario.
        </p>
        <Field label="Nombre del bloque" placeholder="Ej. Fuerza · octubre" required maxLength={100} value={name} onChange={(e) => setName(e.target.value)} />
        <div className="grid grid-cols-2 gap-3">
          <Field label="Desde" type="date" required value={start} onChange={(e) => setStart(e.target.value)} />
          <Field label="Semanas" type="number" inputMode="numeric" min={1} max={16} value={weeks} onChange={(e) => setWeeks(e.target.value)} />
        </div>
        {error && <p className="text-sm font-medium text-danger">{error}</p>}
        <button
          type="submit"
          disabled={create.isPending}
          className="press flex h-touch-lg w-full items-center justify-center rounded-2xl bg-brand text-lg font-bold text-on-brand disabled:opacity-60"
        >
          Crear bloque
        </button>
      </form>
    </Sheet>
  );
}
