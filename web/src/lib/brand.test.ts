import { readFileSync } from "node:fs";

import { describe, expect, it } from "vitest";

import { acentoParaClaro, DEFAULT_ACCENT } from "@/lib/brand";

function luminancia(hex: string): number {
  const [r, g, b] = [1, 3, 5].map((i) => {
    const c = parseInt(hex.slice(i, i + 2), 16) / 255;
    return c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4;
  });
  return 0.2126 * r + 0.7152 * g + 0.0722 * b;
}
function contraste(a: string, b: string): number {
  const [hi, lo] = [luminancia(a), luminancia(b)].sort((x, y) => y - x);
  return (hi + 0.05) / (lo + 0.05);
}

// Los colores que ofrece BoxHome, más el negro y el blanco puros como casos extremos
const ACENTOS = ["#5b9cff", "#ff4700", "#ef4444", "#f59e0b", "#facc15", "#84cc16", "#22c55e", "#14b8a6", "#38bdf8", "#e879f9"];

describe("acento en modo claro", () => {
  it.each(ACENTOS)("%s se lee como texto (AA) sobre los grises claros y lleva texto blanco legible encima", (acento) => {
    const claro = acentoParaClaro(acento);
    expect(contraste(claro, "#f0f0f0")).toBeGreaterThanOrEqual(4.5);
    expect(contraste(claro, "#ffffff")).toBeGreaterThanOrEqual(4.5);
  });

  it("un acento que ya es oscuro no se toca", () => {
    expect(acentoParaClaro("#1d4ed8")).toBe("#1d4ed8");
  });

  it("conserva el tono: el azul sigue siendo azul (el canal azul manda)", () => {
    const [r, g, b] = [1, 3, 5].map((i) => parseInt(acentoParaClaro("#5b9cff").slice(i, i + 2), 16));
    expect(b).toBeGreaterThan(r);
    expect(b).toBeGreaterThan(g);
  });

  it("el azul por defecto del modo claro en index.css es el mismo que calcula el código", () => {
    const css = readFileSync(new URL("../index.css", import.meta.url), "utf-8");
    const bloqueClaro = css.slice(css.indexOf(':root[data-theme="light"]'));
    const valor = bloqueClaro.match(/--color-brand:\s*(#[0-9a-f]{6})/i)?.[1];
    expect(valor?.toLowerCase()).toBe(acentoParaClaro(DEFAULT_ACCENT));
  });
});
