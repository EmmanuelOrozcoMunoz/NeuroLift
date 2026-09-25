import { useState } from "react";

import { IconDownload, IconShare } from "@/components/icons";
import { Button, Card, cx } from "@/components/ui";
import { useInstallPrompt } from "@/lib/pwa";

/** Pasos de "Agregar a inicio" en Safari: iOS no permite abrir un diálogo de instalación. */
function IOSSteps({ className }: { className?: string }) {
  return (
    <ol className={cx("space-y-2 text-sm text-muted", className)}>
      <li className="flex items-center gap-2">
        <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-brand-soft text-xs font-bold text-brand">
          1
        </span>
        <span>
          Toca <IconShare className="inline h-4 w-4 align-[-2px] text-fg" /> <b className="text-fg">Compartir</b> en
          la barra de Safari
        </span>
      </li>
      <li className="flex items-center gap-2">
        <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-brand-soft text-xs font-bold text-brand">
          2
        </span>
        <span>
          Elige <b className="text-fg">Agregar a inicio</b>
        </span>
      </li>
      <li className="flex items-center gap-2">
        <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-brand-soft text-xs font-bold text-brand">
          3
        </span>
        <span>Abre NeuroLift desde el ícono, como cualquier app</span>
      </li>
    </ol>
  );
}

/**
 * Botón principal de instalación (landing). Según el navegador: diálogo nativo, instrucciones
 * de iOS, o nada si ya está instalada / el navegador no permite instalar (ej. Firefox escritorio).
 */
export function InstallButton({ className }: { className?: string }) {
  const { installed, canPrompt, isIOS, promptInstall } = useInstallPrompt();
  const [showIOS, setShowIOS] = useState(false);

  if (installed) return null;

  if (canPrompt) {
    return (
      <Button full className={className} onClick={() => void promptInstall()}>
        <IconDownload className="h-5 w-5" />
        Instalar la app
      </Button>
    );
  }

  if (isIOS) {
    return (
      <div className={className}>
        <Button full onClick={() => setShowIOS((v) => !v)} aria-expanded={showIOS}>
          <IconDownload className="h-5 w-5" />
          Instalar en iPhone
        </Button>
        {showIOS && (
          <Card className="mt-3">
            <IOSSteps />
          </Card>
        )}
      </div>
    );
  }

  return null;
}

/** Tarjeta para el perfil: recuerda que se puede instalar si todavía se usa desde el navegador. */
export function InstallAppCard({ className }: { className?: string }) {
  const { installed, canPrompt, isIOS, promptInstall } = useInstallPrompt();

  if (installed || (!canPrompt && !isIOS)) return null;

  return (
    <Card className={className}>
      <div className="flex items-start gap-3">
        <img src="/pwa-64x64.png" alt="" className="h-11 w-11 shrink-0 rounded-xl" />
        <div className="min-w-0">
          <p className="font-bold">Instala NeuroLift</p>
          <p className="text-sm text-muted">Ábrela desde tu pantalla de inicio, a pantalla completa y más rápido.</p>
        </div>
      </div>
      {canPrompt ? (
        <Button full className="mt-3" onClick={() => void promptInstall()}>
          <IconDownload className="h-5 w-5" />
          Instalar
        </Button>
      ) : (
        <IOSSteps className="mt-3" />
      )}
    </Card>
  );
}
