import { describe, expect, it } from "vitest";

import {
  camposComunes,
  cargaParaEnviar,
  draftDeEjercicio,
  nuevoDraft,
  pesosWodParaEnviar,
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
  it("toma series, reps, RPE, bloque y la primera nota que exista", () => {
    const d = draftDeEjercicio(
      grupo(serie({ prescribed_reps: 3, rpe: 8, block: "strength", prescribed_weight: 100 }), serie({ coach_note: "Espalda neutra" })),
      true,
    );
    expect(d).toMatchObject({ name: "Back Squat", series: 2, reps: 3, rpe: 8, block: "strength", nota: "Espalda neutra" });
  });

  it("deduce el tipo de carga: porcentaje si lo hay, libre solo si el formulario lo ofrece", () => {
    expect(draftDeEjercicio(grupo(serie({ prescribed_percentage: 80 })), true).tipo).toBe("porcentaje");
    expect(draftDeEjercicio(grupo(serie({ prescribed_weight: 60 })), true).tipo).toBe("kg");
    expect(draftDeEjercicio(grupo(serie()), true).tipo).toBe("libre");
    expect(draftDeEjercicio(grupo(serie()), false).tipo).toBe("kg");
  });

  it("valores por defecto cuando la serie no trae % ni referencia", () => {
    const d = draftDeEjercicio(grupo(serie()), true);
    expect(d).toMatchObject({ porcentaje: 75, weight: 0, referencia: "", rpe: 0, nota: "" });
  });
});
