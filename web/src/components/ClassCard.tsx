import { useNavigate } from "react-router-dom";

import { IconChevronRight, IconClock, IconUser } from "@/components/icons";
import { ApiError } from "@/lib/api";
import { useCreateClassDay } from "@/lib/classQueries";
import { formatSeconds } from "@/lib/dates";
import { gruposEnOrden } from "@/lib/sessions";
import { WOD_FORMAT_LABELS } from "@/lib/wod";
import type { ClassOccurrence } from "@/lib/types";

/** "06:00" -> "6:00 am" */
export function formatClassTime(hhmm: string): string {
  const [h, m] = hhmm.split(":").map(Number);
  const suffix = h < 12 ? "am" : "pm";
  const h12 = h % 12 === 0 ? 12 : h % 12;
  return `${h12}:${String(m).padStart(2, "0")} ${suffix}`;
}

/**
 * Una clase en un día: la HORA es la cifra protagonista, luego qué es, quién la dicta y de qué
 * se trata. Solo la ven los entrenadores del box; el profesor (o el dueño) la programa.
 */
export function ClassCard({
  occurrence: o,
  onFeedback,
}: {
  occurrence: ClassOccurrence;
  onFeedback: (message: string, tone?: "done" | "danger") => void;
}) {
  const navigate = useNavigate();
  const createDay = useCreateClassDay();

  const [time, suffix] = formatClassTime(o.start_time).split(" ");
  const grupos = o.session ? gruposEnOrden(o.session.sets, o.session.block_order) : [];

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
                <li key={`${g.name}-${i}`}>
                  <div className="flex items-baseline justify-between gap-3">
                    <span className="min-w-0 truncate">{g.name}</span>
                    <span className="num shrink-0 font-bold">
                      {g.sets.length}×{[...new Set(g.sets.map((s) => s.prescribed_reps))].join("/")}
                    </span>
                  </div>
                  {g.sets.some((s) => s.coach_note) && (
                    <p className="mt-0.5 line-clamp-2 text-xs text-muted">📝 {g.sets.find((s) => s.coach_note)?.coach_note}</p>
                  )}
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
