import { useState } from "react";
import { Link } from "react-router-dom";

import { PageHeader } from "@/components/AppShell";
import { IconCheck, IconFilter, IconTrophy, IconUser } from "@/components/icons";
import { Badge, Button, EmptyState, ErrorState, LoadingList, Segmented, Sheet, cx } from "@/components/ui";
import { useCurrentUser } from "@/lib/auth";
import { useGroups } from "@/lib/coachQueries";
import { shortDate } from "@/lib/dates";
import { equipoDe } from "@/lib/equipo";
import { nombreCorto, soloElResultado } from "@/lib/rankingFormat";
import { useRankingLift, useRankingLifts, useRankingWod, useRankingWods } from "@/lib/rankingQueries";
import type { FiltrosRanking } from "@/lib/rankingQueries";
import { formatWeight, useWeightUnit } from "@/lib/units";
import { useAvatarUrl } from "@/lib/useAvatarUrl";
import { WOD_FORMAT_LABELS } from "@/lib/wod";
import type { RankingLiftRow, RankingWodRow } from "@/lib/types";

type Sexo = "todos" | "female" | "male";

/** Lo que se elige arriba: un levantamiento (su clave) o los WODs. */
const WODS = "wods";

const MEDALLAS = ["🥇", "🥈", "🥉"];
const ETIQUETA_DE_SEXO: Record<Sexo, string> = { todos: "Todos", female: "Mujeres", male: "Hombres" };

/** Pantalla del atleta: el leaderboard de su box o de su coach. */
export default function Ranking() {
  const user = useCurrentUser();
  return (
    <>
      <PageHeader title="Leaderboard" subtitle={equipoDe(user, true).subtitulo} />
      <RankingDelBox esAtleta />
    </>
  );
}

/** Una fila del ranking ya lista para mostrar, venga de las marcas o de un WOD. */
interface FilaDeRanking {
  posicion: number;
  userId: string;
  nombre: string;
  tieneFoto: boolean;
  categoria: "rx" | "scaled" | null;
  esYo: boolean;
  valor: string;
  detalle?: string;
}

function iniciales(nombre: string): string {
  return nombre
    .split(" ")
    .slice(0, 2)
    .map((parte) => parte[0]?.toUpperCase())
    .join("");
}

function Avatar({ userId, tieneFoto, nombre, tamano }: { userId: string; tieneFoto: boolean; nombre: string; tamano: string }) {
  const avatarUrl = useAvatarUrl(userId, tieneFoto);
  const letras = iniciales(nombre);
  return (
    <div className={cx("flex shrink-0 items-center justify-center overflow-hidden rounded-full bg-brand-soft text-brand", tamano)}>
      {avatarUrl ? (
        <img src={avatarUrl} alt="" className="h-full w-full object-cover" />
      ) : letras ? (
        <span className="font-bold">{letras}</span>
      ) : (
        <IconUser className="h-5 w-5" />
      )}
    </div>
  );
}

/** El ranking del box entre atletas: marcas de Snatch y Clean & Jerk, y los WODs que anotaron.
 *  Lo usan el atleta (pantalla Ranking) y los entrenadores (pestaña Ranking de Atletas), que además
 *  pueden acotarlo a uno de sus grupos de asesorados.
 *
 *  Arriba hay UNA sola fila de opciones (los levantamientos y "WODs"); el sexo y el grupo, que casi no se
 *  tocan, viven en una hoja de filtros. Los tres primeros van en un podio y el resto en lista. */
