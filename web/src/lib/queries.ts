import { useMutation, useQueries, useQuery, useQueryClient } from "@tanstack/react-query";
import type { UseQueryResult } from "@tanstack/react-query";

import { apiFetch } from "@/lib/api";
import type {
  FitnessLevel,
  MesocycleFull,
  MesocycleSummary,
  MessageResponse,
  PersonalRecord,
  PlanDetailResponse,
  PlanSummary,
  RecentSessionSummary,
  SessionCompletePayload,
  TrainingSession,
  User,
  WodFormatPayload,
} from "@/lib/types";

export const queryKeys = {
  mesocycles: (userId: string) => ["mesocycles", userId] as const,
  mesocycle: (id: string) => ["mesocycle", id] as const,
  prs: (userId: string) => ["prs", userId] as const,
  fitness: (userId: string) => ["fitness", userId] as const,
  recentActivity: (userId: string) => ["recent-activity", userId] as const,
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

/** Todas las sesiones del atleta, de TODOS sus mesociclos a la vez — para la vista de
 *  calendario, que no puede depender de un solo mesociclo como `useMesocycle`. No hay un
 *  endpoint que devuelva esto en un solo viaje, así que se pide la lista de mesociclos y
 *  luego el detalle de cada uno en paralelo (mismo patrón que `AthleteDetail.tsx` con los
 *  grupos de un coach) — un atleta tiene pocos mesociclos, así que esto no escala mal. */
export function useMesocyclesWithSessions(userId: string): {
  sessions: TrainingSession[];
  isPending: boolean;
  error: Error | null;
} {
  const mesocycles = useMesocycles(userId);
  const details = useQueries({
    queries: (mesocycles.data ?? []).map((m) => ({
      queryKey: queryKeys.mesocycle(m.id),
      queryFn: () => apiFetch<MesocycleFull>(`/mesocycles/${m.id}`),
    })),
  });

  const isPending = mesocycles.isPending || details.some((d) => d.isPending);
  const error = (mesocycles.error as Error | null) ?? (details.find((d) => d.error)?.error as Error | undefined) ?? null;
  // Una sesión "adaptada al tiempo" vive el mismo día que su original (parent_session_id) --
  // sin filtrarla, un día con adaptación aparecería con dos sesiones/puntos en el calendario.
  // El toggle Normal/Adaptada para elegir cuál seguir vive dentro de la sesión, no aquí.
  const sessions = details.flatMap((d) => d.data?.sessions ?? []).filter((s) => !s.parent_session_id);

  return { sessions, isPending, error };
}

/** El coach prescribe (o quita) el formato de WOD de una sesión — el atleta ve ese formato al
 *  completarla y reporta el resultado que le corresponda (tiempo, rondas+reps, o si cumplió). */
export function useSetWodFormat(mesocycleId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ sessionId, body }: { sessionId: string; body: WodFormatPayload }) =>
      apiFetch<MessageResponse>(`/sessions/${sessionId}/wod-format`, { method: "PUT", body }),
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: queryKeys.mesocycle(mesocycleId) }),
  });
}

/** Últimas sesiones completadas de un atleta con lo que REALMENTE hizo — pesos/reps reales y
 *  resultado del WOD, no lo prescrito. Coach o el propio atleta pueden pedirlo. */
export function useRecentActivity(userId: string): UseQueryResult<RecentSessionSummary[]> {
  return useQuery({
    queryKey: queryKeys.recentActivity(userId),
    queryFn: () => apiFetch<RecentSessionSummary[]>(`/users/${userId}/recent-activity`),
  });
}

// ---------------------------------------------------------- registro de series

interface LogSetVars {
  mesocycleId: string;
  setId: string;
  /** null = deshacer el registro (vuelve a "pendiente"), no "cero". */
  actual_reps: number | null;
  actual_weight: number | null;
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
  /** Solo si la sesión tenía un wod_format prescrito — lo que el atleta reportó como resultado. */
  wodResult?: SessionCompletePayload;
}

