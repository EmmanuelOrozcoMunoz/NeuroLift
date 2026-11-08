import { useQuery } from "@tanstack/react-query";
import type { UseQueryResult } from "@tanstack/react-query";

import { apiFetch } from "@/lib/api";
import { useAuth } from "@/lib/auth";

/** GET /users/me/groups: un grupo al que pertenece el atleta. */
export interface MyGroup {
  id: string;
  name: string;
  coach_name: string | null;
  has_cover_image: boolean;
}

/** Los grupos del atleta que tiene la sesión abierta. Solo se piden para un atleta: coach y dueño no los necesitan. */
export function useMyGroups(): UseQueryResult<MyGroup[]> {
  const { user } = useAuth();
  return useQuery({
    queryKey: ["my-groups", user?.id],
    queryFn: () => apiFetch<MyGroup[]>("/users/me/groups"),
    enabled: user?.role === "athlete",
    staleTime: 5 * 60 * 1000,
  });
}
