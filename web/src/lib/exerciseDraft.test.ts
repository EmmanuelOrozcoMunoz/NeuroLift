import { describe, expect, it } from "vitest";

import {
  camposComunes,
  camposDeFila,
  cargaParaEnviar,
  conNumeroDeSeries,
  draftDeEjercicio,
  esUniforme,
  firmaDeEjercicio,
  nuevoDraft,
  pesosWodParaEnviar,
  seriesParaEnviar,
} from "@/lib/exerciseDraft";
import type { ExerciseGroup } from "@/lib/sessions";
import type { SetItem } from "@/lib/types";

function serie(sobre: Partial<SetItem> = {}): SetItem {
  return {
    id: "s1",
    set_order: 1,
    block: null,
    prescribed_reps: 5,
    rpe: null,
    prescribed_weight: null,
    prescribed_percentage: null,
    reference_exercise: null,
    actual_reps: null,
    actual_weight: null,
    technique_feedback: null,
    exercise: { id: "e1", name: "Back Squat", category: null },
    ...sobre,
  };
}

const grupo = (...series: SetItem[]): ExerciseGroup => ({ name: "Back Squat", sets: series });

describe("nuevoDraft", () => {
  it("crea N filas iguales con los valores dados", () => {
    const d = nuevoDraft({ series: 4, reps: 5, tipo: "porcentaje", porcentaje: 80 });
    expect(d.filas).toHaveLength(4);
    expect(d.filas.every((f) => f.reps === 5 && f.porcentaje === 80)).toBe(true);
  });

  it("por defecto son 3 series de 8", () => {
    const d = nuevoDraft();
    expect(d.filas).toEqual([
      { reps: 8, weight: 0, porcentaje: 75 },
      { reps: 8, weight: 0, porcentaje: 75 },
      { reps: 8, weight: 0, porcentaje: 75 },
    ]);
  });
});

describe("cargaParaEnviar", () => {
  it("kg fijos: manda el peso solo si es mayor que 0", () => {
    expect(cargaParaEnviar(nuevoDraft({ tipo: "kg", weight: 80 }))).toEqual({
      prescribed_weight: 80,
      prescribed_percentage: null,
      reference_exercise: null,
    });
    expect(cargaParaEnviar(nuevoDraft({ tipo: "kg", weight: 0 })).prescribed_weight).toBeNull();
  });

  it("porcentaje: manda el % y la referencia recortada; una referencia vacía va como null", () => {
    const con = cargaParaEnviar(nuevoDraft({ tipo: "porcentaje", porcentaje: 80, referencia: "  Front Squat " }));
    expect(con).toEqual({ prescribed_weight: null, prescribed_percentage: 80, reference_exercise: "Front Squat" });
    expect(cargaParaEnviar(nuevoDraft({ tipo: "porcentaje", referencia: "   " })).reference_exercise).toBeNull();
  });

  it("sin carga: todo null aunque haya valores escritos", () => {
    expect(cargaParaEnviar(nuevoDraft({ tipo: "libre", weight: 50, porcentaje: 70, referencia: "x" }))).toEqual({
      prescribed_weight: null,
      prescribed_percentage: null,
      reference_exercise: null,
    });
  });

  it("en metcon la carga individual queda vacía", () => {
    expect(cargaParaEnviar(nuevoDraft({ tipo: "kg", weight: 60 }), true).prescribed_weight).toBeNull();
    expect(cargaParaEnviar(nuevoDraft({ tipo: "porcentaje" }), true).prescribed_percentage).toBeNull();
  });
});

describe("series una por una (rampas)", () => {
  const rampa = () => {
    const d = nuevoDraft({ series: 4, tipo: "porcentaje", referencia: "Snatch", rpe: 8 });
    [
      [3, 50],
      [3, 60],
      [1, 70],
      [1, 80],
    ].forEach(([reps, porcentaje], i) => (d.filas[i] = { reps, weight: 0, porcentaje }));
    return d;
  };

  it("cada serie manda sus propias repeticiones y su propio %", () => {
    const d = rampa();
    const cuerpos = d.filas.map((_, i) => camposDeFila(d, i));
    expect(cuerpos.map((c) => [c.prescribed_reps, c.prescribed_percentage])).toEqual([
      [3, 50],
      [3, 60],
      [1, 70],
      [1, 80],
    ]);
    expect(cuerpos.every((c) => c.reference_exercise === "Snatch" && c.rpe === 8)).toBe(true);
  });

  it("una rampa no es uniforme; series iguales sí", () => {
    expect(esUniforme(rampa())).toBe(false);
    expect(esUniforme(nuevoDraft({ series: 5, reps: 5 }))).toBe(true);
    expect(esUniforme(nuevoDraft({ series: 1 }))).toBe(true);
  });

  it("cambiar el número de series copia la última al crecer y recorta por el final", () => {
    const d = rampa();
    const mas = conNumeroDeSeries(d.filas, 6);
    expect(mas).toHaveLength(6);
    expect(mas[4]).toEqual(d.filas[3]);
    expect(mas[5]).toEqual(d.filas[3]);
    expect(conNumeroDeSeries(d.filas, 2)).toEqual(d.filas.slice(0, 2));
    expect(conNumeroDeSeries(d.filas, 0)).toHaveLength(1); // siempre queda una serie
  });

  it("los kg de una serie no se pierden al pasar por %", () => {
    const d = nuevoDraft({ series: 1, weight: 60, tipo: "kg" });
    d.tipo = "porcentaje";
    d.tipo = "kg";
    expect(camposDeFila(d, 0).prescribed_weight).toBe(60);
  });
});