export function useCompleteSession() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({ sessionId, alsoCompleteId, wodResult }: CompleteSessionVars) => {
      await apiFetch<MessageResponse>(`/sessions/${sessionId}/complete`, { method: "POST", body: wodResult });
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

/** Deshace "Terminar entrenamiento" (por si se tocó sin querer) -- vuelve la sesión a
 *  "pendiente" y borra el resultado del WOD que se hubiera reportado, no solo el estado. */
export function useUncompleteSession() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ sessionId }: { mesocycleId: string; sessionId: string }) =>
      apiFetch<MessageResponse>(`/sessions/${sessionId}/uncomplete`, { method: "POST" }),
    onMutate: async (vars: { mesocycleId: string; sessionId: string }) => {
      const key = queryKeys.mesocycle(vars.mesocycleId);
      const previous = queryClient.getQueryData<MesocycleFull>(key);
      queryClient.setQueryData<MesocycleFull>(key, (old) =>
        old
          ? {
              ...old,
              sessions: old.sessions.map((session) =>
                session.id === vars.sessionId ? { ...session, status: "pending" } : session,
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

export function useDeletePersonalRecord(userId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (recordId: string) =>
      apiFetch<MessageResponse>(`/users/${userId}/records/${recordId}`, { method: "DELETE" }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: queryKeys.prs(userId) });
      void queryClient.invalidateQueries({ queryKey: queryKeys.fitness(userId) });
    },
  });
}

export function useUpdateMyPreferences() {
  return useMutation({
    mutationFn: (body: { weight_unit?: "kg" | "lb"; has_25kg_plates?: boolean }) =>
      apiFetch<User>("/users/me/preferences", { method: "PUT", body }),
  });
}

/** Crea (o recupera, si ya existía) la sesión personal del atleta para una fecha -- su propio
 *  registro manual, sin depender de un coach. Ver POST /users/me/personal-sessions. */
export function useCreatePersonalSession(userId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (scheduled_date: string) =>
      apiFetch<TrainingSession>("/users/me/personal-sessions", { method: "POST", body: { scheduled_date } }),
    onSuccess: (session) => {
      void queryClient.invalidateQueries({ queryKey: queryKeys.mesocycles(userId) });
      void queryClient.invalidateQueries({ queryKey: queryKeys.mesocycle(session.mesocycle_id) });
    },
  });
}

/** Elimina un día suelto del calendario personal (y sus ejercicios) -- el backend solo lo
 *  permite sobre una sesión de un mesociclo is_self_managed (o a un coach/admin sobre lo suyo).
 *  Ver DELETE /sessions/{id}. */
export function useDeleteSession(userId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ sessionId }: { mesocycleId: string; sessionId: string }) =>
      apiFetch<MessageResponse>(`/sessions/${sessionId}`, { method: "DELETE" }),
    onSuccess: (_data, vars) => {
      void queryClient.invalidateQueries({ queryKey: queryKeys.mesocycles(userId) });
      void queryClient.invalidateQueries({ queryKey: queryKeys.mesocycle(vars.mesocycleId) });
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
      // Snatch/Clean & Jerk/Back Squat/Deadlift también quedan como PersonalRecord del lado del
      // backend — refresca "Récords (PRs)" para que se vean sin tener que cambiar de pantalla.
      void queryClient.invalidateQueries({ queryKey: queryKeys.prs(userId) });
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

/** El backend devuelve el plan completo (autor/admin) o una vista previa sin ejercicios/series
 *  (cualquier otro usuario) — ver PlanDetailResponse. Cada pantalla que consume esto debe
 *  chequear `is_preview` antes de asumir la forma. */
export function usePlanDetail(planId: string | undefined): UseQueryResult<PlanDetailResponse> {
  return useQuery({
    queryKey: queryKeys.plan(planId ?? "none"),
    queryFn: () => apiFetch<PlanDetailResponse>(`/plans/${planId}`),
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
