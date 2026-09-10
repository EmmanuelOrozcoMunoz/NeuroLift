import { useEffect, useState } from "react";

import { apiFetchBlob } from "@/lib/api";

/**
 * Descarga cualquier imagen protegida por JWT (avatar de usuario, portada de grupo, portada de
 * plan...) y la expone como un object URL local. Un <img src="..."> normal no sirve para estas
 * rutas: el navegador no le pondría el header Authorization.
 *
 * `version` es un contador que el llamador incrementa después de subir/borrar la imagen, para
 * forzar una nueva descarga aunque `hasImage` no haya cambiado de valor (reemplazar una imagen
 * por otra deja `hasImage` en `true` en ambos casos).
 */
export function useProtectedImageUrl(path: string | null, hasImage: boolean, version = 0): string | null {
  const [url, setUrl] = useState<string | null>(null);

  useEffect(() => {
    if (!hasImage || !path) {
      setUrl(null);
      return;
    }

    let cancelled = false;
    let objectUrl: string | null = null;

    void (async () => {
      try {
        const blob = await apiFetchBlob(path);
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
  }, [path, hasImage, version]);

  return url;
}
