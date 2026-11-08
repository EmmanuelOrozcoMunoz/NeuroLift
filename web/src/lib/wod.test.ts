import { describe, expect, it } from "vitest";

import { equipoDe } from "@/lib/equipo";
import { formatWodResult } from "@/lib/wod";
import type { User } from "@/lib/types";

const base = {
  wod_format: null,
  wod_time_seconds: null,
  wod_rounds: null,
  wod_extra_reps: null,
  wod_emom_completed: null,
  wod_calories: null,
  wod_distance_meters: null,
  wod_watts: null,
} as const;

describe("formatWodResult — intervalos", () => {
  it("muestra el total y cuántos intervalos fueron", () => {
    const r = formatWodResult({ ...base, wod_format: "intervals", wod_time_seconds: 175, wod_interval_times: [50, 60, 65] });
    expect(r).toBe("Intervalos: 2:55 total (3 intervalos)");
  });

  it("sin los tiempos de cada uno, solo el total", () => {
    expect(formatWodResult({ ...base, wod_format: "intervals", wod_time_seconds: 175 })).toBe("Intervalos: 2:55 total");
  });

  it("sin resultado todavía, nada", () => {
    expect(formatWodResult({ ...base, wod_format: "intervals" })).toBeNull();
  });
});

describe("equipoDe — con quién compite uno", () => {
  const usuario = (kind: "box" | "coach", name: string) => ({ box: { kind, name } }) as unknown as User;

  it("en un box habla del box", () => {
    const e = equipoDe(usuario("box", "Box Norte"), true);
    expect(e.todos).toBe("Todo el box");
    expect(e.tu).toBe("de tu box");
    expect(e.subtitulo).toBe("Box Norte");
  });

  it("con un coach independiente no dice 'box'", () => {
    const atleta = equipoDe(usuario("coach", "Laura"), true);
    expect(atleta.todos).toBe("Todos los atletas de tu coach");
    expect(atleta.tu).toBe("de tu coach");
    expect(atleta.subtitulo).toBe("Atletas de Laura");
    expect(equipoDe(usuario("coach", "Laura"), false).todos).toBe("Todos tus atletas");
  });
});
