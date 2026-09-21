import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import type { UseQueryResult } from "@tanstack/react-query";

import { apiFetch } from "@/lib/api";
import { queryKeys } from "@/lib/queries";
import type {
  AIGenerateSmartGroupPayload,
  AIGenerateSmartPayload,
  AthleteActivity,
  BulkResponse,
  CreateGroupPayload,
  GroupBulkAddPayload,
  GroupBulkDeletePayload,
  GroupBulkUpdatePayload,
  GroupBulkWodFormatPayload,
  GroupBulkWodNotesPayload,
  GroupDetail,
  GroupMesocycleProgram,
  GroupProgramDeletePayload,
  GroupSummary,
  ManualMesocycleGroupPayload,
  ManualMesocyclePayload,
  MessageResponse,
  PlanCreatePayload,
  PlanSetCreatePayload,
  PlanSummary,
  PlanUpdatePayload,
  RegisterAthletePayload,
  SetCreatePayload,
  SetUpdatePayload,
  TrainingSession,
  User,
  WodDaySummary,
  WodFormatPayload,
  WodLeaderboardRow,
} from "@/lib/types";

export const coachKeys = {
  athletes: ["athletes"] as const,
  leaderboard: ["leaderboard"] as const,
  groups: ["groups"] as const,
  group: (id: string) => ["group", id] as const,
  groupMesocycles: (id: string) => ["group-mesocycles", id] as const,
  groupWodDays: (id: string) => ["group-wod-days", id] as const,
  groupWodLeaderboard: (id: string, date: string) => ["group-wod-leaderboard", id, date] as const,
  myPlans: ["plans", "mine"] as const,
};

// ------------------------------------------------------------------- atletas

export function useAthletes(): UseQueryResult<User[]> {
  return useQuery({
    queryKey: coachKeys.athletes,
    queryFn: () => apiFetch<User[]>("/users/athletes"),
  });
}

/** Tabla de posiciones: cuántos entrenamientos completó cada uno de tus atletas (con sus
 *  reps/pesos reales), ordenados por actividad de esta semana. */
export function useAthleteLeaderboard(): UseQueryResult<AthleteActivity[]> {
  return useQuery({
    queryKey: coachKeys.leaderboard,
    queryFn: () => apiFetch<AthleteActivity[]>("/coach/leaderboard"),
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

/** Elimina el programa completo (el mesociclo de CADA atleta del grupo para ese nombre+fecha),
 *  con sus sesiones y series — no solo un ejercicio suelto (ver useGroupBulkDelete). */
export function useDeleteGroupProgram(groupId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (body: GroupProgramDeletePayload) =>
      apiFetch<MessageResponse>(`/groups/${groupId}/mesocycles`, { method: "DELETE", body }),
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: coachKeys.groupMesocycles(groupId) }),
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

/** Fija (o quita) el formato de WOD y su timer/time cap para TODO el grupo a la vez, en una
 *  fecha dada — evita repetir la acción atleta por atleta cuando todos hacen el mismo WOD. */
export function useGroupBulkSetWodFormat(groupId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (body: GroupBulkWodFormatPayload) =>
      apiFetch<BulkResponse>(`/groups/${groupId}/sessions/bulk-set-wod-format`, { method: "POST", body }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["mesocycle"] });
      void queryClient.invalidateQueries({ queryKey: coachKeys.groupWodDays(groupId) });
    },
  });
}

/** Escribe (o borra) la descripción libre del WOD para TODO el grupo a la vez, en una fecha
 *  dada — mismo motivo que useGroupBulkSetWodFormat, para el bloque Metabólico/WOD. */
export function useGroupBulkSetWodNotes(groupId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (body: GroupBulkWodNotesPayload) =>
      apiFetch<BulkResponse>(`/groups/${groupId}/sessions/bulk-set-wod-notes`, { method: "POST", body }),
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: ["mesocycle"] }),
  });
}

