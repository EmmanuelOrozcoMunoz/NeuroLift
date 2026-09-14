import { useState } from "react";
import { Link } from "react-router-dom";

import { PageHeader } from "@/components/AppShell";
import { IconChevronRight, IconTrophy, IconUser } from "@/components/icons";
import { Badge, EmptyState, ErrorState, LoadingList, Segmented } from "@/components/ui";
import {
  useAthleteLeaderboard,
  useGroupWodDays,
  useGroupWodLeaderboard,
  useGroups,
} from "@/lib/coachQueries";
import { relativeDay, shortDate } from "@/lib/dates";
import { useAvatarUrl } from "@/lib/useAvatarUrl";
import { WOD_FORMAT_LABELS } from "@/lib/wod";
import type { AthleteActivity, WodDaySummary, WodLeaderboardRow } from "@/lib/types";

const MEDALLAS = ["🥇", "🥈", "🥉"];

function AthleteRow({ athlete, posicion }: { athlete: AthleteActivity; posicion: number }) {
  const avatarUrl = useAvatarUrl(athlete.user_id, athlete.has_avatar);
  const initials = athlete.full_name
    .split(" ")
    .slice(0, 2)
    .map((part) => part[0]?.toUpperCase())
    .join("");

  return (
    <Link
      to={`/coach/atletas/${athlete.user_id}`}
      className="flex items-center gap-3 rounded-2xl border border-line bg-surface p-3 active:bg-surface-2"
    >
      <div className="flex w-6 shrink-0 items-center justify-center text-base font-bold text-muted">
        {MEDALLAS[posicion] ?? posicion + 1}
      </div>
      <div className="flex h-11 w-11 shrink-0 items-center justify-center overflow-hidden rounded-full bg-brand-soft text-brand">
        {avatarUrl ? (
          <img src={avatarUrl} alt="" className="h-full w-full object-cover" />
        ) : initials ? (
          <span className="text-sm font-bold">{initials}</span>
        ) : (
          <IconUser className="h-5 w-5" />
        )}
      </div>
      <div className="min-w-0 grow">
        <p className="truncate font-bold">{athlete.full_name}</p>
        <p className="truncate text-xs text-muted">
          {athlete.completed_total} completado{athlete.completed_total === 1 ? "" : "s"} en total
          {athlete.last_completed_at && ` · último ${relativeDay(athlete.last_completed_at.split("T")[0])}`}
        </p>
        {athlete.last_wod_summary && (
          <p className="truncate text-xs font-semibold text-brand">{athlete.last_wod_summary}</p>
        )}
      </div>
      <div className="shrink-0 whitespace-nowrap">
        <Badge tone={athlete.completed_this_week > 0 ? "done" : "neutral"}>
          {athlete.completed_this_week} esta semana
        </Badge>
      </div>
    </Link>
  );
}

function WodRow({ row, posicion }: { row: WodLeaderboardRow; posicion: number }) {
  const avatarUrl = useAvatarUrl(row.user_id, row.has_avatar);
  const initials = row.full_name
    .split(" ")
    .slice(0, 2)
    .map((part) => part[0]?.toUpperCase())
    .join("");

  return (
    <div className="flex items-center gap-3 rounded-2xl border border-line bg-surface p-3">
      <div className="flex w-6 shrink-0 items-center justify-center text-base font-bold text-muted">
        {row.rank ? (MEDALLAS[posicion] ?? row.rank) : "—"}
      </div>
      <div className="flex h-11 w-11 shrink-0 items-center justify-center overflow-hidden rounded-full bg-brand-soft text-brand">
        {avatarUrl ? (
          <img src={avatarUrl} alt="" className="h-full w-full object-cover" />
        ) : initials ? (
          <span className="text-sm font-bold">{initials}</span>
        ) : (
          <IconUser className="h-5 w-5" />
        )}
      </div>
      <div className="min-w-0 grow">
        <p className="truncate font-bold">{row.full_name}</p>
        {row.score_label && <p className="truncate text-xs font-semibold text-brand">{row.score_label}</p>}
      </div>
      <div className="shrink-0 whitespace-nowrap">
        <Badge tone={row.completed ? (row.score_label ? "done" : "neutral") : "warn"}>
          {row.completed ? (row.score_label ? "Listo" : "Sin resultado") : "Pendiente"}
        </Badge>
      </div>
    </div>
  );
}

function WodDayRow({ day, onSelect }: { day: WodDaySummary; onSelect: () => void }) {
  return (
    <button
      type="button"
      onClick={onSelect}
      className="flex w-full items-center gap-3 rounded-2xl border border-line bg-surface p-4 text-left active:bg-surface-2"
    >
      <div className="min-w-0 grow">
        <p className="truncate font-bold">
          {shortDate(day.scheduled_date)}
          {day.wod_name && <span className="text-brand"> · {day.wod_name}</span>}
        </p>
        <p className="text-sm text-muted">
          {WOD_FORMAT_LABELS[day.wod_format]} · {day.participants_count} atleta(s)
        </p>
      </div>
      <IconChevronRight className="h-5 w-5 shrink-0 text-muted" />
    </button>
  );
}

/** Tab "Por WOD": el coach elige un grupo, luego una fecha con WOD prescrito, y ve a sus
 *  atletas rankeados por el resultado real de ESE WOD (menor tiempo, más rondas/reps/peso/
 *  calorías/distancia/vatios según el formato — ver _rank_wod_sessions en el backend). */
