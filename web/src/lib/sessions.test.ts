import { describe, expect, it } from "vitest";

import {
  cargaDelGrupo,
  coincideConLoProgramado,
  entradasComoProgramado,
  entradasParaDeshacer,
  estadoDelGrupo,
  groupByBlock,
  groupSummary,
  gruposEnOrden,
  resumenRegistrado,
} from "@/lib/sessions";
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

describe("groupByBlock: bloques forzados (texto libre del WOD y del calentamiento)", () => {
  const con = (block: string | null, order: number) =>
    serie(5, { block, set_order: order, exercise: { id: `${block}-${order}`, name: `Ej ${order}`, category: null } });
  const claves = (g: ReturnType<typeof groupByBlock>) => g.map((b) => b.key);

  it("forzar el calentamiento crea el bloque aunque ningún ejercicio lo lleve, y queda primero", () => {
    const sets = [con("strength", 1), con("metcon", 2)];
    expect(claves(groupByBlock(sets, null, ["warmup"]))).toEqual(["warmup", "strength", "metcon"]);
    expect(groupByBlock(sets, null, ["warmup"])[0].groups).toEqual([]);
  });

  it("el bloque forzado sigue el orden guardado de la sesión, igual que los demás", () => {
    const sets = [con("strength", 1)];
    expect(claves(groupByBlock(sets, "strength,warmup", ["warmup"]))).toEqual(["strength", "warmup"]);
  });

  it("se pueden forzar varios a la vez, y forzar uno que ya existe no lo duplica", () => {
    const sets = [con("warmup", 1), con("strength", 2)];
    expect(claves(groupByBlock(sets, null, ["warmup", "metcon"]))).toEqual(["warmup", "strength", "metcon"]);
  });

  it("true sigue significando forzar el metabólico (como antes)", () => {
    const sets = [con("strength", 1)];
    expect(claves(groupByBlock(sets, null, true))).toEqual(["strength", "metcon"]);
  });

  it("sin nada forzado y sin bloques, una sesión vieja sigue siendo un solo grupo sin título", () => {
    const sets = [con(null, 1), con(null, 2)];
    expect(groupByBlock(sets, null)).toHaveLength(1);
    expect(groupByBlock(sets, null, [])[0]).toMatchObject({ key: null, label: "" });
    // y con un bloque forzado, los ejercicios sin bloque pasan a "Otros ejercicios"
    expect(claves(groupByBlock(sets, null, ["warmup"]))).toEqual(["warmup", null]);
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

describe("registro de un ejercicio completo", () => {
  const hecha = (reps: number, peso: number | null, extra: Partial<SetItem> = {}) =>
    serie(5, { prescribed_weight: 80, actual_reps: reps, actual_weight: peso, ...extra });

  it("estadoDelGrupo distingue pendiente, parcial y completo", () => {
    expect(estadoDelGrupo(grupo(serie(5), serie(5)))).toBe("pendiente");
    expect(estadoDelGrupo(grupo(hecha(5, 80), serie(5)))).toBe("parcial");
    expect(estadoDelGrupo(grupo(hecha(5, 80), hecha(5, 80)))).toBe("completo");
    // 0 reps es un registro (se intentó y no salió), no "pendiente"
    expect(estadoDelGrupo(grupo(hecha(0, 80)))).toBe("completo");
  });

  it("entradasComoProgramado usa lo prescrito y respeta las series ya anotadas", () => {
    const a = serie(5, { id: "a", prescribed_weight: 80 });
    const b = serie(3, { id: "b", prescribed_weight: 90, actual_reps: 2, actual_weight: 85 });
    const c = serie(8, { id: "c" }); // peso libre
    expect(entradasComoProgramado(grupo(a, b, c))).toEqual([
      { set_id: "a", actual_reps: 5, actual_weight: 80 },
      { set_id: "c", actual_reps: 8, actual_weight: null }, // sin peso prescrito: no se inventa 0 kg
    ]);
  });

  it("entradasParaDeshacer limpia todas las series", () => {
    const a = serie(5, { id: "a" });
    const b = serie(5, { id: "b", actual_reps: 5, actual_weight: 80 });
    expect(entradasParaDeshacer(grupo(a, b))).toEqual([
      { set_id: "a", actual_reps: null, actual_weight: null },
      { set_id: "b", actual_reps: null, actual_weight: null },
    ]);
  });

  it("coincideConLoProgramado es falso si algo cambió o falta una serie", () => {
    expect(coincideConLoProgramado(grupo(hecha(5, 80), hecha(5, 80)))).toBe(true);
    expect(coincideConLoProgramado(grupo(hecha(5, 80), hecha(4, 80)))).toBe(false); // menos reps
    expect(coincideConLoProgramado(grupo(hecha(5, 80), hecha(5, 85)))).toBe(false); // otro peso
    expect(coincideConLoProgramado(grupo(hecha(5, 80), serie(5, { prescribed_weight: 80 })))).toBe(false);
    expect(coincideConLoProgramado(grupo())).toBe(false);
    // peso libre: null y 0 son lo mismo
    expect(coincideConLoProgramado(grupo(serie(5, { actual_reps: 5, actual_weight: null })))).toBe(true);
  });

  it("en una sesión con WOD de peso (1RM) el registro normal no anota el peso programado", () => {
    // El resultado de ese WOD es el MAYOR peso anotado: anotar el programado inventaría una marca.
    const a = serie(1, { id: "a", prescribed_weight: 100 });
    const b = serie(1, { id: "b", prescribed_weight: 110 });
    expect(entradasComoProgramado(grupo(a, b), { sinPeso: true })).toEqual([
      { set_id: "a", actual_reps: 1, actual_weight: null },
      { set_id: "b", actual_reps: 1, actual_weight: null },
    ]);
    // lo registrado así cuenta como "como se programó" (un toque lo deshace)...
    const registradas = grupo(
      serie(1, { prescribed_weight: 100, actual_reps: 1, actual_weight: null }),
      serie(1, { prescribed_weight: 110, actual_reps: 1, actual_weight: null }),
    );
    expect(coincideConLoProgramado(registradas, { sinPeso: true })).toBe(true);
    // ...y sin la bandera no, porque el peso programado nunca se anotó
    expect(coincideConLoProgramado(registradas)).toBe(false);
    // si el atleta SÍ anotó un peso, es un registro propio: un toque no debe borrarlo
    const conPeso = grupo(serie(1, { prescribed_weight: 100, actual_reps: 1, actual_weight: 102.5 }));
    expect(coincideConLoProgramado(conPeso, { sinPeso: true })).toBe(false);
  });

  it("resumenRegistrado: series iguales o cada una con su peso", () => {
    expect(resumenRegistrado(grupo(hecha(5, 80), hecha(5, 80), hecha(5, 80)), "kg")).toBe("3 x 5 @ 80 kg");
    expect(resumenRegistrado(grupo(hecha(5, 80), hecha(3, 85)), "kg")).toBe("80 kg×5 · 85 kg×3");
    expect(resumenRegistrado(grupo(serie(5, { actual_reps: 10, actual_weight: null })), "kg")).toBe("1 x 10");
    // sin peso en ninguna serie: solo repeticiones
    expect(resumenRegistrado(grupo(serie(8, { actual_reps: 8 }), serie(8, { actual_reps: 5 })), "kg")).toBe("8 · 5 reps");
    expect(resumenRegistrado(grupo(serie(5)), "kg")).toBe("");
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