/** Fechas del grupo con un WOD prescrito — para elegir cuál ver en la tabla de posiciones. */
export function useGroupWodDays(groupId: string | undefined): UseQueryResult<WodDaySummary[]> {
  return useQuery({
    queryKey: coachKeys.groupWodDays(groupId ?? "none"),
    queryFn: () => apiFetch<WodDaySummary[]>(`/groups/${groupId}/wod-days`),
    enabled: Boolean(groupId),
  });
}

/** Tabla de posiciones de UN WOD específico del grupo, ya ordenada por resultado real. */
export function useGroupWodLeaderboard(
  groupId: string | undefined,
  scheduledDate: string | undefined,
): UseQueryResult<WodLeaderboardRow[]> {
  return useQuery({
    queryKey: coachKeys.groupWodLeaderboard(groupId ?? "none", scheduledDate ?? "none"),
    queryFn: () =>
      apiFetch<WodLeaderboardRow[]>(
        `/groups/${groupId}/wod-leaderboard?scheduled_date=${encodeURIComponent(scheduledDate!)}`,
      ),
    enabled: Boolean(groupId && scheduledDate),
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

export function useDeleteMesocycle() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (mesocycleId: string) =>
      apiFetch<MessageResponse>(`/mesocycles/${mesocycleId}`, { method: "DELETE" }),
    onSuccess: (_data, mesocycleId) => {
      void queryClient.invalidateQueries({ queryKey: ["mesocycles"] });
      // Por si el mesociclo eliminado pertenecía a un programa de grupo, no solo al atleta.
      void queryClient.invalidateQueries({ queryKey: ["group-mesocycles"] });
      queryClient.removeQueries({ queryKey: queryKeys.mesocycle(mesocycleId) });
    },
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

/** Metadatos de la sesión aparte de sus series: orden de los bloques y pautas de calentamiento
 *  (ver PUT /sessions/{id}/meta). Cada campo se guarda solo si viene en el body. */
export function useUpdateSessionMeta(mesocycleId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      sessionId,
      body,
    }: {
      sessionId: string;
      body: { block_order?: string | null; warmup_notes?: string | null; wod_notes?: string | null };
    }) => apiFetch<TrainingSession>(`/sessions/${sessionId}/meta`, { method: "PUT", body }),
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

/** Edita nombre/descripción/disciplina/nivel/precio de un plan — funciona igual esté
 *  publicado o en borrador. */
export function useUpdatePlan(planId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (body: PlanUpdatePayload) => apiFetch<PlanSummary>(`/plans/${planId}`, { method: "PUT", body }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: coachKeys.myPlans });
      void queryClient.invalidateQueries({ queryKey: queryKeys.plan(planId) });
    },
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

/** Metadatos de un día del plan aparte de sus series -- hoy solo se usa para wod_notes (texto
 *  libre del bloque Metabólico/WOD). No reutiliza PUT /sessions/{id}/meta porque un plan no
 *  tiene dueño (Mesocycle.user_id=None) y ese endpoint general lo exige. */
export function useUpdatePlanSessionMeta(planId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      sessionId,
      body,
    }: {
      sessionId: string;
      body: { wod_notes?: string | null };
    }) => apiFetch<TrainingSession>(`/plans/${planId}/sessions/${sessionId}/meta`, { method: "PUT", body }),
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: queryKeys.plan(planId) }),
  });
}

/** Fija (o quita) el formato de WOD y su timer/time cap de un día del plan -- mismo motivo que
 *  useUpdatePlanSessionMeta arriba. */
export function useSetPlanSessionWodFormat(planId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ sessionId, body }: { sessionId: string; body: WodFormatPayload }) =>
      apiFetch<MessageResponse>(`/plans/${planId}/sessions/${sessionId}/wod-format`, { method: "PUT", body }),
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: queryKeys.plan(planId) }),
  });
}
