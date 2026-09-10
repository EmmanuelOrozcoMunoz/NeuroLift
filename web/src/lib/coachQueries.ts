import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import type { UseQueryResult } from "@tanstack/react-query";

import { apiFetch } from "@/lib/api";
import { queryKeys } from "@/lib/queries";
import type {
  AIGenerateSmartGroupPayload,
  AIGenerateSmartPayload,
  BulkResponse,
  CreateGroupPayload,
  GroupBulkAddPayload,
  GroupBulkDeletePayload,
  GroupBulkUpdatePayload,
  GroupDetail,
  GroupMesocycleProgram,
  GroupSummary,
  ManualMesocycleGroupPayload,
  ManualMesocyclePayload,
  MessageResponse,
  PlanCreatePayload,
  PlanSetCreatePayload,
  PlanSummary,
  RegisterAthletePayload,
  SetCreatePayload,
  SetUpdatePayload,
  User,
} from "@/lib/types";

export const coachKeys = {
  athletes: ["athletes"] as const,
  groups: ["groups"] as const,
  group: (id: string) => ["group", id] as const,
  groupMesocycles: (id: string) => ["group-mesocycles", id] as const,
  myPlans: ["plans", "mine"] as const,
};

// ------------------------------------------------------------------- atletas

export function useAthletes(): UseQueryResult<User[]> {
  return useQuery({
    queryKey: coachKeys.athletes,
    queryFn: () => apiFetch<User[]>("/users/athletes"),
  });
}

/** Busca un atleta ya registrado por correo EXACTO — para agregar a un grupo a alguien que se
 *  auto-registró por su cuenta (GET /users/athletes solo devuelve "tus" atletas, así que ese
 *  atleta no aparece ahí hasta que lo agregues). Es una mutation (no query) porque se dispara
 *  a demanda con un botón, no automáticamente al montar el componente. */
export function useSearchAthleteByEmail() {
  return useMutation({
    mutationFn: (email: string) => apiFetch<User>(`/users/search?email=${encodeURIComponent(email.trim())}`),
  });
}

export function useRegisterAthlete() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (body: RegisterAthletePayload) =>
      apiFetch<MessageResponse>("/auth/register", { method: "POST", body }),
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: coachKeys.athletes }),
  });
}

// -------------------------------------------------------------------- grupos

export function useGroups(): UseQueryResult<GroupSummary[]> {
  return useQuery({ queryKey: coachKeys.groups, queryFn: () => apiFetch<GroupSummary[]>("/groups/") });
}

export function useGroupDetail(groupId: string | undefined): UseQueryResult<GroupDetail> {
  return useQuery({
    queryKey: coachKeys.group(groupId ?? "none"),
    queryFn: () => apiFetch<GroupDetail>(`/groups/${groupId}`),
    enabled: Boolean(groupId),
  });
}

export function useCreateGroup() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (body: CreateGroupPayload) => apiFetch<GroupDetail>("/groups/", { method: "POST", body }),
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: coachKeys.groups }),
  });
}

export function useAddGroupMembers(groupId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (athleteIds: string[]) =>
      apiFetch<GroupDetail>(`/groups/${groupId}/members`, { method: "POST", body: { athlete_ids: athleteIds } }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: coachKeys.group(groupId) });
      void queryClient.invalidateQueries({ queryKey: coachKeys.groups });
      void queryClient.invalidateQueries({ queryKey: coachKeys.groupMesocycles(groupId) });
    },
  });
}

export function useRemoveGroupMember(groupId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (userId: string) =>
      apiFetch<GroupDetail>(`/groups/${groupId}/members/${userId}`, { method: "DELETE" }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: coachKeys.group(groupId) });
      void queryClient.invalidateQueries({ queryKey: coachKeys.groups });
    },
  });
}

export function useDeleteGroup() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (groupId: string) => apiFetch<MessageResponse>(`/groups/${groupId}`, { method: "DELETE" }),
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: coachKeys.groups }),
  });
}

export function useGroupMesocycles(groupId: string | undefined): UseQueryResult<GroupMesocycleProgram[]> {
  return useQuery({
    queryKey: coachKeys.groupMesocycles(groupId ?? "none"),
    queryFn: () => apiFetch<GroupMesocycleProgram[]>(`/groups/${groupId}/mesocycles`),
    enabled: Boolean(groupId),
  });
}

// ------------------------------------------------- edición masiva de grupo

export function useGroupBulkAdd(groupId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (body: GroupBulkAddPayload) =>
      apiFetch<BulkResponse>(`/groups/${groupId}/sessions/bulk-add-exercise`, { method: "POST", body }),
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: ["mesocycle"] }),
  });
}

