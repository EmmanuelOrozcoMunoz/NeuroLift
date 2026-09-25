import { useRegisterSW } from "virtual:pwa-register/react";

import { Button } from "@/components/ui";

// Una PWA instalada puede quedarse abierta días sin recargar: se revisa si hay versión nueva
// cada hora además de al abrir.
const UPDATE_CHECK_MS = 60 * 60 * 1000;

/**
 * Registra el service worker y avisa cuando hay una versión nueva. NUNCA recarga sola: si el
 * atleta está a media sesión, decide él cuándo actualizar (ver registerType en vite.config.ts).
 */
export function UpdatePrompt() {
  const {
    needRefresh: [needRefresh, setNeedRefresh],
    updateServiceWorker,
  } = useRegisterSW({
    onRegisteredSW(swUrl, registration) {
      if (!registration) return;
      setInterval(async () => {
        // Sin red, o con el SW a medio instalar, no tiene caso preguntar
        if (registration.installing || !navigator.onLine) return;
        try {
          const response = await fetch(swUrl, { cache: "no-store", headers: { "cache-control": "no-cache" } });
          if (response.status === 200) await registration.update();
        } catch {
          /* se reintenta en el siguiente intervalo */
        }
      }, UPDATE_CHECK_MS);
    },
  });

  if (!needRefresh) return null;

  return (
    // bottom-24: queda encima de la barra de navegación inferior del shell
    <div className="pointer-events-none fixed inset-x-0 bottom-24 z-50 flex justify-center px-4">
      <div
        role="status"
        className="pointer-events-auto flex w-full max-w-sm items-center gap-3 rounded-2xl border border-line bg-surface p-3 shadow-lg"
      >
        <p className="grow text-sm">
          <span className="block font-semibold">Hay una versión nueva</span>
          <span className="text-muted">Actualiza cuando termines lo que estás haciendo.</span>
        </p>
        <Button variant="ghost" className="min-h-10 px-3 text-sm" onClick={() => setNeedRefresh(false)}>
          Luego
        </Button>
        <Button className="min-h-10 px-3 text-sm" onClick={() => void updateServiceWorker(true)}>
          Actualizar
        </Button>
      </div>
    </div>
  );
}
