/**
 * Color de acento personalizable por box.
 *
 * Toda la UI usa el token `--color-brand` (bg-brand, text-brand, border-brand...), así que
 * cambiar esa variable en <html> recolorea la app entera sin recompilar. `--color-brand-soft`
 * se deriva sola en index.css; aquí se calcula `--color-on-brand` (texto encima del acento),
 * porque con un acento claro —amarillo, lima— el texto blanco dejaría de leerse.
 *
 * De dónde sale el acento, en orden de prioridad:
 *  1. `?acento=RRGGBB` en la URL — para demos: enseñarle a un box cómo se vería la app con su
 *     color sin tocar nada. Dura lo que la pestaña (sessionStorage), no se guarda para siempre.
 *  2. El acento del box del usuario (configurado por el dueño, llega en /auth/me). Se guarda en
 *     localStorage para pintarlo desde el primer frame en el siguiente arranque, antes de que
 *     responda la API — ver setBoxAccent, llamado desde AuthProvider.
 *  3. `VITE_BRAND_ACCENT` al compilar.
 *  4. El azul por defecto de index.css.
 *
 * Modo claro (lib/theme.ts): un acento pensado para fondo oscuro —amarillo, celeste— no se lee como texto
 * sobre blanco. En claro se usa la MISMA tonalidad y saturación con menos luminosidad, lo justo para llegar a
 * 4.5:1 sobre los grises claros y sobre su propio fondo suave. El color guardado de la cuenta no cambia: al
 * volver a oscuro se aplica tal cual (ver reaplicarAcento).
 */

export const DEFAULT_ACCENT = "#5b9cff";
const INK = "#121212"; // --color-ink: fondo de la app
const DEMO_KEY = "neurolift_demo_accent";
const BOX_KEY = "neurolift_box_accent";

