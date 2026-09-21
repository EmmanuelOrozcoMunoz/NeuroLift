import { useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";

import { IconBack, IconChevronRight } from "@/components/icons";
import { cx } from "@/components/ui";
import { monthGrid, monthLabel, todayIso } from "@/lib/dates";
import type { TrainingSession } from "@/lib/types";

const WEEKDAY_LABELS = ["L", "M", "X", "J", "V", "S", "D"];

/**
 * Vista de calendario mensual de las sesiones de entrenamiento, como alternativa a la lista
 * agrupada por semana de `MesocycleDetail.tsx`. Un punto bajo el día indica que hay sesión
 * programada; lima si ya se completó (mismo color que el resto de la app usa para "Hecho"),
 * violeta si todavía está pendiente. El círculo violeta marca el día de hoy.
 */
export function TrainingCalendar({
  sessions,
  onEmptyDayTap,
}: {
  sessions: TrainingSession[];
  /** Si se pasa, un día del mes actual sin sesión también se puede tocar (para que el atleta
   *  agregue ahí su propia rutina manual) en vez de quedar inerte. */
  onEmptyDayTap?: (iso: string) => void;
}) {
  const navigate = useNavigate();
  const today = todayIso();
  const now = new Date();
  const [cursor, setCursor] = useState({ year: now.getFullYear(), month: now.getMonth() });

  const byDate = useMemo(() => {
    const map = new Map<string, TrainingSession[]>();
    for (const session of sessions) {
      const list = map.get(session.scheduled_date) ?? [];
      list.push(session);
      map.set(session.scheduled_date, list);
    }
    return map;
  }, [sessions]);

  const cells = useMemo(() => monthGrid(cursor.year, cursor.month), [cursor]);

  function goToMonth(delta: number) {
    setCursor((prev) => {
      const date = new Date(prev.year, prev.month + delta, 1);
      return { year: date.getFullYear(), month: date.getMonth() };
    });
  }

  function handleSelectDay(daySessions: TrainingSession[]) {
    if (daySessions.length === 0) return;
    const session = daySessions[0];
    navigate(`/entrenos/${session.mesocycle_id}/sesion/${session.id}`);
  }

  return (
    <div className="rounded-2xl border border-line bg-surface p-4">
      <div className="mb-4 flex items-center justify-between">
        <button
          type="button"
          onClick={() => goToMonth(-1)}
          aria-label="Mes anterior"
          className="rounded-full p-2 text-muted active:bg-surface-2"
        >
          <IconBack className="h-5 w-5" />
        </button>
        <p className="font-bold">{monthLabel(cursor.year, cursor.month)}</p>
        <button
          type="button"
          onClick={() => goToMonth(1)}
          aria-label="Mes siguiente"
          className="rounded-full p-2 text-muted active:bg-surface-2"
        >
          <IconChevronRight className="h-5 w-5" />
        </button>
      </div>

      <div className="grid grid-cols-7 gap-y-2 text-center">
        {WEEKDAY_LABELS.map((label, index) => (
          <span key={index} className="text-xs font-semibold text-muted">
            {label}
          </span>
        ))}

        {cells.map(({ iso, inMonth }) => {
          const daySessions = byDate.get(iso) ?? [];
          const isToday = iso === today;
          const hasCompleted = daySessions.some((s) => s.status === "completed");
          const hasSession = daySessions.length > 0;
          const canTapEmpty = !hasSession && inMonth && Boolean(onEmptyDayTap);

          return (
            <button
              key={iso}
              type="button"
              disabled={!hasSession && !canTapEmpty}
              onClick={() => (hasSession ? handleSelectDay(daySessions) : onEmptyDayTap?.(iso))}
              className="flex flex-col items-center gap-1 py-0.5"
            >
              <span
                className={cx(
                  "flex h-9 w-9 items-center justify-center rounded-full text-sm font-semibold transition-colors",
                  !inMonth && "text-muted/30",
                  inMonth && !isToday && "text-fg",
                  isToday && "bg-brand text-white",
                )}
              >
                {Number(iso.slice(-2))}
              </span>
              <span
                className={cx(
                  "h-1.5 w-1.5 rounded-full",
                  hasSession && hasCompleted && "bg-done",
                  hasSession && !hasCompleted && "bg-brand",
                  !hasSession && "bg-transparent",
                )}
              />
            </button>
          );
        })}
      </div>
    </div>
  );
}
