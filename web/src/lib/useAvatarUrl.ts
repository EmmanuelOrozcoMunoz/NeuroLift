import { useEffect, useState } from "react";

import { apiFetchBlob } from "@/lib/api";

/**
 * Descarga la foto de perfil (protegida por JWT, así que un <img src="..."> normal no sirve:
 * el navegador no le pondría el header Authorization) y la expone como un object URL local.
 *
 * `version` es un contador que el llamador incrementa después de subir/borrar la foto, para
 * forzar una nueva descarga aunque `hasAvatar` no haya cambiado de valor (reemplazar una foto
 * por otra deja `hasAvatar` en `true` en ambos casos).
 */
export function useAvatarUrl(userId: string, hasAvatar: boolean, version = 0): string | null {
  const [url, setUrl] = useState<string | null>(null);

  useEffect(() => {
    if (!hasAvatar) {
      setUrl(null);
      return;
    }

    let cancelled = false;
    let objectUrl: string | null = null;

    void (async () => {
      try {
        const blob = await apiFetchBlob(`/users/${userId}/avatar`);
        if (cancelled) return;
        objectUrl = URL.createObjectURL(blob);
        setUrl(objectUrl);
      } catch {
        if (!cancelled) setUrl(null);
      }
    })();

    return () => {
      cancelled = true;
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, [userId, hasAvatar, version]);

  return url;
}