describe("pesosWodParaEnviar", () => {
  const conPesos = nuevoDraft({ wod: { rxMale: 43, rxFemale: 30, scaledMale: 0, scaledFemale: 20 } });

  it("solo manda los pesos mayores que 0 y solo en metcon", () => {
    expect(pesosWodParaEnviar(conPesos, true)).toEqual({
      prescribed_weight_rx_male: 43,
      prescribed_weight_rx_female: 30,
      prescribed_weight_scaled_male: null,
      prescribed_weight_scaled_female: 20,
    });
    expect(Object.values(pesosWodParaEnviar(conPesos, false)).every((v) => v === null)).toBe(true);
  });
});

describe("camposComunes", () => {
  it("RPE 0 y bloque vacío se envían como null", () => {
    const c = camposComunes(nuevoDraft({ rpe: 0, block: "" }));
    expect(c.rpe).toBeNull();
    expect(c.block).toBeNull();
  });

  it("conserva RPE y bloque cuando existen", () => {
    const c = camposComunes(nuevoDraft({ rpe: 8, block: "strength" }));
    expect(c.rpe).toBe(8);
    expect(c.block).toBe("strength");
  });
});

describe("draftDeEjercicio", () => {
  it("toma RPE, bloque y la primera nota que exista, con una fila por serie", () => {
    const d = draftDeEjercicio(
      grupo(serie({ prescribed_reps: 3, rpe: 8, block: "strength", prescribed_weight: 100 }), serie({ coach_note: "Espalda neutra" })),
      true,
    );
    expect(d).toMatchObject({ name: "Back Squat", rpe: 8, block: "strength", nota: "Espalda neutra" });
    expect(d.filas).toHaveLength(2);
    expect(d.filas[0]).toMatchObject({ reps: 3, weight: 100 });
  });

  it("recupera una rampa tal cual: cada fila con su % y sus reps", () => {
    const d = draftDeEjercicio(
      grupo(
        serie({ prescribed_reps: 3, prescribed_percentage: 50 }),
        serie({ prescribed_reps: 3, prescribed_percentage: 60 }),
        serie({ prescribed_reps: 1, prescribed_percentage: 100 }),
      ),
      true,
    );
    expect(d.tipo).toBe("porcentaje");
    expect(d.filas.map((f) => [f.reps, f.porcentaje])).toEqual([
      [3, 50],
      [3, 60],
      [1, 100],
    ]);
    expect(esUniforme(d)).toBe(false);
  });

  it("deduce el tipo de carga: porcentaje si lo hay, libre solo si el formulario lo ofrece", () => {
    expect(draftDeEjercicio(grupo(serie({ prescribed_percentage: 80 })), true).tipo).toBe("porcentaje");
    expect(draftDeEjercicio(grupo(serie({ prescribed_weight: 60 })), true).tipo).toBe("kg");
    expect(draftDeEjercicio(grupo(serie()), true).tipo).toBe("libre");
    expect(draftDeEjercicio(grupo(serie()), false).tipo).toBe("kg");
  });

  it("valores por defecto cuando la serie no trae % ni referencia", () => {
    const d = draftDeEjercicio(grupo(serie()), true);
    expect(d.filas[0]).toMatchObject({ porcentaje: 75, weight: 0 });
    expect(d).toMatchObject({ referencia: "", rpe: 0, nota: "" });
  });
});

describe("firmaDeEjercicio", () => {
  it("cambia cuando llegan más series o cambia algún valor, y no cuando los datos son los mismos", () => {
    const a = serie({ id: "a", prescribed_reps: 3 });
    const b = serie({ id: "b", prescribed_reps: 3 });
    const una = firmaDeEjercicio(grupo(a));
    expect(firmaDeEjercicio(grupo(a))).toBe(una);
    expect(firmaDeEjercicio(grupo(a, b))).not.toBe(una);
    expect(firmaDeEjercicio(grupo({ ...a, prescribed_percentage: 60 }))).not.toBe(una);
  });
});

describe("seriesParaEnviar", () => {
  it("manda cada serie con sus repeticiones y su carga", () => {
    const d = nuevoDraft({ series: 3, tipo: "porcentaje" });
    d.filas = [
      { reps: 3, weight: 0, porcentaje: 50 },
      { reps: 3, weight: 0, porcentaje: 60 },
      { reps: 1, weight: 0, porcentaje: 80 },
    ];
    expect(seriesParaEnviar(d)).toEqual([
      { prescribed_reps: 3, prescribed_weight: null, prescribed_percentage: 50 },
      { prescribed_reps: 3, prescribed_weight: null, prescribed_percentage: 60 },
      { prescribed_reps: 1, prescribed_weight: null, prescribed_percentage: 80 },
    ]);
  });

  it("con kg fijos manda el peso de cada serie y sin carga manda null", () => {
    const d = nuevoDraft({ series: 2, tipo: "kg" });
    d.filas = [{ reps: 5, weight: 60, porcentaje: 75 }, { reps: 3, weight: 0, porcentaje: 75 }];
    expect(seriesParaEnviar(d)?.map((s) => s.prescribed_weight)).toEqual([60, null]);
    d.tipo = "libre";
    expect(seriesParaEnviar(d)?.every((s) => s.prescribed_weight === null && s.prescribed_percentage === null)).toBe(true);
  });

  it("en metcon no manda series (la carga va por categoría y género)", () => {
    expect(seriesParaEnviar(nuevoDraft(), true)).toBeUndefined();
  });
});