export function useGroupBulkUpdate(groupId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (body: GroupBulkUpdatePayload) =>
      apiFetch<BulkResponse>(`/groups/${groupId}/sessions/bulk-update-exercise`, { method: "PUT", body }),
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: ["mesocycle"] }),
  });
}

export function useGroupBulkDelete(groupId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (body: GroupBulkDeletePayload) =>
      apiFetch<BulkResponse>(`/groups/${groupId}/sessions/bulk-delete-exercise`, { method: "POST", body }),
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: ["mesocycle"] }),
  });
}

// ------------------------------------------------------------- mesociclos

export function useCreateManualMesocycle() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (body: ManualMesocyclePayload) =>
      apiFetch<{ message: string; mesocycle_id: string; total_sessions: number }>("/mesocycles/manual", {
        method: "POST",
        body,
      }),
    onSuccess: (_data, vars) =>
      void queryClient.invalidateQueries({ queryKey: queryKeys.mesocycles(vars.user_id) }),
  });
}

export function useCreateManualMesocycleForGroup(groupId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    // La forma real de `results` aquí es distinta a BulkResponse (trae mesocycle_id/total_sessions,
    // no status) — solo se usa `.message`, así que MessageResponse basta.
    mutationFn: (body: ManualMesocycleGroupPayload) =>
      apiFetch<MessageResponse>("/mesocycles/manual/group", { method: "POST", body }),
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: coachKeys.groupMesocycles(groupId) }),
  });
}

export function useGenerateAIMesocycle() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (body: AIGenerateSmartPayload) =>
      apiFetch<MessageResponse>("/ai/generate-smart-mesocycle/", { method: "POST", body }),
    onSuccess: (_data, vars) =>
      void queryClient.invalidateQueries({ queryKey: queryKeys.mesocycles(vars.user_id) }),
  });
}

export function useGenerateAIMesocycleForGroup(groupId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (body: AIGenerateSmartGroupPayload) =>
      apiFetch<BulkResponse>("/ai/generate-smart-mesocycle/group", { method: "POST", body }),
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: coachKeys.groupMesocycles(groupId) }),
  });
}

// -------------------------------------------------- edición de series (coach)

export function useAddSet(mesocycleId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ sessionId, body }: { sessionId: string; body: SetCreatePayload }) =>
      apiFetch<MessageResponse>(`/sessions/${sessionId}/sets/`, { method: "POST", body }),
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: queryKeys.mesocycle(mesocycleId) }),
  });
}

export function useUpdateSet(mesocycleId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ setId, body }: { setId: string; body: SetUpdatePayload }) =>
      apiFetch<unknown>(`/sets/${setId}`, { method: "PUT", body }),
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: queryKeys.mesocycle(mesocycleId) }),
  });
}

export function useDeleteSet(mesocycleId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (setId: string) => apiFetch<MessageResponse>(`/sets/${setId}`, { method: "DELETE" }),
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: queryKeys.mesocycle(mesocycleId) }),
  });
}

// ----------------------------------------------------------- planes (coach)

export function useMyPlans(): UseQueryResult<PlanSummary[]> {
  return useQuery({ queryKey: coachKeys.myPlans, queryFn: () => apiFetch<PlanSummary[]>("/plans/mine") });
}

export function useCreatePlan() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (body: PlanCreatePayload) => apiFetch<PlanSummary>("/plans/", { method: "POST", body }),
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: coachKeys.myPlans }),
  });
}

export function usePublishPlan() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ planId, isPublished }: { planId: string; isPublished: boolean }) =>
      apiFetch<PlanSummary>(`/plans/${planId}/publish`, { method: "PUT", body: { is_published: isPublished } }),
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: coachKeys.myPlans }),
  });
}

export function useDeletePlan() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (planId: string) => apiFetch<MessageResponse>(`/plans/${planId}`, { method: "DELETE" }),
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: coachKeys.myPlans }),
  });
}

export function useAddPlanSet(planId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ sessionId, body }: { sessionId: string; body: PlanSetCreatePayload }) =>
      apiFetch<MessageResponse>(`/plans/${planId}/sessions/${sessionId}/sets`, { method: "POST", body }),
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: queryKeys.plan(planId) }),
  });
}

export function useDeletePlanSet(planId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (setId: string) =>
      apiFetch<MessageResponse>(`/plans/${planId}/sets/${setId}`, { method: "DELETE" }),
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: queryKeys.plan(planId) }),
  });
}
