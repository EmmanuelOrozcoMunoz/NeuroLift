import { useState } from "react";
import { Link } from "react-router-dom";

import { PageHeader } from "@/components/AppShell";
import { IconTrophy, IconUser } from "@/components/icons";
import { Badge, EmptyState, ErrorState, LoadingList, Segmented, cx } from "@/components/ui";
import { useCurrentUser } from "@/lib/auth";
import { useGroups } from "@/lib/coachQueries";
import { shortDate } from "@/lib/dates";
import { useRankingLift, useRankingLifts, useRankingWod, useRankingWods } from "@/lib/rankingQueries";
import type { FiltrosRanking } from "@/lib/rankingQueries";
import { formatWeight, useWeightUnit } from "@/lib/units";
import { useAvatarUrl } from "@/lib/useAvatarUrl";
import { WOD_FORMAT_LABELS } from "@/lib/wod";
import type { RankingLiftRow, RankingWodRow } from "@/lib/types";

type Vista = "marcas" | "wods";
type Sexo = "todos" | "female" | "male";

const MEDALLAS = ["🥇", "🥈", "🥉"];

/** Pantalla del atleta: el ranking de su box. */
export default function Ranking() {
  const user = useCurrentUser();
  return (
    <>
      <PageHeader title="Ranking" subtitle={user.box?.name ?? "Tu box"} />
      <RankingDelBox esAtleta />
    </>
  );
}

/** Elige entre el ranking de todo el box o el de uno de los grupos del entrenador. */
function SelectorDeGrupo({ valor, onChange }: { valor: string | null; onChange: (id: string | null) => void }) {
  const grupos = useGroups();
  if (!grupos.data?.length) return null;
  return (
    <div className="mb-3 flex flex-wrap gap-2">
      {[{ id: null as string | null, name: "Todo el box" }, ...grupos.data].map((g) => (
        <button
          key={g.id ?? "box"}
          type="button"
          onClick={() => onChange(g.id)}
          className={cx(
            "min-h-touch max-w-full truncate rounded-full px-4 py-2 text-sm font-semibold",
            g.id === valor ? "bg-brand text-on-brand" : "bg-surface-2 text-muted",
          )}
        >
          {g.name}
        </button>
      ))}
    </div>
  );
}

/** El ranking del box entre atletas: marcas de Snatch y Clean & Jerk, y los WODs que anotaron.
 *  Lo usan el atleta (pantalla Ranking) y los entrenadores (pestaña de Actividad), que además
 *  pueden acotarlo a uno de sus grupos de asesorados. */
export function RankingDelBox({ esAtleta }: { esAtleta: boolean }) {
  const [vista, setVista] = useState<Vista>("marcas");
  const [sexo, setSexo] = useState<Sexo>("todos");
  const [grupoId, setGrupoId] = useState<string | null>(null);
  const filtros: FiltrosRanking = { sexo: sexo === "todos" ? undefined : sexo, grupoId };

  return (
    <>
      {!esAtleta && <SelectorDeGrupo valor={grupoId} onChange={setGrupoId} />}
      <div className="mb-3">
        <Segmented<Vista>
          value={vista}
          onChange={setVista}
          options={[
            { value: "marcas", label: "Marcas (RM)" },
            { value: "wods", label: "WODs" },
          ]}
        />
      </div>
      <div className="mb-4">
        <Segmented<Sexo>
          value={sexo}
          onChange={setSexo}
          options={[
            { value: "todos", label: "Todos" },
            { value: "female", label: "Mujeres" },
            { value: "male", label: "Hombres" },
          ]}
        />
      </div>

      {vista === "marcas" ? (
        <Marcas filtros={filtros} esAtleta={esAtleta} />
      ) : (
        <Wods filtros={filtros} esAtleta={esAtleta} />
      )}

      <p className="mt-6 text-center text-xs text-muted">
        Aparecen los atletas {grupoId ? "del grupo" : "del box"} que lo permiten.
        {esAtleta && (
          <>
            {" "}
            Puedes salir del ranking desde{" "}
            <Link to="/perfil" className="font-semibold underline">
              tu perfil
            </Link>
            .
          </>
        )}
      </p>
    </>
  );
}

// ---------------------------------------------------------------- selector de la lista

function Selector<T extends string>({
  opciones,
  valor,
  onChange,
}: {
  opciones: { valor: T; etiqueta: string; detalle: string }[];
  valor: T | null;
  onChange: (valor: T) => void;
}) {
  return (
    <div className="mb-4 flex flex-wrap gap-2">
      {opciones.map((o) => (
        <button
          key={o.valor}
          type="button"
          onClick={() => onChange(o.valor)}
          className={cx(
            "min-h-touch max-w-full truncate rounded-full px-4 py-2 text-sm font-semibold",
            o.valor === valor ? "bg-brand text-on-brand" : "bg-surface-2 text-muted",
          )}
        >
          {o.etiqueta} <span className="opacity-70">· {o.detalle}</span>
        </button>
      ))}
    </div>
  );
}

// ---------------------------------------------------------------- marcas (1RM)

