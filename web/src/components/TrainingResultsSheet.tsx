import { IconUser } from "@/components/icons";
import { Badge, Button, ErrorState, LoadingList, Sheet } from "@/components/ui";
import { useTrainingResults } from "@/lib/coachQueries";
import { formatSeconds, longDate } from "@/lib/dates";
import { useAvatarUrl } from "@/lib/useAvatarUrl";
import { WOD_FORMAT_LABELS } from "@/lib/wod";
import type { TrainingResultRow } from "@/lib/types";

const MEDALLAS = ["🥇", "🥈", "🥉"];

function capitalizar(texto: string): string {
  return texto.charAt(0).toUpperCase() + texto.slice(1);
}

function FilaDeResultado({ fila }: { fila: TrainingResultRow }) {
  const avatarUrl = useAvatarUrl(fila.user_id, fila.has_avatar);
  const iniciales = fila.full_name
    .split(" ")
    .slice(0, 2)
    .map((parte) => parte[0]?.toUpperCase())
    .join("");

  return (
    <div className="flex items-center gap-3 rounded-2xl border border-line bg-surface p-3">
      <div className="flex w-6 shrink-0 items-center justify-center text-base font-bold text-muted">
        {fila.rank ? (MEDALLAS[fila.rank - 1] ?? fila.rank) : "—"}
      </div>
      <div className="flex h-10 w-10 shrink-0 items-center justify-center overflow-hidden rounded-full bg-brand-soft text-brand">
        {avatarUrl ? (
          <img src={avatarUrl} alt="" className="h-full w-full object-cover" />
        ) : iniciales ? (
          <span className="text-sm font-bold">{iniciales}</span>
        ) : (
          <IconUser className="h-5 w-5" />
        )}
      </div>
      <div className="min-w-0 grow">
        <p className="truncate font-bold">{fila.full_name}</p>
        {fila.score_label && <p className="truncate text-xs font-semibold text-brand">{fila.score_label}</p>}
        {fila.sets_total > 0 && fila.completed && (
          <p className="truncate text-xs text-muted">
            {fila.sets_logged} de {fila.sets_total} series anotadas
          </p>
        )}
      </div>
      <div className="shrink-0 whitespace-nowrap">
        <Badge tone={fila.completed ? "done" : "warn"}>{fila.completed ? "Terminó" : "Pendiente"}</Badge>
      </div>
    </div>
  );
}

/** Cómo quedó un entreno entre sus miembros. Con un WOD que tiene formato (tiempo, rondas, carga...) es el
 *  RANKING por su resultado, mejor primero; sin WOD, quién lo terminó y quién falta (en una sesión de fuerza nadie
 *  "gana" por terminarla antes, así que no hay posiciones). Es lo que antes vivía en la pantalla Actividad. */
export function TrainingResultsSheet({
  sessionId,
  onClose,
  onEdit,
}: {
  sessionId: string | null;
  onClose: () => void;
  onEdit: () => void;
}) {
  const resultados = useTrainingResults(sessionId);
  const datos = resultados.data;
  const conRanking = Boolean(datos?.wod_format);

  return (
    <Sheet
      open={sessionId !== null}
      onClose={onClose}
      title={datos?.title ?? "Resultados"}
    >
      <div className="space-y-3 pb-4">
        {resultados.isPending && <LoadingList rows={3} />}
        {resultados.error && <ErrorState error={resultados.error} onRetry={() => void resultados.refetch()} />}

        {datos && (
          <>
            <p className="text-sm font-semibold">{capitalizar(longDate(datos.date))}</p>
            <p className="text-sm text-muted">
              {datos.kind === "group"
                ? `${datos.completed} de ${datos.total} ${datos.total === 1 ? "miembro lo terminó" : "miembros lo terminaron"}`
                : datos.completed > 0
                  ? "Lo terminó"
                  : "Todavía no lo termina"}
            </p>

            <p className="text-xs font-semibold tracking-wide text-muted uppercase">
              {conRanking
                ? `🏆 Leaderboard · ${datos.wod_format ? WOD_FORMAT_LABELS[datos.wod_format] : ""}${datos.wod_name ? ` · ${datos.wod_name}` : ""}${datos.time_cap_seconds ? ` · cap ${formatSeconds(datos.time_cap_seconds)}` : ""}`
                : datos.kind === "group"
                  ? "Quién lo terminó"
                  : "Resultado"}
            </p>

            <div className="space-y-2">
              {datos.rows.map((fila) => (
                <FilaDeResultado key={fila.user_id} fila={fila} />
              ))}
            </div>
          </>
        )}

        <Button full variant="secondary" onClick={onEdit}>
          Editar este día
        </Button>
      </div>
    </Sheet>
  );
}
