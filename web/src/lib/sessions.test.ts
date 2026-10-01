import { describe, expect, it } from "vitest";

import { cargaDelGrupo, groupSummary, gruposEnOrden } from "@/lib/sessions";
import type { ExerciseGroup } from "@/lib/sessions";
import type { SetItem } from "@/lib/types";

function serie(reps: number, extra: Partial<SetItem> = {}): SetItem {
  return {
    id: `s-${reps}-${Math.random()}`,
    set_order: 1,
    block: null,
    prescribed_reps: reps,
    rpe: null,
    prescribed_weight: null,
    prescribed_percentage: null,
    reference_exercise: null,
    actual_reps: null,
    actual_weight: null,
    technique_feedback: null,
    exercise: { id: "e1", name: "Snatch", category: null },
    ...extra,
  };
}

const grupo = (...sets: SetItem[]): ExerciseGroup => ({ name: "Snatch", sets });

describe("groupSummary", () => {
  it("series iguales: 'N x reps @ carga'", () => {
    const g = grupo(serie(5, { prescribed_weight: 100 }), serie(5, { prescribed_weight: 100 }), serie(5, { prescribed_weight: 100 }));
    expect(groupSummary(g, "kg")).toBe("3 x 5 @ 100 kg");
  });

  it("una rampa lista cada serie con su carga y sus repeticiones", () => {
    const g = grupo(
      serie(3, { prescribed_percentage: 50 }),
      serie(3, { prescribed_percentage: 60 }),
      serie(1, { prescribed_percentage: 70 }),
      serie(1, { prescribed_percentage: 100 }),
    );
    expect(groupSummary(g, "kg")).toBe("50%×3 · 60%×3 · 70%×1 · 100%×1");
  });

  it("misma carga pero distintas repeticiones también se detalla", () => {
    const g = grupo(serie(5, { prescribed_weight: 80 }), serie(3, { prescribed_weight: 80 }));
    expect(groupSummary(g, "kg")).toBe("80 kg×5 · 80 kg×3");
  });

  it("un ejercicio sin series da texto vacío", () => {
    expect(groupSummary(grupo(), "kg")).toBe("");
  });
});

describe("gruposEnOrden", () => {
  const con = (name: string, block: string, order: number) =>
    serie(5, { block, set_order: order, exercise: { id: name, name, category: null } });
  const sets = [con("Sentadilla", "strength", 1), con("Fran", "metcon", 2), con("Movilidad", "warmup", 3)];

  it("sigue el orden de bloques de la sesión, no el de las series", () => {
    expect(gruposEnOrden(sets, "metcon,strength,warmup").map((g) => g.name)).toEqual(["Fran", "Sentadilla", "Movilidad"]);
  });

  it("sin orden guardado usa el orden canónico de bloques", () => {
    expect(gruposEnOrden(sets, null).map((g) => g.name)).toEqual(["Movilidad", "Sentadilla", "Fran"]);
  });

  it("sin bloques conserva el orden de las series", () => {
    const sinBloque = [serie(3, { set_order: 2, exercise: { id: "b", name: "B", category: null } }), serie(3, { set_order: 1 })];
    expect(gruposEnOrden(sinBloque, "metcon").map((g) => g.name)).toEqual(["Snatch", "B"]);
  });
});

describe("cargaDelGrupo", () => {
  it("series iguales: una sola cifra", () => {
    expect(cargaDelGrupo(grupo(serie(5, { prescribed_weight: 100 }), serie(5, { prescribed_weight: 100 })), "kg")).toEqual({ value: "100", unit: "kg" });
  });

  it("una rampa muestra el rango y no solo la primera serie", () => {
    const g = grupo(serie(2, { prescribed_weight: 60 }), serie(2, { prescribed_weight: 80 }), serie(2, { prescribed_weight: 97.5 }));
    expect(cargaDelGrupo(g, "kg")).toEqual({ value: "60–97.5", unit: "kg" });
  });

  it("una serie anotada muestra el peso real, no el prescrito", () => {
    const hecha = serie(2, { prescribed_weight: 97.5, actual_reps: 2, actual_weight: 74 });
    expect(cargaDelGrupo(grupo(hecha), "kg")).toEqual({ value: "74", unit: "kg" });
    // sin anotar sigue la prescripción
    expect(cargaDelGrupo(grupo(serie(2, { prescribed_weight: 97.5, actual_weight: 74 })), "kg")).toEqual({ value: "97.5", unit: "kg" });
  });

  it("porcentajes en rampa y sin carga", () => {
    expect(cargaDelGrupo(grupo(serie(3, { prescribed_percentage: 60 }), serie(3, { prescribed_percentage: 75 })), "kg")).toEqual({ value: "60–75", unit: "%" });
    expect(cargaDelGrupo(grupo(serie(10)), "kg")).toBeNull();
  });
});

describe("al reordenar los bloques cada ejercicio conserva su propia prescripción", () => {
  const ejercicio = (nombre: string, block: string, order: number, extra: Partial<SetItem>) =>
    serie(2, { block, set_order: order, exercise: { id: nombre, name: nombre, category: null }, ...extra });
  const sets = [
    ejercicio("Back Squat", "strength", 1, { prescribed_weight: 100, prescribed_percentage: 80, reference_exercise: "Back Squat" }),
    ejercicio("Power clean", "weightlifting", 2, { prescribed_weight: 97.5, prescribed_percentage: 78, reference_exercise: "Back Squat" }),
  ];
  const resumenes = (orden: string) =>
    gruposEnOrden(sets, orden).map((g) => [g.name, groupSummary(g, "kg")]);

  it("el resumen de cada tarjeta sale de sus propias series, en cualquier orden", () => {
    expect(resumenes("strength,weightlifting")).toEqual([
      ["Back Squat", "1 x 2 @ 100 kg (80%)"],
      ["Power clean", "1 x 2 @ 97.5 kg (78%)"],
    ]);
    expect(resumenes("weightlifting,strength")).toEqual([
      ["Power clean", "1 x 2 @ 97.5 kg (78%)"],
      ["Back Squat", "1 x 2 @ 100 kg (80%)"],
    ]);
  });
});