function Marcas({ filtros, esAtleta }: { filtros: FiltrosRanking; esAtleta: boolean }) {
  const lifts = useRankingLifts(filtros);
  const [elegido, setElegido] = useState<string | null>(null);
  const actual = elegido && lifts.data?.some((l) => l.key === elegido) ? elegido : (lifts.data?.[0]?.key ?? null);
  const tabla = useRankingLift(actual, filtros);

  if (lifts.isPending) return <LoadingList rows={4} />;
  if (lifts.error) return <ErrorState error={lifts.error} onRetry={() => void lifts.refetch()} />;
  const nombre = lifts.data.find((l) => l.key === actual)?.name ?? "este levantamiento";

  return (
    <>
      <Selector
        opciones={lifts.data.map((l) => ({ valor: l.key, etiqueta: l.name, detalle: String(l.athletes_count) }))}
        valor={actual}
        onChange={setElegido}
      />
      {tabla.isPending && <LoadingList rows={3} />}
      {tabla.error && <ErrorState error={tabla.error} onRetry={() => void tabla.refetch()} />}
      {tabla.data && tabla.data.length === 0 && (
        <EmptyState icon={<IconTrophy className="h-10 w-10" />} title={`Sin marcas de ${nombre}`}>
          {esAtleta
            ? "Nadie ha registrado su marca todavía. Registra tu 1RM en tu perfil y aparecerás aquí."
            : "Los atletas del box todavía no tienen marca de este levantamiento."}
        </EmptyState>
      )}
      <div className="space-y-2">
        {(tabla.data ?? []).map((fila) => (
          <MarcaFila key={fila.user_id} fila={fila} />
        ))}
      </div>
    </>
  );
}

function MarcaFila({ fila }: { fila: RankingLiftRow }) {
  const unit = useWeightUnit();
  return (
    <FilaBase
      posicion={fila.rank}
      userId={fila.user_id}
      nombre={fila.full_name}
      tieneFoto={fila.has_avatar}
      categoria={fila.category}
      esYo={fila.is_me}
      valor={formatWeight(fila.weight_kg, unit)}
    />
  );
}

// ---------------------------------------------------------------- WODs

function Wods({ filtros, esAtleta }: { filtros: FiltrosRanking; esAtleta: boolean }) {
  const wods = useRankingWods(filtros);
  const [elegido, setElegido] = useState<string | null>(null);
  const idDe = (w: { key: string; wod_format: string }) => `${w.key}|${w.wod_format}`;
  const actual = wods.data?.find((w) => idDe(w) === elegido) ?? wods.data?.[0] ?? null;
  const tabla = useRankingWod(actual?.key ?? null, actual?.wod_format ?? null, filtros);

  if (wods.isPending) return <LoadingList rows={4} />;
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
      <Selector
        opciones={wods.data.map((w) => ({
          valor: idDe(w),
          etiqueta: w.name,
          detalle: `${WOD_FORMAT_LABELS[w.wod_format as keyof typeof WOD_FORMAT_LABELS] ?? w.wod_format} · ${w.athletes_count}`,
        }))}
        valor={actual ? idDe(actual) : null}
        onChange={setElegido}
      />
      {tabla.isPending && <LoadingList rows={3} />}
      {tabla.error && <ErrorState error={tabla.error} onRetry={() => void tabla.refetch()} />}
      <div className="space-y-2">
        {(tabla.data ?? []).map((fila) => (
          <WodFila key={fila.user_id} fila={fila} />
        ))}
      </div>
    </>
  );
}

function WodFila({ fila }: { fila: RankingWodRow }) {
  return (
    <FilaBase
      posicion={fila.rank}
      userId={fila.user_id}
      nombre={fila.full_name}
      tieneFoto={fila.has_avatar}
      categoria={fila.category}
      esYo={fila.is_me}
      valor={fila.score_label ?? "—"}
      detalle={shortDate(fila.date)}
    />
  );
}

// ---------------------------------------------------------------- fila común

function FilaBase({
  posicion,
  userId,
  nombre,
  tieneFoto,
  categoria,
  esYo,
  valor,
  detalle,
}: {
  posicion: number;
  userId: string;
  nombre: string;
  tieneFoto: boolean;
  categoria: string | null;
  esYo: boolean;
  valor: string;
  detalle?: string;
}) {
  const avatarUrl = useAvatarUrl(userId, tieneFoto);
  const iniciales = nombre
    .split(" ")
    .slice(0, 2)
    .map((parte) => parte[0]?.toUpperCase())
    .join("");

  return (
    <div
      className={cx(
        "flex items-center gap-3 rounded-2xl border p-3",
        esYo ? "border-brand bg-brand-soft" : "border-line bg-surface",
      )}
    >
      <div className="flex w-7 shrink-0 items-center justify-center text-base font-bold text-muted">
        {MEDALLAS[posicion - 1] ?? posicion}
      </div>
      <div className="flex h-11 w-11 shrink-0 items-center justify-center overflow-hidden rounded-full bg-brand-soft text-brand">
        {avatarUrl ? (
          <img src={avatarUrl} alt="" className="h-full w-full object-cover" />
        ) : iniciales ? (
          <span className="text-sm font-bold">{iniciales}</span>
        ) : (
          <IconUser className="h-5 w-5" />
        )}
      </div>
      <div className="min-w-0 grow">
        <p className="truncate font-bold">
          {nombre}
          {esYo && <span className="text-brand"> · tú</span>}
        </p>
        {(categoria || detalle) && (
          <p className="flex items-center gap-2 text-xs text-muted">
            {categoria && <Badge>{categoria === "rx" ? "Rx" : "Scaled"}</Badge>}
            {detalle}
          </p>
        )}
      </div>
      <p className="num shrink-0 whitespace-nowrap text-right text-lg font-extrabold">{valor}</p>
    </div>
  );
}
