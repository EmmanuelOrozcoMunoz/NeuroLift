import { Link } from "react-router-dom";

import { PageHeader } from "@/components/AppShell";
import { IconTrophy, IconUser } from "@/components/icons";
import { Badge, EmptyState, ErrorState, LoadingList } from "@/components/ui";
import { useAthleteLeaderboard } from "@/lib/coachQueries";
import { relativeDay } from "@/lib/dates";
import { useAvatarUrl } from "@/lib/useAvatarUrl";
import type { AthleteActivity } from "@/lib/types";

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

/** "Tabla de posiciones" del coach: quiénes de sus atletas completaron entrenamientos (con sus
 *  reps/pesos reales) y cuándo — visibilidad que antes solo existía entrando mesociclo por
 *  mesociclo a cada atleta uno por uno. */
export default function Leaderboard() {
  const { data, isPending, error, refetch } = useAthleteLeaderboard();

  return (
    <>
      <PageHeader title="Actividad" subtitle="Quién ha completado sus entrenamientos" />

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
  );
}
