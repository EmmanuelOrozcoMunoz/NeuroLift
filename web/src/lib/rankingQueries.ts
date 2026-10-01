import { useQuery } from "@tanstack/react-query";
import type { UseQueryResult } from "@tanstack/react-query";

import { apiFetch } from "@/lib/api";
import type { RankingLift, RankingLiftRow, RankingWod, RankingWodRow } from "@/lib/types";

type Sexo = "male" | "female" | undefined;

/** Filtros del ranking: sexo y, para un entrenador, uno de sus grupos (sin grupo = todo el box). */
export type FiltrosRanking = { sexo?: Sexo; grupoId?: string | null };

const consulta = (f: FiltrosRanking, extra: Record<string, string> = {}) => {
  const params = new URLSearchParams(extra);
  if (f.sexo) params.set("sex", f.sexo);
  if (f.grupoId) params.set("group_id", f.grupoId);
  const texto = params.toString();
  return texto ? `?${texto}` : "";
};

const clave = (f: FiltrosRanking) => [f.sexo ?? "todos", f.grupoId ?? "box"] as const;

export const rankingKeys = {
  all: ["ranking"] as const,
  lifts: (f: FiltrosRanking) => ["ranking", "lifts", ...clave(f)] as const,
  lift: (key: string, f: FiltrosRanking) => ["ranking", "lift", key, ...clave(f)] as const,
  wods: (f: FiltrosRanking) => ["ranking", "wods", ...clave(f)] as const,
  wod: (key: string, formato: string, f: FiltrosRanking) => ["ranking", "wod", key, formato, ...clave(f)] as const,
};

export function useRankingLifts(f: FiltrosRanking): UseQueryResult<RankingLift[]> {
  return useQuery({
    queryKey: rankingKeys.lifts(f),
    queryFn: () => apiFetch<RankingLift[]>(`/ranking/lifts${consulta(f)}`),
  });
}

export function useRankingLift(key: string | null, f: FiltrosRanking): UseQueryResult<RankingLiftRow[]> {
  return useQuery({
    queryKey: rankingKeys.lift(key ?? "", f),
    queryFn: () => apiFetch<RankingLiftRow[]>(`/ranking/lifts/${encodeURIComponent(key!)}${consulta(f)}`),
    enabled: Boolean(key),
  });
}

export function useRankingWods(f: FiltrosRanking): UseQueryResult<RankingWod[]> {
  return useQuery({
    queryKey: rankingKeys.wods(f),
    queryFn: () => apiFetch<RankingWod[]>(`/ranking/wods${consulta(f)}`),
  });
}

export function useRankingWod(key: string | null, formato: string | null, f: FiltrosRanking): UseQueryResult<RankingWodRow[]> {
  return useQuery({
    queryKey: rankingKeys.wod(key ?? "", formato ?? "", f),
    queryFn: () => apiFetch<RankingWodRow[]>(`/ranking/wods/${encodeURIComponent(key!)}${consulta(f, { wod_format: formato! })}`),
    enabled: Boolean(key && formato),
  });
}
