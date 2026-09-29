import { describe, expect, it } from "vitest";

import { groupSummary } from "@/lib/sessions";
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
