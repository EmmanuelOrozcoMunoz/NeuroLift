import { describe, expect, it } from "vitest";

import { estaVigente } from "@/lib/dates";

describe("estaVigente", () => {
  const hoy = "2026-10-06";

  it("un mesociclo cuya fecha final ya pasó no está vigente aunque is_active siga en true", () => {
    expect(estaVigente({ is_active: true, end_date: "2026-09-30" }, hoy)).toBe(false);
  });

  it("el último día todavía cuenta como vigente, y los días anteriores al fin también", () => {
    expect(estaVigente({ is_active: true, end_date: "2026-10-06" }, hoy)).toBe(true);
    expect(estaVigente({ is_active: true, end_date: "2026-10-14" }, hoy)).toBe(true);
  });

  it("sin fecha final (registro personal) no termina nunca", () => {
    expect(estaVigente({ is_active: true, end_date: null }, hoy)).toBe(true);
  });

  it("uno desactivado no está vigente por mucho que falte para su fecha final", () => {
    expect(estaVigente({ is_active: false, end_date: "2026-12-31" }, hoy)).toBe(false);
    expect(estaVigente({ is_active: false, end_date: null }, hoy)).toBe(false);
  });

  it("compara por fecha de calendario, también al cambiar de mes o de año", () => {
    expect(estaVigente({ is_active: true, end_date: "2026-10-06" }, "2026-10-07")).toBe(false);
    expect(estaVigente({ is_active: true, end_date: "2027-01-02" }, "2026-12-31")).toBe(true);
    expect(estaVigente({ is_active: true, end_date: "2026-12-31" }, "2027-01-01")).toBe(false);
  });
});
