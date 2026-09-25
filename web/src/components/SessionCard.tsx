import { Link } from "react-router-dom";

import { IconCheck, IconChevronRight, IconClock } from "@/components/icons";
import { cx } from "@/components/ui";
import { parseApiDate, relativeDay } from "@/lib/dates";
import { groupSets, sessionProgress } from "@/lib/sessions";
import type { TrainingSession } from "@/lib/types";

/**
 * Fila de una sesión en listas (Hoy, mesociclos, panel del coach). Sin borde: la separa su
 * superficie. La FECHA es la cifra protagonista (día del mes grande, día de la semana en
 * versalitas), para ubicar la sesión de un vistazo.
 */
export function SessionCard({
  session,
  mesocycleId,
  adapted,
  highlight = false,
  to,
}: {
  session: TrainingSession;
  mesocycleId: string;
  /** Versión corta de esta sesión, si el atleta ya pidió una. */
  adapted?: TrainingSession;
  highlight?: boolean;
  /** Override del destino — el panel de coach enlaza al editor, no al registro del atleta. */
  to?: string;
}) {
  const completed = session.status === "completed";
  const { logged, total } = sessionProgress(session);
  const started = logged > 0 && !completed;
  const nombres = groupSets(session.sets).map((group) => group.name);
  const date = parseApiDate(session.scheduled_date);
  const weekday = date.toLocaleDateString("es", { weekday: "short" }).replace(".", "");

  return (
    <Link
      to={to ?? `/entrenos/${mesocycleId}/sesion/${session.id}`}
      className={cx(
        "press flex min-h-touch items-center gap-4 rounded-2xl p-4",
        highlight ? "bg-surface-2" : "bg-surface active:bg-surface-2",
      )}
    >
      {/* Fecha como cifra */}
      <div className="flex w-11 shrink-0 flex-col items-center">
        <span className="label-caps">{weekday}</span>
        <span className={cx("num text-metric-sm", completed ? "text-muted" : "text-fg")}>{date.getDate()}</span>
      </div>

      <div className="min-w-0 grow">
        <p className="truncate font-semibold">{nombres.length ? nombres.join(" · ") : "Sin ejercicios asignados"}</p>
        <p className="mt-0.5 flex flex-wrap items-center gap-x-2 text-sm text-muted">
          <span>{relativeDay(session.scheduled_date)}</span>
          {completed && (
            <span className="inline-flex items-center gap-1 font-semibold text-done">
              <IconCheck className="h-3.5 w-3.5" /> Hecho
            </span>
          )}
          {started && (
            <span className="num font-semibold text-warn">
              {logged}/{total} series
            </span>
          )}
          {adapted && (
            <span className="inline-flex items-center gap-1">
              <IconClock className="h-3.5 w-3.5" /> versión de {adapted.duration_minutes ?? "?"} min
            </span>
          )}
        </p>
        {started && (
          <div className="mt-2 h-1 overflow-hidden rounded-full bg-surface-3" aria-hidden>
            <div className="h-full rounded-full bg-warn" style={{ width: `${(logged / total) * 100}%` }} />
          </div>
        )}
      </div>

      <IconChevronRight className="h-5 w-5 shrink-0 text-muted" />
    </Link>
  );
}
