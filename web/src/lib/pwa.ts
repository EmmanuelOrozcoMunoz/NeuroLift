import { useEffect, useState } from "react";

/**
 * Instalación de la PWA.
 *
 * Chrome/Edge/Android disparan `beforeinstallprompt` UNA vez, muy temprano (a veces antes de
 * que React monte la pantalla que muestra el botón). Por eso el listener se registra al cargar
 * este módulo —se importa desde main.tsx— y el evento se guarda aquí hasta que alguien lo use.
 *
 * iOS/Safari no tiene ese evento: ahí solo se puede instalar a mano (Compartir → "Agregar a
 * inicio"), así que la UI muestra instrucciones en vez de un botón.
 */

interface BeforeInstallPromptEvent extends Event {
  prompt(): Promise<void>;
  userChoice: Promise<{ outcome: "accepted" | "dismissed" }>;
}

let deferredPrompt: BeforeInstallPromptEvent | null = null;
const listeners = new Set<() => void>();
const notify = () => listeners.forEach((listener) => listener());

if (typeof window !== "undefined") {
  window.addEventListener("beforeinstallprompt", (event) => {
    // Evita la mini-barra automática de Chrome: la instalación se ofrece desde la landing y el perfil
    event.preventDefault();
    deferredPrompt = event as BeforeInstallPromptEvent;
    notify();
  });
  window.addEventListener("appinstalled", () => {
    deferredPrompt = null;
    notify();
  });
}

/** La app corre instalada (abierta desde el ícono), no en una pestaña del navegador. */
export function isStandalone(): boolean {
  if (typeof window === "undefined") return false;
  return (
    window.matchMedia("(display-mode: standalone)").matches ||
    // Safari de iOS no soporta display-mode en todas las versiones: usa su propia bandera
    (navigator as Navigator & { standalone?: boolean }).standalone === true
  );
}

function detectIOS(): boolean {
  const ua = navigator.userAgent;
  // iPadOS 13+ se presenta como Mac: se distingue por la pantalla táctil
  return /iPad|iPhone|iPod/.test(ua) || (ua.includes("Macintosh") && navigator.maxTouchPoints > 1);
}

export interface InstallState {
  /** Ya está instalada y abierta como app: no hay nada que ofrecer. */
  installed: boolean;
  /** Hay un prompt nativo listo (Chrome/Edge/Android). */
  canPrompt: boolean;
  /** iOS: no hay prompt nativo, hay que mostrar las instrucciones de "Agregar a inicio". */
  isIOS: boolean;
  /** Abre el diálogo nativo. Devuelve true si el usuario aceptó. */
  promptInstall: () => Promise<boolean>;
}

export function useInstallPrompt(): InstallState {
  const [, force] = useState(0);
  const [installed, setInstalled] = useState(isStandalone);

  useEffect(() => {
    const listener = () => {
      force((n) => n + 1);
      if (!deferredPrompt && isStandalone()) setInstalled(true);
    };
    listeners.add(listener);
    return () => {
      listeners.delete(listener);
    };
  }, []);

  async function promptInstall(): Promise<boolean> {
    const event = deferredPrompt;
    if (!event) return false;
    await event.prompt();
    const { outcome } = await event.userChoice;
    // El evento solo sirve una vez, se acepte o no
    deferredPrompt = null;
    notify();
    return outcome === "accepted";
  }

  return {
    installed,
    canPrompt: deferredPrompt !== null,
    isIOS: detectIOS(),
    promptInstall,
  };
}
