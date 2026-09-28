import { useNavigate } from "react-router-dom";

import { IconCheck, IconChevronRight, IconClock, IconUser } from "@/components/icons";
import { cx } from "@/components/ui";
import { ApiError } from "@/lib/api";
import { useCreateClassDay, useJoinClass } from "@/lib/classQueries";
import { daysFromToday, formatSeconds } from "@/lib/dates";
import { groupSets } from "@/lib/sessions";
import { WOD_FORMAT_LABELS } from "@/lib/wod";
import type { ClassOccurrence, Role } from "@/lib/types";

/** "06:00" -> "6:00 am" */
export function formatClassTime(hhmm: string): string {
  const [h, m] = hhmm.split(":").map(Number);
  const suffix = h < 12 ? "am" : "pm";
  const h12 = h % 12 === 0 ? 12 : h % 12;
  return `${h12}:${String(m).padStart(2, "0")} ${suffix}`;
}

/**
 * Una clase en un día: la HORA es la cifra protagonista, luego qué es, quién la dicta y de qué
 * se trata. Las acciones cambian según quién mira: el atleta la registra; su profesor (o el
 * dueño) la programa.
 */
export function ClassCard({
  occurrence: o,
  role,
  onFeedback,
}: {
  occurrence: ClassOccurrence;
  role: Role;
  onFeedback: (message: string, tone?: "done" | "danger") => void;
}) {
  const navigate = useNavigate();
  const join = useJoinClass();
  const createDay = useCreateClassDay();

  const [time, suffix] = formatClassTime(o.start_time).split(" ");
  const grupos = o.session ? groupSets(o.session.sets) : [];
  const esFutura = daysFromToday(o.date) > 0;
  const registrada = Boolean(o.my_session_id);
  const completada = o.my_status === "completed";
  const esAtleta = role === "athlete";

  function registrar() {
    if (!o.session) return;
    if (o.my_session_id && o.my_mesocycle_id) {
      navigate(`/entrenos/${o.my_mesocycle_id}/sesion/${o.my_session_id}`);
      return;
    }
    join.mutate(o.session.id, {
      onSuccess: (res) => {
        if (res.missing_prs.length) {
          onFeedback(`Sin marca de ${res.missing_prs.join(", ")}: ajusta esos pesos a mano.`);
        }
        navigate(`/entrenos/${res.mesocycle_id}/sesion/${res.session_id}`);
      },
      onError: (err) => onFeedback(err instanceof ApiError ? err.message : "No se pudo registrar la clase.", "danger"),
    });
  }

  function programar() {
    createDay.mutate(
      { classId: o.class_id, date: o.date },
      {
        onSuccess: (res) => navigate(`/coach/mesociclos/${res.mesocycle_id}/sesion/${res.session_id}`),
        onError: (err) => onFeedback(err instanceof ApiError ? err.message : "No se pudo abrir la programación.", "danger"),
      },
    );
  }

  return (
    <article className="rounded-3xl bg-surface p-5">
      <div className="flex items-start gap-4">
        <div className="w-16 shrink-0">
          <p className="num text-metric-sm">{time}</p>
          <p className="label-caps mt-1">{suffix}</p>
        </div>
        <div className="min-w-0 grow">
          <div className="flex items-start justify-between gap-2">
            <h3 className="text-lg leading-tight font-extrabold tracking-tight">{o.class_name}</h3>
            {esAtleta && completada && (
              <span className="inline-flex shrink-0 items-center gap-1 rounded-full bg-done-soft px-2.5 py-1 text-xs font-semibold text-done">
                <IconCheck className="h-3.5 w-3.5" /> Hecha
              </span>
            )}
          </div>
          <p className="mt-1 flex flex-wrap items-center gap-x-3 gap-y-1 text-sm text-muted">
            <span className="inline-flex items-center gap-1">
              <IconUser className="h-4 w-4" aria-hidden />
              {o.coach_name ?? "Sin profesor asignado"}
            </span>
            <span className="inline-flex items-center gap-1">
              <IconClock className="h-4 w-4" aria-hidden />
              <span className="num">{o.duration_minutes}</span> min
            </span>
          </p>
        </div>
      </div>

      {/* De qué se trata */}
      {o.session ? (
        <div className="mt-4 space-y-2">
          {o.session.wod_format && (
            <p className="inline-flex items-center gap-2 rounded-full bg-surface-2 px-3 py-1 text-sm font-semibold">
              WOD · {WOD_FORMAT_LABELS[o.session.wod_format]}
              {o.session.wod_time_cap_seconds ? (
                <span className="num text-muted">{formatSeconds(o.session.wod_time_cap_seconds)}</span>
              ) : null}
            </p>
          )}
          {grupos.length > 0 && (
            <ul className="space-y-1">
              {grupos.map((g, i) => (
                <li key={`${g.name}-${i}`} className="flex items-baseline justify-between gap-3">
                  <span className="min-w-0 truncate">{g.name}</span>
                  <span className="num shrink-0 font-bold">
                    {g.sets.length}×{[...new Set(g.sets.map((s) => s.prescribed_reps))].join("/")}
                  </span>
                </li>
              ))}
            </ul>
          )}
          {o.session.wod_notes && <p className="text-sm whitespace-pre-line text-muted">{o.session.wod_notes}</p>}
          {grupos.length === 0 && !o.session.wod_notes && !o.session.wod_format && (
            <p className="text-sm text-muted">El profesor está preparando el contenido.</p>
          )}
        </div>
      ) : (
        <p className="mt-4 text-sm text-muted">
          {o.description ? o.description : "El profesor todavía no publica el contenido de esta clase."}
        </p>
      )}

      {/* Acciones */}
      {esAtleta && o.session && !esFutura && (
        <button
          type="button"
          onClick={registrar}
          disabled={join.isPending}
          className={cx(
            "press mt-5 flex h-touch-lg w-full items-center justify-center gap-2 rounded-2xl text-lg font-bold disabled:opacity-60",
            registrada ? "bg-surface-2 text-fg" : "bg-brand text-on-brand",
          )}
        >
          {completada ? "Ver mi registro" : registrada ? "Continuar registro" : "Registrar mi clase"}
          <IconChevronRight className="h-5 w-5" />
        </button>
      )}
      {esAtleta && o.session && esFutura && (
        <p className="mt-4 text-xs text-muted">Podrás registrarla el día de la clase.</p>
      )}

      {o.can_program && (
        <button
          type="button"
          onClick={programar}
          disabled={createDay.isPending}
          className="press mt-4 flex min-h-touch w-full items-center justify-center gap-2 rounded-2xl bg-surface-2 font-semibold disabled:opacity-60"
        >
          {o.session ? "Editar contenido" : "Programar este día"}
          <IconChevronRight className="h-5 w-5" />
        </button>
      )}
    </article>
  );
}
