import { Link } from "react-router-dom";

import { IconCheck, IconChevronRight, IconClock } from "@/components/icons";
import { Badge, cx } from "@/components/ui";
import { relativeDay, shortDate } from "@/lib/dates";
import { groupSets, sessionProgress } from "@/lib/sessions";
import type { TrainingSession } from "@/lib/types";

export function SessionCard({
  session,
  mesocycleId,
  adapted,
  highlight = false,
}: {
  session: TrainingSession;
  mesocycleId: string;
  /** Versión corta de esta sesión, si el atleta ya pidió una. */
  adapted?: TrainingSession;
  highlight?: boolean;
}) {
  const completed = session.status === "completed";
  const { logged, total } = sessionProgress(session);
  const started = logged > 0 && !completed;
  const groups = groupSets(session.sets);
  const nombres = groups.map((group) => group.name);

  return (
    <Link
      to={`/entrenos/${mesocycleId}/sesion/${session.id}`}
      className={cx(
        "block rounded-2xl border p-4 transition-colors active:bg-surface-2",
        highlight ? "border-brand/50 bg-brand-soft/40" : "border-line bg-surface",
      )}
    >
      <div className="flex items-start gap-3">
        <div className="min-w-0 grow">
          <div className="flex flex-wrap items-center gap-2">
            <span className="font-bold">{shortDate(session.scheduled_date)}</span>
            <span className="text-xs text-muted">{relativeDay(session.scheduled_date)}</span>
            {completed && (
              <Badge tone="done">
                <span className="inline-flex items-center gap-1">
                  <IconCheck className="h-3 w-3" /> Hecho
                </span>
              </Badge>
            )}
            {started && <Badge tone="warn">{`${logged}/${total} series`}</Badge>}
          </div>

          <p className="mt-1.5 truncate text-sm text-muted">
            {nombres.length ? nombres.join(" · ") : "Sin ejercicios asignados"}
          </p>

          {adapted && (
            <p className="mt-2 inline-flex items-center gap-1.5 text-xs font-semibold text-brand">
              <IconClock className="h-3.5 w-3.5" />
              Tienes una versión de {adapted.duration_minutes ?? "?"} min
            </p>
          )}
        </div>

        <IconChevronRight className="mt-1 h-5 w-5 shrink-0 text-muted" />
      </div>

      {started && (
        <div className="mt-3 h-1.5 overflow-hidden rounded-full bg-surface-2">
          <div className="h-full rounded-full bg-warn" style={{ width: `${(logged / total) * 100}%` }} />
        </div>
      )}
    </Link>
  );
}
