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
 *  2. `VITE_BRAND_ACCENT` al compilar — una instalación por box.
 *  3. El naranja por defecto de index.css.
 * Cuando el acento viva en el backend (configuración del box), `applyAccent` es el punto de
 * entrada: se llama con el valor que devuelva la API.
 */

export const DEFAULT_ACCENT = "#ff4700";
const INK = "#121212"; // --color-ink: fondo de la app
const DEMO_KEY = "neurolift_demo_accent";

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

/**
 * Texto blanco mientras se lea (3:1, el mínimo de WCAG para texto en negrita y componentes de
 * UI — los botones van en semibold); con acentos más claros, texto oscuro.
 */
function textOn(accent: string): string {
  return contrast(accent, "#ffffff") >= 3 ? "#ffffff" : INK;
}

/**
 * Aplica un acento a toda la app. Devuelve false (y deja el actual) si el color no sirve:
 * formato inválido, o tan oscuro que sobre el fondo carbón no se distinguiría — el acento
 * también se usa como color de texto (text-brand) y de la pestaña activa.
 */
export function applyAccent(value: string): boolean {
  const accent = normalizeHex(value);
  if (!accent) return false;
  if (contrast(accent, INK) < 3) {
    console.warn(`[brand] El acento ${accent} casi no contrasta con el fondo; se mantiene el actual.`);
    return false;
  }
  const root = document.documentElement.style;
  root.setProperty("--color-brand", accent);
  root.setProperty("--color-on-brand", textOn(accent));
  return true;
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
    import.meta.env.VITE_BRAND_ACCENT as string | undefined,
  ];
  for (const candidate of candidates) {
    const accent = normalizeHex(candidate);
    if (accent === DEFAULT_ACCENT) return;
    if (accent && applyAccent(accent)) return;
  }
}