export function RankingDelBox({ esAtleta }: { esAtleta: boolean }) {
  const user = useCurrentUser();
  // Un coach independiente no tiene un box con varios atletas que compitan entre sí: sin pestaña de WODs.
  const hayWods = esAtleta || user.box?.kind !== "coach";
  const equipo = equipoDe(user, esAtleta);
  const grupos = useGroups();
  const [seleccion, setSeleccion] = useState<string | null>(null);
  const [sexo, setSexo] = useState<Sexo>("todos");
  const [grupoId, setGrupoId] = useState<string | null>(null);
  const [filtrosAbiertos, setFiltrosAbiertos] = useState(false);
  const filtros: FiltrosRanking = { sexo: sexo === "todos" ? undefined : sexo, grupoId };

  const lifts = useRankingLifts(filtros);
  const actual =
    seleccion === WODS && hayWods ? WODS : seleccion && lifts.data?.some((l) => l.key === seleccion) ? seleccion : (lifts.data?.[0]?.key ?? (hayWods ? WODS : ""));

  const grupo = grupos.data?.find((g) => g.id === grupoId);
  const filtrosActivos = grupoId !== null || sexo !== "todos";
  const resumen = [grupo?.name, sexo !== "todos" ? ETIQUETA_DE_SEXO[sexo] : null].filter(Boolean).join(" · ");

  return (
    <>
      <div className="mb-3 flex items-center justify-between gap-3">
        <p className="min-w-0 truncate text-xs font-semibold tracking-wide text-muted uppercase">
          {grupo ? `Grupo ${grupo.name}` : equipo.todos}
        </p>
        <button
          type="button"
          onClick={() => setFiltrosAbiertos(true)}
          aria-label="Filtros del leaderboard"
          className={cx(
            "flex min-h-10 shrink-0 items-center gap-2 rounded-full px-3.5 text-sm font-semibold active:opacity-80",
            filtrosActivos ? "bg-brand-soft text-brand" : "bg-surface-2 text-muted",
          )}
        >
          <IconFilter className="h-4 w-4" />
          {filtrosActivos ? resumen : "Filtros"}
        </button>
      </div>

      {/* Una sola fila: los levantamientos y los WODs */}
      <div className="mb-4 flex gap-2 overflow-x-auto pb-1">
        {(lifts.data ?? []).map((l) => (
          <Chip key={l.key} activo={actual === l.key} onClick={() => setSeleccion(l.key)}>
            {l.name}
          </Chip>
        ))}
        {hayWods && (
          <Chip activo={actual === WODS} onClick={() => setSeleccion(WODS)}>
            WODs
          </Chip>
        )}
      </div>

      {lifts.error && <ErrorState error={lifts.error} onRetry={() => void lifts.refetch()} />}
      {lifts.isPending && <LoadingList rows={3} />}

      {actual === WODS ? (
        <Wods filtros={filtros} esAtleta={esAtleta} />
      ) : (
        !lifts.isPending && actual !== "" && <Marcas lift={actual} nombre={lifts.data?.find((l) => l.key === actual)?.name} filtros={filtros} esAtleta={esAtleta} />
      )}

      <p className="mt-6 text-center text-xs text-muted">
        Aparecen los atletas {grupoId ? "del grupo" : equipo.de} que lo permiten.
        {esAtleta && (
          <>
            {" "}
            Puedes salir del leaderboard desde{" "}
            <Link to="/perfil" className="font-semibold underline">
              tu perfil
            </Link>
            .
          </>
        )}
      </p>

      <FiltrosDelRanking
        open={filtrosAbiertos}
        onClose={() => setFiltrosAbiertos(false)}
        esAtleta={esAtleta}
        grupoId={grupoId}
        onGrupo={setGrupoId}
        sexo={sexo}
        onSexo={setSexo}
        grupos={grupos.data ?? []}
      />
    </>
  );
}

function Chip({ activo, onClick, children }: { activo: boolean; onClick: () => void; children: React.ReactNode }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={cx(
        "min-h-touch shrink-0 rounded-full px-4 py-2 text-sm font-semibold",
        activo ? "bg-brand text-on-brand" : "bg-surface-2 text-muted",
      )}
    >
      {children}
    </button>
  );
}

// ---------------------------------------------------------------- filtros

/** El sexo y (para el entrenador) el grupo. Cambian al tocarlos: no hay que "aplicar". */
function FiltrosDelRanking({
  open,
  onClose,
  esAtleta,
  grupoId,
  onGrupo,
  sexo,
  onSexo,
  grupos,
}: {
  open: boolean;
  onClose: () => void;
  esAtleta: boolean;
  grupoId: string | null;
  onGrupo: (id: string | null) => void;
  sexo: Sexo;
  onSexo: (sexo: Sexo) => void;
  grupos: { id: string; name: string }[];
}) {
  const user = useCurrentUser();
  const todos = equipoDe(user, esAtleta).todos;
  const opcionesDeGrupo = [{ id: null as string | null, name: todos }, ...grupos];
  return (
    <Sheet open={open} onClose={onClose} title="Filtros del leaderboard">
      <div className="space-y-5 pb-4">
        <div>
          <span className="mb-1.5 block text-sm font-medium text-muted">Sexo</span>
          <Segmented<Sexo>
            value={sexo}
            onChange={onSexo}
            options={[
              { value: "todos", label: "Todos" },
              { value: "female", label: "Mujeres" },
              { value: "male", label: "Hombres" },
            ]}
          />
        </div>

        {!esAtleta && grupos.length > 0 && (
          <div>
            <span className="mb-1.5 block text-sm font-medium text-muted">Atletas</span>
            <div className="space-y-1.5">
              {opcionesDeGrupo.map((g) => (
                <button
                  key={g.id ?? "box"}
                  type="button"
                  onClick={() => onGrupo(g.id)}
                  className={cx(
                    "flex min-h-touch w-full items-center justify-between gap-3 rounded-xl px-4 py-2 text-left font-semibold",
                    g.id === grupoId ? "bg-brand-soft text-brand" : "bg-surface-2",
                  )}
                >
                  <span className="truncate">{g.name}</span>
                  {g.id === grupoId && <IconCheck className="h-5 w-5 shrink-0" />}
                </button>
              ))}
            </div>
          </div>
        )}

        <Button full onClick={onClose}>
          Listo
        </Button>
      </div>
    </Sheet>
  );
}

