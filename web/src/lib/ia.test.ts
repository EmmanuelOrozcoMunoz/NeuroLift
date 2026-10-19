import { describe, expect, it } from "vitest";

import { mensajeConAvisos } from "@/lib/ia";

describe("mensajeConAvisos", () => {
  it("sin avisos deja el mensaje como está", () => {
    expect(mensajeConAvisos("¡Listo!", [])).toBe("¡Listo!");
    expect(mensajeConAvisos("¡Listo!", undefined)).toBe("¡Listo!");
  });

  it("con pocos avisos los lista todos", () => {
    expect(mensajeConAvisos("¡Listo!", ["Back Squat: sin marca"])).toBe("¡Listo! Revisa: Back Squat: sin marca");
    expect(mensajeConAvisos("¡Listo!", ["uno", "dos"])).toBe("¡Listo! Revisa: uno · dos");
  });

  it("con muchos muestra los dos primeros y cuenta el resto", () => {
    expect(mensajeConAvisos("¡Listo!", ["uno", "dos", "tres", "cuatro"])).toBe("¡Listo! Revisa: uno · dos · y 2 aviso(s) más");
  });
});
