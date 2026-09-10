import { useProtectedImageUrl } from "@/lib/useImageUrl";

/**
 * Descarga la foto de perfil (protegida por JWT) y la expone como un object URL local.
 * Delgado sobre useProtectedImageUrl — ver ahí el porqué (headers, revocación de object URLs).
 */
export function useAvatarUrl(userId: string, hasAvatar: boolean, version = 0): string | null {
  return useProtectedImageUrl(`/users/${userId}/avatar`, hasAvatar, version);
}