function PorWodTab() {
  const groups = useGroups();
  const [groupId, setGroupId] = useState<string | null>(null);
  const [selectedDay, setSelectedDay] = useState<WodDaySummary | null>(null);

  const wodDays = useGroupWodDays(groupId ?? undefined);
  const wodLeaderboard = useGroupWodLeaderboard(groupId ?? undefined, selectedDay?.scheduled_date);

  if (!groupId) {
    if (groups.isPending) return <LoadingList rows={3} />;
    if (groups.error) return <ErrorState error={groups.error} onRetry={() => void groups.refetch()} />;
    if ((groups.data?.length ?? 0) === 0) {
      return (
        <EmptyState icon={<IconTrophy className="h-10 w-10" />} title="Todavía no tienes grupos">
          El leaderboard por WOD compara atletas de un mismo grupo que hicieron el mismo entreno.
        </EmptyState>
      );
    }
    return (
      <div className="space-y-2">
        <p className="mb-1 text-sm text-muted">Elige un grupo</p>
        {groups.data?.map((group) => (
          <button
            key={group.id}
            type="button"
            onClick={() => setGroupId(group.id)}
            className="flex w-full items-center gap-3 rounded-2xl border border-line bg-surface p-4 text-left active:bg-surface-2"
          >
            <div className="min-w-0 grow">
              <p className="truncate font-bold">{group.name}</p>
              <p className="text-sm text-muted">{group.member_count} atleta(s)</p>
            </div>
            <IconChevronRight className="h-5 w-5 shrink-0 text-muted" />
          </button>
        ))}
      </div>
    );
  }

  if (!selectedDay) {
    return (
      <div className="space-y-2">
        <button
          type="button"
          onClick={() => setGroupId(null)}
          className="mb-1 text-sm font-semibold text-brand"
        >
          ← Cambiar grupo
        </button>
        {wodDays.isPending && <LoadingList rows={3} />}
        {!wodDays.isPending && wodDays.error && (
          <ErrorState error={wodDays.error} onRetry={() => void wodDays.refetch()} />
        )}
        {!wodDays.isPending && !wodDays.error && (wodDays.data?.length ?? 0) === 0 && (
          <EmptyState title="Este grupo todavía no tiene ningún WOD con formato asignado">
            Asígnalo desde el mesociclo del grupo, en la pestaña "Grupo completo" de una fecha.
          </EmptyState>
        )}
        {wodDays.data?.map((day) => (
          <WodDayRow
            key={`${day.scheduled_date}-${day.wod_format}`}
            day={day}
            onSelect={() => setSelectedDay(day)}
          />
        ))}
      </div>
    );
  }

  return (
    <div className="space-y-2">
      <button
        type="button"
        onClick={() => setSelectedDay(null)}
        className="mb-1 text-sm font-semibold text-brand"
      >
        ← Cambiar fecha
      </button>
      <p className="mb-2 text-sm text-muted">
        {shortDate(selectedDay.scheduled_date)}
        {selectedDay.wod_name && <span className="font-semibold text-brand"> · {selectedDay.wod_name}</span>}
      </p>
      {wodLeaderboard.isPending && <LoadingList rows={3} />}
      {!wodLeaderboard.isPending && wodLeaderboard.error && (
        <ErrorState error={wodLeaderboard.error} onRetry={() => void wodLeaderboard.refetch()} />
      )}
      {wodLeaderboard.data?.map((row, index) => (
        <WodRow key={row.user_id} row={row} posicion={index} />
      ))}
    </div>
  );
}

/** "Tabla de posiciones" del coach: quiénes de sus atletas completaron entrenamientos (con sus
 *  reps/pesos reales) y cuándo — visibilidad que antes solo existía entrando mesociclo por
 *  mesociclo a cada atleta uno por uno. La pestaña "Por WOD" compara resultados de un WOD
 *  específico entre los atletas de un grupo. */
export default function Leaderboard() {
  const { data, isPending, error, refetch } = useAthleteLeaderboard();
  const [tab, setTab] = useState<"general" | "wod">("general");

  return (
    <>
      <PageHeader title="Actividad" subtitle="Quién ha completado sus entrenamientos" />

      <div className="mb-4">
        <Segmented<"general" | "wod">
          value={tab}
          onChange={setTab}
          options={[
            { value: "general", label: "General" },
            { value: "wod", label: "Por WOD" },
          ]}
        />
      </div>

      {tab === "wod" ? (
        <PorWodTab />
      ) : (
        <>
          {isPending && <LoadingList rows={4} />}
          {!isPending && error && <ErrorState error={error} onRetry={() => void refetch()} />}

          {!isPending && !error && (data?.length ?? 0) === 0 && (
            <EmptyState icon={<IconTrophy className="h-10 w-10" />} title="Todavía no tienes atletas">
              Cuando tengas atletas y empiecen a completar sus entrenamientos, los verás aquí.
            </EmptyState>
          )}

          <div className="space-y-2">
            {data?.map((athlete, index) => (
              <AthleteRow key={athlete.user_id} athlete={athlete} posicion={index} />
            ))}
          </div>
        </>
      )}
    </>
  );
}
