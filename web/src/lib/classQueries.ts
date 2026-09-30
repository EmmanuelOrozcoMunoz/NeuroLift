import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import type { UseQueryResult } from "@tanstack/react-query";

import { apiFetch } from "@/lib/api";
import { useCurrentUser } from "@/lib/auth";
import { queryKeys } from "@/lib/queries";
import type {
  BoxClass,
  BoxClassPayload,
  ClassOccurrence,
  ClassProgram,
  MessageResponse,
  OwnerDashboard,
} from "@/lib/types";

export const classKeys = {
  all: ["classes"] as const,
  list: ["classes", "list"] as const,
  schedule: (start: string, days: number) => ["classes", "schedule", start, days] as const,
  programs: (classId: string) => ["classes", "programs", classId] as const,
  dashboard: ["box", "dashboard"] as const,
};

export function useClasses(enabled = true): UseQueryResult<BoxClass[]> {
  return useQuery({ queryKey: classKeys.list, queryFn: () => apiFetch<BoxClass[]>("/classes/"), enabled });
}

/** Horario día por día desde `start` (YYYY-MM-DD). */
export function useClassSchedule(start: string, days = 7, enabled = true): UseQueryResult<ClassOccurrence[]> {
  return useQuery({
    queryKey: classKeys.schedule(start, days),
    queryFn: () => apiFetch<ClassOccurrence[]>(`/classes/schedule?start=${start}&days=${days}`),
    enabled,
  });
}

function useInvalidateClasses() {
  const queryClient = useQueryClient();
  return () => {
    void queryClient.invalidateQueries({ queryKey: classKeys.all });
    void queryClient.invalidateQueries({ queryKey: classKeys.dashboard });
  };
}

export function useSaveClass() {
  const invalidate = useInvalidateClasses();
  return useMutation({
    mutationFn: ({ id, body }: { id?: string; body: BoxClassPayload & { clear_coach?: boolean } }) =>
      id
        ? apiFetch<BoxClass>(`/classes/${id}`, { method: "PUT", body })
        : apiFetch<BoxClass>("/classes/", { method: "POST", body }),
    onSuccess: invalidate,
  });
}

export function useDeactivateClass() {
  const invalidate = useInvalidateClasses();
  return useMutation({
    mutationFn: (id: string) => apiFetch<MessageResponse>(`/classes/${id}`, { method: "DELETE" }),
    onSuccess: invalidate,
  });
}

/** Programar la clase como un bloque de varias semanas (estructura de mesociclo). */
export function useCreateClassProgram() {
  const invalidate = useInvalidateClasses();
  return useMutation({
    mutationFn: ({ classId, ...body }: { classId: string; name: string; start_date: string; weeks_count: number }) =>
      apiFetch<ClassProgram>(`/classes/${classId}/programs`, { method: "POST", body }),
    onSuccess: invalidate,
  });
}

/** Programar la clase de un solo día. Idempotente: si ya tiene contenido, devuelve esa sesión. */
export function useCreateClassDay() {
  const invalidate = useInvalidateClasses();
  return useMutation({
    mutationFn: ({ classId, date }: { classId: string; date: string }) =>
      apiFetch<{ mesocycle_id: string; session_id: string }>(`/classes/${classId}/days`, {
        method: "POST",
        body: { date },
      }),
    onSuccess: invalidate,
  });
}

/** El atleta quita un registro ANTIGUO de clase (de cuando se podían registrar). La clase no se toca. */
export function useLeaveClass() {
  const queryClient = useQueryClient();
  const user = useCurrentUser();
  return useMutation({
    mutationFn: ({ classSessionId }: { classSessionId: string; mesocycleId: string }) =>
      apiFetch<MessageResponse>(`/classes/sessions/${classSessionId}/join`, { method: "DELETE" }),
    onSuccess: (_res, { mesocycleId }) => {
      queryClient.removeQueries({ queryKey: queryKeys.mesocycle(mesocycleId) });
      void queryClient.invalidateQueries({ queryKey: classKeys.all });
      void queryClient.invalidateQueries({ queryKey: queryKeys.mesocycles(user.id) });
    },
  });
}

export function useOwnerDashboard(): UseQueryResult<OwnerDashboard> {
  return useQuery({ queryKey: classKeys.dashboard, queryFn: () => apiFetch<OwnerDashboard>("/boxes/me/dashboard") });
}
