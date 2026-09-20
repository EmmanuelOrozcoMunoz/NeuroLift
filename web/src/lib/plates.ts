/** Discos estándar en kg, de mayor a menor — el orden en que se van cargando desde la barra
 *  hacia afuera (los más grandes primero, pegados a la barra, por estabilidad). */
const PLATE_DENOMINATIONS_KG = [25, 20, 15, 10, 5, 2.5, 1.25];

/** Escala entera (kg * 4) para hacer la resta con enteros y no arrastrar errores de
 *  punto flotante — el disco más chico (1.25kg) es exactamente 5 en esta escala. */
const SCALE = 4;

/** Colores estándar de discos de competencia (IWF/CrossFit) — el mismo código de colores
 *  que ya usan casi todos los boxes con discos de goma, sea cual sea la unidad en la que la
 *  app le muestra el peso al atleta (por eso el cálculo siempre trabaja en kg). */
export const PLATE_COLORS: Record<number, string> = {
  25: "#dc2626",
  20: "#2563eb",
  15: "#eab308",
  10: "#16a34a",
  5: "#f8fafc",
  2.5: "#111827",
  1.25: "#94a3b8",
};

/** Barra de 20kg (hombre) o 15kg (mujer) — el estándar de competencia IWF. null/sin dato
 *  usa 20kg por defecto. */
export function barWeightKg(sex: "male" | "female" | null | undefined): number {
  return sex === "female" ? 15 : 20;
}

export interface PlateBreakdown {
  barKg: number;
  /** Discos de UN lado, de mayor a menor (el primero va pegado a la barra). Vacío si el peso
   *  total no supera el de la barra sola. */
  perSide: number[];
  /** kg que sobran por lado sin poder representarse con los discos disponibles (0 = exacto). */
  remainderKg: number;
}

export function calculatePlates(totalKg: number, barKg: number): PlateBreakdown {
  const perSideScaled = Math.round(((totalKg - barKg) / 2) * SCALE);
  if (perSideScaled <= 0) {
    return { barKg, perSide: [], remainderKg: Math.max(0, -perSideScaled) / SCALE };
  }

  let remaining = perSideScaled;
  const perSide: number[] = [];
  for (const denom of PLATE_DENOMINATIONS_KG) {
    const scaledDenom = Math.round(denom * SCALE);
    while (remaining >= scaledDenom) {
      perSide.push(denom);
      remaining -= scaledDenom;
    }
  }

  return { barKg, perSide, remainderKg: remaining / SCALE };
}
