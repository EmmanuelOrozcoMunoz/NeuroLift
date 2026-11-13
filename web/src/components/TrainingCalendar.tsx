import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";

import { IconBack, IconChevronRight } from "@/components/icons";
import { cx } from "@/components/ui";
import { monthGrid, monthLabel, todayIso } from "@/lib/dates";
import type { TrainingSession } from "@/lib/types";

/** Lo único que el calendario necesita de una sesión (así también sirve para mostrar un grupo). */
export type CalendarSession = Pick<TrainingSession, "id" | "mesocycle_id" | "scheduled_date" | "status">;

const WEEKDAY_LABELS = ["L", "M", "X", "J", "V", "S", "D"];

/**
 * Vista de calendario mensual de las sesiones de entrenamiento, como alternativa a la lista
 * agrupada por semana de `MesocycleDetail.tsx`. Un punto bajo el día indica que hay sesión
 * programada; verde si ya se completó (mismo color que el resto de la app usa para "Hecho"),
 * violeta si todavía está pendiente. El círculo violeta marca el día de hoy.
 */
export function TrainingCalendar({
  sessions,
  onEmptyDayTap,
  onDayTap,
  onVisibleRangeChange,
}: {
  sessions: CalendarSession[];
  /** Si se pasa, tocar CUALQUIER día del mes (con sesión o sin ella) llama aquí en vez de abrir la sesión. */
  onDayTap?: (iso: string) => void;
  /** Si se pasa, un día del mes actual sin sesión también se puede tocar (para que el atleta
   *  agregue ahí su propia rutina manual) en vez de quedar inerte. */
  onEmptyDayTap?: (iso: string) => void;
  /** Se llama al montar y cada vez que cambia el mes visible, con el primer y el último día que se ven
   *  (incluidos los de las semanas vecinas): sirve para pedir al servidor solo ese rango. */
  onVisibleRangeChange?: (desde: string, hasta: string) => void;
}) {
  const navigate = useNavigate();
  const today = todayIso();
  const now = new Date();
  const [cursor, setCursor] = useState({ year: now.getFullYear(), month: now.getMonth() });

  const byDate = useMemo(() => {
    const map = new Map<string, CalendarSession[]>();
    for (const session of sessions) {
      const list = map.get(session.scheduled_date) ?? [];
      list.push(session);
      map.set(session.scheduled_date, list);
    }
    return map;
  }, [sessions]);

  const cells = useMemo(() => monthGrid(cursor.year, cursor.month), [cursor]);

  useEffect(() => {
    if (cells.length > 0) onVisibleRangeChange?.(cells[0].iso, cells[cells.length - 1].iso);
    // solo cuando cambia el mes: el callback puede cambiar de identidad en cada render sin que importe
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [cells]);

  function goToMonth(delta: number) {
    setCursor((prev) => {
      const date = new Date(prev.year, prev.month + delta, 1);
      return { year: date.getFullYear(), month: date.getMonth() };
    });
  }

  function handleSelectDay(daySessions: CalendarSession[]) {
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
          className="flex h-11 w-11 items-center justify-center rounded-full text-muted active:bg-surface-2"
        >
          <IconBack className="h-5 w-5" />
        </button>
        <p className="font-bold">{monthLabel(cursor.year, cursor.month)}</p>
        <button
          type="button"
          onClick={() => goToMonth(1)}
          aria-label="Mes siguiente"
          className="flex h-11 w-11 items-center justify-center rounded-full text-muted active:bg-surface-2"
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
          const tocable = onDayTap ? inMonth || hasSession : hasSession || canTapEmpty;

          return (
            <button
              key={iso}
              type="button"
              disabled={!tocable}
              onClick={() => {
                if (onDayTap) onDayTap(iso);
                else if (hasSession) handleSelectDay(daySessions);
                else onEmptyDayTap?.(iso);
              }}
              className="flex flex-col items-center gap-1 py-0.5"
            >
              <span
                className={cx(
                  "flex h-9 w-9 items-center justify-center rounded-full text-sm font-semibold transition-colors",
                  !inMonth && "text-muted/60",
                  inMonth && !isToday && "text-fg",
                  isToday && "bg-brand text-on-brand",
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
