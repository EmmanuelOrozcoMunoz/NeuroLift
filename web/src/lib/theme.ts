import { useSyncExternalStore } from "react";

import { reaplicarAcento } from "@/lib/brand";

/**
 * Tema de la app: oscuro (por defecto, pensado para el gimnasio), claro, o automático (el del sistema).
 *
 * Es una preferencia del DISPOSITIVO (localStorage), no de la cuenta: en el celular del gimnasio puede
 * querer oscuro y en el computador de la oficina claro. Se aplica con `data-theme="light"` en <html>: index.css
 * redefine los mismos tokens (bg-surface, text-fg...) con valores claros, así ningún componente cambia.
 *
 * index.html lo aplica con un script en línea ANTES de pintar (sin parpadeo); aquí se mantiene al día.
 */
export type Tema = "oscuro" | "claro" | "sistema";

const CLAVE = "neurolift_tema";
const COLOR_BARRA = { oscuro: "#121212", claro: "#f5f5f5" } as const; // <meta name="theme-color">

const oyentes = new Set<() => void>();
let consultaSistema: MediaQueryList | null = null;

export function leerTema(): Tema {
  try {
    const guardado = localStorage.getItem(CLAVE);
    return guardado === "claro" || guardado === "sistema" ? guardado : "oscuro";
  } catch {
    return "oscuro";
  }
}

function sistemaEsClaro(): boolean {
  return typeof window !== "undefined" && window.matchMedia?.("(prefers-color-scheme: light)").matches === true;
}

/** ¿Está la app en claro ahora mismo? (resuelve "sistema"). */
export function esClaro(): boolean {
  return document.documentElement.dataset.theme === "light";
}

function aplicar(tema: Tema) {
  const claro = tema === "claro" || (tema === "sistema" && sistemaEsClaro());
  const raiz = document.documentElement;
  if (claro) raiz.dataset.theme = "light";
  else delete raiz.dataset.theme;
  document.querySelector('meta[name="theme-color"]')?.setAttribute("content", claro ? COLOR_BARRA.claro : COLOR_BARRA.oscuro);
  // El acento de la cuenta se ajusta al tema (en claro se oscurece lo justo para leerse sobre blanco)
  reaplicarAcento();
}

function alCambiarElSistema() {
  if (leerTema() === "sistema") aplicar("sistema");
}

/** Se llama una vez, antes del primer render: aplica el tema guardado y escucha los cambios del sistema. */
export function initTema() {
  aplicar(leerTema());
  if (!consultaSistema && typeof window !== "undefined" && window.matchMedia) {
    consultaSistema = window.matchMedia("(prefers-color-scheme: light)");
    consultaSistema.addEventListener("change", alCambiarElSistema);
  }
}

export function setTema(tema: Tema) {
  try {
    localStorage.setItem(CLAVE, tema);
  } catch {
    // sin almacenamiento (modo privado): se aplica igual, solo no se recuerda
  }
  aplicar(tema);
  oyentes.forEach((avisar) => avisar());
}

/** El tema elegido (oscuro/claro/sistema), para el selector del perfil. */
export function useTema(): Tema {
  return useSyncExternalStore(
    (avisar) => {
      oyentes.add(avisar);
      return () => oyentes.delete(avisar);
    },
    leerTema,
    () => "oscuro",
  );
}
