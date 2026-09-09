import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import type { UseQueryResult } from "@tanstack/react-query";

import { apiFetch } from "@/lib/api";
import type {
  FitnessLevel,
  MesocycleFull,
  MesocycleSummary,
  MessageResponse,
  PersonalRecord,
  PlanSummary,
  TrainingSession,
} from "@/lib/types";

export const queryKeys = {
  mesocycles: (userId: string) => ["mesocycles", userId] as const,
  mesocycle: (id: string) => ["mesocycle", id] as const,
  prs: (userId: string) => ["prs", userId] as const,
  fitness: (userId: string) => ["fitness", userId] as const,
  planCatalog: ["plans", "catalog"] as const,
  plan: (id: string) => ["plan", id] as const,
};

// ---------------------------------------------------------------- mesociclos

export function useMesocycles(userId: string): UseQueryResult<MesocycleSummary[]> {
  return useQuery({
    queryKey: queryKeys.mesocycles(userId),
    queryFn: () => apiFetch<MesocycleSummary[]>(`/users/${userId}/mesocycles/`),
  });
}

export function useMesocycle(mesocycleId: string | undefined): UseQueryResult<MesocycleFull> {
  return useQuery({
    queryKey: queryKeys.mesocycle(mesocycleId ?? "none"),
    queryFn: () => apiFetch<MesocycleFull>(`/mesocycles/${mesocycleId}`),
    enabled: Boolean(mesocycleId),
  });
}

// ---------------------------------------------------------- registro de series

interface LogSetVars {
  mesocycleId: string;
  setId: string;
  actual_reps: number;
  actual_weight: number;
}

/**
 * Registra una serie. La actualización es OPTIMISTA a propósito: el atleta está en el rack
 * con la barra cargada y mala señal — la UI tiene que responder al instante y el POST
 * reintentarse por debajo. Si falla de verdad, se revierte la caché.
 */
export function useLogSet() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ setId, actual_reps, actual_weight }: LogSetVars) =>
      apiFetch<unknown>(`/sets/${setId}/log`, {
        method: "PUT",
        body: { actual_reps, actual_weight },
      }),
    retry: 2,
    onMutate: async (vars) => {
      const key = queryKeys.mesocycle(vars.mesocycleId);
      await queryClient.cancelQueries({ queryKey: key });
      const previous = queryClient.getQueryData<MesocycleFull>(key);

      queryClient.setQueryData<MesocycleFull>(key, (old) => {
        if (!old) return old;
        return {
          ...old,
          sessions: old.sessions.map((session) => ({
            ...session,
            sets: session.sets.map((set) =>
              set.id === vars.setId
                ? { ...set, actual_reps: vars.actual_reps, actual_weight: vars.actual_weight }
                : set,
            ),
          })),
        };
      });

      return { previous, key };
    },
    onError: (_err, _vars, context) => {
      if (context?.previous) queryClient.setQueryData(context.key, context.previous);
    },
  });
}

interface CompleteSessionVars {
  mesocycleId: string;
  sessionId: string;
  /** Si se completó la versión adaptada, la original se marca también: para el calendario
   *  ese día ya está entrenado, y no tiene sentido que quede pendiente para siempre. */
  alsoCompleteId?: string;
}

export function useCompleteSession() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({ sessionId, alsoCompleteId }: CompleteSessionVars) => {
      await apiFetch<MessageResponse>(`/sessions/${sessionId}/complete`, { method: "POST" });
      if (alsoCompleteId) {
        await apiFetch<MessageResponse>(`/sessions/${alsoCompleteId}/complete`, { method: "POST" });
      }
    },
    onMutate: async (vars) => {
      const key = queryKeys.mesocycle(vars.mesocycleId);
      const previous = queryClient.getQueryData<MesocycleFull>(key);
      const marcadas = new Set([vars.sessionId, vars.alsoCompleteId].filter(Boolean) as string[]);
      queryClient.setQueryData<MesocycleFull>(key, (old) =>
        old
          ? {
              ...old,
              sessions: old.sessions.map((session) =>
                marcadas.has(session.id) ? { ...session, status: "completed" } : session,
              ),
            }
          : old,
      );
      return { previous, key };
    },
    onError: (_err, _vars, context) => {
      if (context?.previous) queryClient.setQueryData(context.key, context.previous);
    },
    onSettled: (_data, _err, vars) => {
      void queryClient.invalidateQueries({ queryKey: queryKeys.mesocycle(vars.mesocycleId) });
    },
  });
}

/** Pide a la IA una versión más corta de la sesión. La original nunca se toca. */
export function useAdaptSession() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ sessionId, minutes }: { mesocycleId: string; sessionId: string; minutes: number }) =>
      apiFetch<TrainingSession>(`/sessions/${sessionId}/adapt`, {
        method: "POST",
        body: { available_minutes: minutes },
      }),
    onSuccess: (_data, vars) => {
      void queryClient.invalidateQueries({ queryKey: queryKeys.mesocycle(vars.mesocycleId) });
    },
  });
}

// ------------------------------------------------------------------ marcas (PRs)

export function usePersonalRecords(userId: string): UseQueryResult<PersonalRecord[]> {
  return useQuery({
    queryKey: queryKeys.prs(userId),
    queryFn: () => apiFetch<PersonalRecord[]>(`/users/${userId}/records/`),
  });
}

export function useUpsertPersonalRecord(userId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (body: { exercise_name: string; max_weight_kg: number }) =>
      apiFetch<MessageResponse>(`/users/${userId}/records/`, { method: "POST", body }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: queryKeys.prs(userId) });
      // Las marcas alimentan el Fit Level de halterofilia
      void queryClient.invalidateQueries({ queryKey: queryKeys.fitness(userId) });
    },
  });
}

// -------------------------------------------------------------------- fit level

export function useFitnessLevel(userId: string): UseQueryResult<FitnessLevel> {
  return useQuery({
    queryKey: queryKeys.fitness(userId),
    queryFn: () => apiFetch<FitnessLevel>(`/users/${userId}/fitness-level`),
  });
}

export function useSaveBenchmarks(userId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (body: Record<string, number | string>) =>
      apiFetch<FitnessLevel>(`/users/${userId}/fitness-benchmarks`, { method: "PUT", body }),
    onSuccess: (data) => {
      queryClient.setQueryData(queryKeys.fitness(userId), data);
    },
  });
}

// ----------------------------------------------------------------------- planes

export function usePlanCatalog(): UseQueryResult<PlanSummary[]> {
  return useQuery({
    queryKey: queryKeys.planCatalog,
    queryFn: () => apiFetch<PlanSummary[]>("/plans/catalog"),
  });
}

export function usePlanDetail(planId: string | undefined): UseQueryResult<MesocycleFull> {
  return useQuery({
    queryKey: queryKeys.plan(planId ?? "none"),
    queryFn: () => apiFetch<MesocycleFull>(`/plans/${planId}`),
    enabled: Boolean(planId),
  });
}

export function useAcquirePlan(userId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ planId, startDate }: { planId: string; startDate: string }) =>
      apiFetch<MessageResponse>(`/plans/${planId}/acquire`, {
        method: "POST",
        body: { start_date: startDate },
      }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: queryKeys.mesocycles(userId) });
    },
  });
}
