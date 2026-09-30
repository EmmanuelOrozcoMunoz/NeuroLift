import { useQuery } from "@tanstack/react-query";
import type { UseQueryResult } from "@tanstack/react-query";

import { apiFetch } from "@/lib/api";
import type { RankingLift, RankingLiftRow, RankingWod, RankingWodRow } from "@/lib/types";

type Sexo = "male" | "female" | undefined;

const conSexo = (sexo: Sexo) => (sexo ? `?sex=${sexo}` : "");

export const rankingKeys = {
  all: ["ranking"] as const,
  lifts: (sexo: Sexo) => ["ranking", "lifts", sexo ?? "todos"] as const,
  lift: (clave: string, sexo: Sexo) => ["ranking", "lift", clave, sexo ?? "todos"] as const,
  wods: (sexo: Sexo) => ["ranking", "wods", sexo ?? "todos"] as const,
  wod: (clave: string, formato: string, sexo: Sexo) => ["ranking", "wod", clave, formato, sexo ?? "todos"] as const,
};

export function useRankingLifts(sexo: Sexo): UseQueryResult<RankingLift[]> {
  return useQuery({
    queryKey: rankingKeys.lifts(sexo),
    queryFn: () => apiFetch<RankingLift[]>(`/ranking/lifts${conSexo(sexo)}`),
  });
}

export function useRankingLift(clave: string | null, sexo: Sexo): UseQueryResult<RankingLiftRow[]> {
  return useQuery({
    queryKey: rankingKeys.lift(clave ?? "", sexo),
    queryFn: () => apiFetch<RankingLiftRow[]>(`/ranking/lifts/${encodeURIComponent(clave!)}${conSexo(sexo)}`),
    enabled: Boolean(clave),
  });
}

export function useRankingWods(sexo: Sexo): UseQueryResult<RankingWod[]> {
  return useQuery({
    queryKey: rankingKeys.wods(sexo),
    queryFn: () => apiFetch<RankingWod[]>(`/ranking/wods${conSexo(sexo)}`),
  });
}

export function useRankingWod(clave: string | null, formato: string | null, sexo: Sexo): UseQueryResult<RankingWodRow[]> {
  return useQuery({
    queryKey: rankingKeys.wod(clave ?? "", formato ?? "", sexo),
    queryFn: () => {
      const params = new URLSearchParams({ wod_format: formato! });
      if (sexo) params.set("sex", sexo);
      return apiFetch<RankingWodRow[]>(`/ranking/wods/${encodeURIComponent(clave!)}?${params}`);
    },
    enabled: Boolean(clave && formato),
  });
}
