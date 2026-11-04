import { describe, expect, it } from "vitest";

import { nombreCorto, soloElResultado } from "@/lib/rankingFormat";

describe("nombreCorto", () => {
  it("deja el primer nombre y la inicial del segundo", () => {
    expect(nombreCorto("Ana Demo Pérez")).toBe("Ana D.");
    expect(nombreCorto("beto ruiz")).toBe("beto R.");
  });

  it("con una sola palabra la deja igual, y tolera espacios de más", () => {
    expect(nombreCorto("Carla")).toBe("Carla");
    expect(nombreCorto("  Dani   Ruiz  ")).toBe("Dani R.");
    expect(nombreCorto("")).toBe("");
  });
});

describe("soloElResultado", () => {
  it("quita el nombre del formato", () => {
    expect(soloElResultado("Por tiempo: 3:05")).toBe("3:05");
    expect(soloElResultado("AMRAP: 5 rondas + 8 reps")).toBe("5 rondas + 8 reps");
    expect(soloElResultado("1RM: 100 kg")).toBe("100 kg");
  });

  it("deja igual lo que no trae formato y pone una raya si no hay resultado", () => {
    expect(soloElResultado("120 cal")).toBe("120 cal");
    expect(soloElResultado("500 m")).toBe("500 m");
    expect(soloElResultado(null)).toBe("—");
  });
});