// ---------------------------------------------------------------- podio y lista

/** Los tres primeros en un podio (el segundo a la izquierda y el tercero a la derecha) y el resto en lista. */
function TablaDeRanking({ filas }: { filas: FilaDeRanking[] }) {
  const podio = filas.slice(0, 3);
  const resto = filas.slice(3);
  // El orden de izquierda a derecha: 2.º, 1.º, 3.º
  const enPantalla = [podio[1], podio[0], podio[2]].filter((f): f is FilaDeRanking => Boolean(f));
  return (
    <>
      <div className="flex items-end justify-center gap-2 rounded-2xl border border-line bg-surface px-3 pt-6">
        {enPantalla.map((fila) => (
          <PuestoDelPodio key={fila.userId} fila={fila} />
        ))}
      </div>
      {resto.length > 0 && (
        <div className="mt-3 space-y-2">
          {resto.map((fila) => (
            <FilaDeLista key={fila.userId} fila={fila} />
          ))}
        </div>
      )}
    </>
  );
}

const ALTO_DEL_PEDESTAL = ["h-16", "h-11", "h-8"];

function PuestoDelPodio({ fila }: { fila: FilaDeRanking }) {
  const primero = fila.posicion === 1;
  return (
    <div className="flex min-w-0 flex-1 basis-0 flex-col items-center">
      <div className="relative">
        <div className={cx("rounded-full", fila.esYo && "ring-2 ring-brand ring-offset-2 ring-offset-surface")}>
          <Avatar
            userId={fila.userId}
            tieneFoto={fila.tieneFoto}
            nombre={fila.nombre}
            tamano={primero ? "h-16 w-16 text-lg" : "h-14 w-14 text-base"}
          />
        </div>
        <span className="absolute -bottom-2 left-1/2 -translate-x-1/2 text-xl leading-none">{MEDALLAS[fila.posicion - 1]}</span>
      </div>
      <p className="mt-4 w-full truncate text-center text-sm font-bold">{nombreCorto(fila.nombre)}</p>
      {fila.esYo && <p className="text-xs font-semibold text-brand">tú</p>}
      <p
        className={cx(
          "num mt-0.5 w-full text-center leading-tight font-extrabold break-words",
          fila.valor.length > 8 ? "text-sm" : "text-base",
        )}
      >
        {fila.valor}
      </p>
      <p className="flex min-h-5 items-center gap-1.5 text-xs text-muted">
        {fila.categoria && <Badge>{fila.categoria === "rx" ? "Rx" : "Scaled"}</Badge>}
        {fila.detalle}
      </p>
      <div
        className={cx(
          "mt-2 flex w-full items-start justify-center rounded-t-xl border border-b-0 pt-1.5 text-sm font-extrabold",
          ALTO_DEL_PEDESTAL[fila.posicion - 1],
          primero ? "border-brand/40 bg-brand-soft text-brand" : "border-line bg-surface-2 text-muted",
        )}
      >
        {fila.posicion}
      </div>
    </div>
  );
}

function FilaDeLista({ fila }: { fila: FilaDeRanking }) {
  return (
    <div
      className={cx(
        "flex items-center gap-3 rounded-2xl border p-3",
        fila.esYo ? "border-brand bg-brand-soft" : "border-line bg-surface",
      )}
    >
      <div className="flex w-7 shrink-0 items-center justify-center text-base font-bold text-muted">{fila.posicion}</div>
      <Avatar userId={fila.userId} tieneFoto={fila.tieneFoto} nombre={fila.nombre} tamano="h-11 w-11 text-sm" />
      <div className="min-w-0 grow">
        <p className="truncate font-bold">
          {fila.nombre}
          {fila.esYo && <span className="text-brand"> · tú</span>}
        </p>
        {(fila.categoria || fila.detalle) && (
          <p className="flex items-center gap-2 text-xs text-muted">
            {fila.categoria && <Badge>{fila.categoria === "rx" ? "Rx" : "Scaled"}</Badge>}
            {fila.detalle}
          </p>
        )}
      </div>
      <p className="num max-w-[45%] shrink-0 text-right text-lg leading-tight font-extrabold">{fila.valor}</p>
    </div>
  );
}

