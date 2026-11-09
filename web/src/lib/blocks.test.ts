import { describe, expect, it } from "vitest";

import { blockLabel, clavePersonalizada, esBloquePersonalizado } from "@/lib/blocks";
import { bloquesConTexto, groupByBlock } from "@/lib/sessions";
import type { TrainingSession } from "@/lib/types";

describe("bloques con nombre propio", () => {
  it("la clave se arma con el nombre que escribió el usuario", () => {
    expect(clavePersonalizada("Activación")).toBe("x:Activación");
    expect(clavePersonalizada("  Finisher   2 ")).toBe("x:Finisher 2");
  });

  it("las comas y los signos < > se cambian por espacios (romperían el orden y el HTML)", () => {
    expect(clavePersonalizada("A,B")).toBe("x:A B");
    expect(clavePersonalizada("<b>Core</b>")).toBe("x:b Core /b");
  });

  it("un nombre vacío o demasiado largo no vale", () => {
    expect(clavePersonalizada("   ")).toBeNull();
    expect(clavePersonalizada("a".repeat(31))).toBeNull();
    expect(clavePersonalizada("a".repeat(30))).toBe(`x:${"a".repeat(30)}`);
  });

  it("el bloque sale con su nombre, y los de siempre conservan el suyo", () => {
    expect(blockLabel("x:Activación")).toBe("Activación");
    expect(blockLabel("strength")).toBe("Fuerza");
    expect(esBloquePersonalizado("x:Core")).toBe(true);
    expect(esBloquePersonalizado("strength")).toBe(false);
    expect(esBloquePersonalizado("x:")).toBe(false);
  });
});

describe("bloques con nombre propio dentro del día", () => {
  it("salen una sola vez, en el lugar del orden guardado, y con su nombre", () => {
    const grupos = groupByBlock([], "x:Activación,strength", ["strength", "x:Activación", "x:Core"]);
    expect(grupos.map((g) => g.key)).toEqual(["x:Activación", "strength", "x:Core"]);
    expect(grupos.map((g) => g.label)).toEqual(["Activación", "Fuerza", "Core"]);
  });

  it("sin orden guardado van después de los bloques de siempre", () => {
    const grupos = groupByBlock([], null, ["x:Core", "strength"]);
    expect(grupos.map((g) => g.key)).toEqual(["strength", "x:Core"]);
  });

  it("cuentan como contenido y aparecen aunque no estén en el orden guardado", () => {
    const sesion = { sets: [], block_notes: { "x:Core": "plancha", strength: "Back Squat" }, block_order: null } as unknown as TrainingSession;
    expect(bloquesConTexto(sesion)).toEqual(["Fuerza", "Core"]);
  });
});