function normalizeHex(value: string | null | undefined): string | null {
  const match = value?.trim().match(/^#?([0-9a-f]{6})$/i);
  return match ? `#${match[1].toLowerCase()}` : null;
}

/** Luminancia relativa WCAG 2.x */
function luminance(hex: string): number {
  const channels = [1, 3, 5].map((i) => {
    const c = parseInt(hex.slice(i, i + 2), 16) / 255;
    return c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4;
  });
  return 0.2126 * channels[0] + 0.7152 * channels[1] + 0.0722 * channels[2];
}

function contrast(a: string, b: string): number {
  const [hi, lo] = [luminance(a), luminance(b)].sort((x, y) => y - x);
  return (hi + 0.05) / (lo + 0.05);
}

// --- modo claro -----------------------------------------------------------------------------------------
const CLARO_FONDO = "#ebebeb"; // --color-ink en claro: el gris más oscuro sobre el que va texto
const CLARO_SUAVE = 0.12; // --color-brand-soft en claro: 12 % del acento sobre el fondo
const MINIMO_TEXTO = 4.6; // 4.5:1 de AA, con un margen por la mezcla en oklab de index.css

function temaClaro(): boolean {
  return typeof document !== "undefined" && document.documentElement.dataset.theme === "light";
}

function hexARgb(hex: string): [number, number, number] {
  return [1, 3, 5].map((i) => parseInt(hex.slice(i, i + 2), 16) / 255) as [number, number, number];
}

function rgbAHex(r: number, g: number, b: number): string {
  return `#${[r, g, b].map((c) => Math.round(Math.min(1, Math.max(0, c)) * 255).toString(16).padStart(2, "0")).join("")}`;
}

/** El mismo color con `menos` puntos menos de luminosidad (HSL): conserva tono y saturación. */
function oscurecer(hex: string, menos: number): string {
  const [r, g, b] = hexARgb(hex);
  const max = Math.max(r, g, b), min = Math.min(r, g, b);
  let l = (max + min) / 2;
  const d = max - min;
  const s = d === 0 ? 0 : d / (1 - Math.abs(2 * l - 1));
  let h = 0;
  if (d !== 0) {
    if (max === r) h = ((g - b) / d) % 6;
    else if (max === g) h = (b - r) / d + 2;
    else h = (r - g) / d + 4;
  }
  h = (h * 60 + 360) % 360;
  l = Math.max(0, l - menos);
  const c = (1 - Math.abs(2 * l - 1)) * s;
  const x = c * (1 - Math.abs(((h / 60) % 2) - 1));
  const m = l - c / 2;
  const [r1, g1, b1] = h < 60 ? [c, x, 0] : h < 120 ? [x, c, 0] : h < 180 ? [0, c, x] : h < 240 ? [0, x, c] : h < 300 ? [x, 0, c] : [c, 0, x];
  return rgbAHex(r1 + m, g1 + m, b1 + m);
}

function mezclar(a: string, b: string, t: number): string {
  const [ra, ga, ba] = hexARgb(a), [rb, gb, bb] = hexARgb(b);
  return rgbAHex(ra * t + rb * (1 - t), ga * t + gb * (1 - t), ba * t + bb * (1 - t));
}

/** El acento listo para el modo claro: lo justo más oscuro para leerse como texto sobre los grises claros y
 *  sobre su propio fondo suave (chips, etiquetas). Exportado para las pruebas. */
export function acentoParaClaro(hex: string): string {
  for (let menos = 0; menos <= 1; menos += 0.01) {
    const candidato = oscurecer(hex, menos);
    if (
      contrast(candidato, CLARO_FONDO) >= MINIMO_TEXTO &&
      contrast(candidato, mezclar(candidato, CLARO_FONDO, CLARO_SUAVE)) >= MINIMO_TEXTO
    ) {
      return candidato;
    }
  }
  return "#000000";
}

/** El acento como se debe ver en el tema actual, o null si en oscuro no contrasta con el fondo. */
function acentoParaElTema(accent: string): string | null {
  if (temaClaro()) return acentoParaClaro(accent);
  return contrast(accent, INK) >= 3 ? accent : null;
}

/** El acento que pidió la cuenta (o la demo, o el .env), SIN ajustar al tema: se reaplica al cambiar de tema. */
let acentoPedido: string | null = null;

/**
 * Texto blanco mientras se lea (3:1, el mínimo de WCAG para texto en negrita y componentes de
 * UI — los botones van en semibold); con acentos más claros, texto oscuro.
 */
function textOn(accent: string): string {
  return contrast(accent, "#ffffff") >= 3 ? "#ffffff" : INK;
}

/** Variables CSS para previsualizar un acento SOLO dentro de un contenedor (style={...}), sin
 *  aplicarlo a toda la app. null si el color no sirve (formato o contraste, igual que applyAccent). */
export function accentPreviewVars(value: string): Record<string, string> | null {
  const accent = normalizeHex(value);
  const visible = accent ? acentoParaElTema(accent) : null;
  if (!visible) return null;
  return { "--color-brand": visible, "--color-on-brand": textOn(visible) };
}

/**
 * Aplica un acento a toda la app. Devuelve false (y deja el actual) si el color no sirve:
 * formato inválido, o tan oscuro que sobre el fondo carbón no se distinguiría — el acento
 * también se usa como color de texto (text-brand) y de la pestaña activa.
 */
export function applyAccent(value: string): boolean {
  const accent = normalizeHex(value);
  if (!accent) return false;
  const visible = acentoParaElTema(accent);
  if (!visible) {
    console.warn(`[brand] El acento ${accent} casi no contrasta con el fondo; se mantiene el actual.`);
    return false;
  }
  const root = document.documentElement.style;
  root.setProperty("--color-brand", visible);
  root.setProperty("--color-on-brand", textOn(visible));
  acentoPedido = accent;
  return true;
}

/** Vuelve a aplicar el acento de la cuenta con el ajuste del tema actual (lo llama lib/theme.ts al cambiar de tema). */
export function reaplicarAcento() {
  const pedido = acentoPedido;
  if (!pedido || !applyAccent(pedido)) resetAccent();
}

/** Vuelve al acento por defecto (el de VITE_BRAND_ACCENT o el azul de index.css). */
function resetAccent() {
  const root = document.documentElement.style;
  root.removeProperty("--color-brand");
  root.removeProperty("--color-on-brand");
  acentoPedido = null;
  const envAccent = normalizeHex(import.meta.env.VITE_BRAND_ACCENT as string | undefined);
  if (envAccent && envAccent !== DEFAULT_ACCENT) applyAccent(envAccent);
}

/**
 * Aplica el acento del box del usuario (o lo quita con null: logout, box sin acento propio) y
 * lo recuerda para el próximo arranque. Una demo con ?acento= activa en la pestaña manda.
 */
export function setBoxAccent(value: string | null) {
  const accent = normalizeHex(value);
  safeSession(() => (accent ? localStorage.setItem(BOX_KEY, accent) : localStorage.removeItem(BOX_KEY)));
  if (safeSession(() => sessionStorage.getItem(DEMO_KEY))) return;
  if (!accent || !applyAccent(accent)) resetAccent();
}

function safeSession<T>(fn: () => T): T | null {
  try {
    return fn();
  } catch {
    return null; // almacenamiento bloqueado: la demo simplemente no persiste entre recargas
  }
}

/** Se llama una vez, antes del primer render, para que no parpadee el color por defecto. */
export function initAccent() {
  const fromUrl = new URLSearchParams(window.location.search).get("acento");
  // Un ?acento= inválido o rechazado no se guarda: no debe "pegarse" al resto de la sesión
  if (fromUrl && applyAccent(fromUrl)) {
    safeSession(() => sessionStorage.setItem(DEMO_KEY, normalizeHex(fromUrl)!));
    return;
  }
  const candidates = [
    safeSession(() => sessionStorage.getItem(DEMO_KEY)),
    safeSession(() => localStorage.getItem(BOX_KEY)),
    import.meta.env.VITE_BRAND_ACCENT as string | undefined,
  ];
  for (const candidate of candidates) {
    const accent = normalizeHex(candidate);
    if (accent === DEFAULT_ACCENT) return;
    if (accent && applyAccent(accent)) return;
  }
}