// ---------------------------------------------------------------- marcas (1RM)

function Marcas({
  lift,
  nombre,
  filtros,
  esAtleta,
}: {
  lift: string;
  nombre: string | undefined;
  filtros: FiltrosRanking;
  esAtleta: boolean;
}) {
  const unit = useWeightUnit();
  const tabla = useRankingLift(lift, filtros);

  if (tabla.isPending) return <LoadingList rows={3} />;
  if (tabla.error) return <ErrorState error={tabla.error} onRetry={() => void tabla.refetch()} />;
  if (tabla.data.length === 0) {
    return (
      <EmptyState icon={<IconTrophy className="h-10 w-10" />} title={`Sin marcas de ${nombre ?? "este levantamiento"}`}>
        {esAtleta
          ? "Nadie ha registrado su marca todavía. Registra tu 1RM en tu perfil y aparecerás aquí."
          : "Los atletas todavía no tienen marca de este levantamiento."}
      </EmptyState>
    );
  }
  return <TablaDeRanking filas={tabla.data.map((f) => deMarca(f, formatWeight(f.weight_kg, unit)))} />;
}

function deMarca(fila: RankingLiftRow, valor: string): FilaDeRanking {
  return {
    posicion: fila.rank,
    userId: fila.user_id,
    nombre: fila.full_name,
    tieneFoto: fila.has_avatar,
    categoria: fila.category,
    esYo: fila.is_me,
    valor,
  };
}

// ---------------------------------------------------------------- WODs

const selectClass = "min-h-12 w-full rounded-xl border border-line bg-surface-2 px-3.5 text-fg";

function Wods({ filtros, esAtleta }: { filtros: FiltrosRanking; esAtleta: boolean }) {
  const wods = useRankingWods(filtros);
  const [elegido, setElegido] = useState<string | null>(null);
  const idDe = (w: { key: string; wod_format: string }) => `${w.key}|${w.wod_format}`;
  const actual = wods.data?.find((w) => idDe(w) === elegido) ?? wods.data?.[0] ?? null;
  const tabla = useRankingWod(actual?.key ?? null, actual?.wod_format ?? null, filtros);

  if (wods.isPending) return <LoadingList rows={3} />;
  if (wods.error) return <ErrorState error={wods.error} onRetry={() => void wods.refetch()} />;
  if (!wods.data.length) {
    return (
      <EmptyState icon={<IconTrophy className="h-10 w-10" />} title="Todavía no hay WODs">
        {esAtleta
          ? "Anota un WOD con su resultado en tu entreno (con el nombre del WOD, por ejemplo «Fran») y aparecerás aquí junto a quienes lo hicieron."
          : "Cuando los atletas anoten un WOD con su resultado (con su nombre, por ejemplo «Fran»), aparecerá aquí."}
      </EmptyState>
    );
  }

  return (
    <>
      {/* Con un solo WOD no hay nada que elegir */}
      {wods.data.length > 1 && (
        <select
          value={actual ? idDe(actual) : ""}
          onChange={(e) => setElegido(e.target.value)}
          aria-label="WOD"
          className={cx(selectClass, "mb-4")}
        >
          {wods.data.map((w) => (
            <option key={idDe(w)} value={idDe(w)}>
              {w.name} · {WOD_FORMAT_LABELS[w.wod_format as keyof typeof WOD_FORMAT_LABELS] ?? w.wod_format} ({w.athletes_count})
            </option>
          ))}
        </select>
      )}
      {wods.data.length === 1 && actual && (
        <p className="mb-3 text-sm text-muted">
          {actual.name} · {WOD_FORMAT_LABELS[actual.wod_format as keyof typeof WOD_FORMAT_LABELS] ?? actual.wod_format}
        </p>
      )}
      {tabla.isPending && <LoadingList rows={3} />}
      {tabla.error && <ErrorState error={tabla.error} onRetry={() => void tabla.refetch()} />}
      {tabla.data && tabla.data.length > 0 && <TablaDeRanking filas={tabla.data.map(deWod)} />}
    </>
  );
}

function deWod(fila: RankingWodRow): FilaDeRanking {
  return {
    posicion: fila.rank,
    userId: fila.user_id,
    nombre: fila.full_name,
    tieneFoto: fila.has_avatar,
    categoria: fila.category,
    esYo: fila.is_me,
    valor: soloElResultado(fila.score_label),
    detalle: shortDate(fila.date),
  };
}
