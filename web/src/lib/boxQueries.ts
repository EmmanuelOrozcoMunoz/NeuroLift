import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import type { UseQueryResult } from "@tanstack/react-query";

import { adminKeys } from "@/lib/adminQueries";
import { apiFetch, apiUpload } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { coachKeys } from "@/lib/coachQueries";
import type { AdminBoxRow, BoxDetail, BoxMember, BoxStatus, BoxUpdatePayload, MessageResponse, Role } from "@/lib/types";

export const boxKeys = {
  mine: ["box", "me"] as const,
  members: (role?: Role) => ["box", "members", role ?? "all"] as const,
  adminBoxes: ["admin", "boxes"] as const,
};

/** Perfil completo del box del usuario (el código de invitación solo llega a dueño/coaches). */
export function useMyBox(): UseQueryResult<BoxDetail> {
  return useQuery({ queryKey: boxKeys.mine, queryFn: () => apiFetch<BoxDetail>("/boxes/me") });
}

/** Tras cambiar nombre, acento o logo, /auth/me también trae el box: se refresca para que el
 *  acento y el nombre se apliquen en toda la app sin recargar. */
function useInvalidateBox() {
  const queryClient = useQueryClient();
  const { refreshUser } = useAuth();
  return (box?: BoxDetail) => {
    if (box) queryClient.setQueryData(boxKeys.mine, box);
    else void queryClient.invalidateQueries({ queryKey: boxKeys.mine });
    void refreshUser();
  };
}

export function useUpdateBox() {
  const invalidate = useInvalidateBox();
  return useMutation({
    mutationFn: (body: BoxUpdatePayload) => apiFetch<BoxDetail>("/boxes/me", { method: "PUT", body }),
    onSuccess: (box) => invalidate(box),
  });
}

export function useUploadBoxLogo() {
  const invalidate = useInvalidateBox();
  return useMutation({
    mutationFn: (file: File) => apiUpload<BoxDetail>("/boxes/me/logo", file),
    onSuccess: (box) => invalidate(box),
  });
}

export function useDeleteBoxLogo() {
  const invalidate = useInvalidateBox();
  return useMutation({
    mutationFn: () => apiFetch<MessageResponse>("/boxes/me/logo", { method: "DELETE" }),
    onSuccess: () => invalidate(),
  });
}

export function useRotateInviteCode() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => apiFetch<BoxDetail>("/boxes/me/invite-code", { method: "POST" }),
    onSuccess: (box) => queryClient.setQueryData(boxKeys.mine, box),
  });
}

export function useBoxMembers(role?: Role): UseQueryResult<BoxMember[]> {
  return useQuery({
    queryKey: boxKeys.members(role),
    queryFn: () => apiFetch<BoxMember[]>(role ? `/boxes/me/members?role=${role}` : "/boxes/me/members"),
  });
}

export function useCreateCoach() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (body: { full_name: string; email: string; password: string }) =>
      apiFetch<BoxMember>("/boxes/me/coaches", { method: "POST", body }),
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: ["box", "members"] }),
  });
}

export function useAssignCoach() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ athleteId, coachId }: { athleteId: string; coachId: string | null }) =>
      apiFetch<BoxMember>(`/boxes/me/athletes/${athleteId}/coach`, { method: "PUT", body: { coach_id: coachId } }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["box", "members"] });
      void queryClient.invalidateQueries({ queryKey: coachKeys.athletes });
    },
  });
}

// ------------------------------------------------------------ admin de plataforma

export function useAdminBoxes(): UseQueryResult<AdminBoxRow[]> {
  return useQuery({ queryKey: boxKeys.adminBoxes, queryFn: () => apiFetch<AdminBoxRow[]>("/admin/boxes") });
}

export function useUpdateBoxStatus() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ boxId, status }: { boxId: string; status: BoxStatus }) =>
      apiFetch<MessageResponse>(`/admin/boxes/${boxId}/status`, { method: "PUT", body: { status } }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: boxKeys.adminBoxes });
      void queryClient.invalidateQueries({ queryKey: adminKeys.overview });
    },
  });
}
