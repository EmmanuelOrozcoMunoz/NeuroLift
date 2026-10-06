import { describe, expect, it } from "vitest";

import { PREPARACION_SEGUNDOS, anilloDelTemporizador, segundosDePreparacion } from "@/lib/wodTimer";

describe("segundosDePreparacion", () => {
  it("cuenta hacia atrás redondeando hacia arriba y nunca baja de 0", () => {
    const fin = 10_000;
    expect(segundosDePreparacion(fin, 0)).toBe(10);
    expect(segundosDePreparacion(fin, 100)).toBe(10); // el primer segundo sigue mostrando 10
    expect(segundosDePreparacion(fin, 9_001)).toBe(1);
    expect(segundosDePreparacion(fin, 10_000)).toBe(0);
    expect(segundosDePreparacion(fin, 12_000)).toBe(0);
    expect(PREPARACION_SEGUNDOS).toBe(10);
  });
});

describe("anilloDelTemporizador", () => {
  const base = { totalSegundos: null, timeCapSegundos: null };

  it("cuenta regresiva: el anillo se vacía y avisa en los últimos 10 s", () => {
    const total = 600;
    expect(anilloDelTemporizador({ ...base, modo: "countdown", totalSegundos: total, elapsedSeconds: 0 })).toEqual({
      value: 600, max: 600, tone: "brand", animar: true,
    });
    expect(anilloDelTemporizador({ ...base, modo: "countdown", totalSegundos: total, elapsedSeconds: 595 }).tone).toBe("warn");
    expect(anilloDelTemporizador({ ...base, modo: "countdown", totalSegundos: total, elapsedSeconds: 700 }).value).toBe(0);
  });

  it("cronómetro con time cap: se llena hasta el cap y se pone rojo al pasarse", () => {
    const antes = anilloDelTemporizador({ ...base, modo: "stopwatch", timeCapSegundos: 720, elapsedSeconds: 360 });
    expect(antes).toEqual({ value: 360, max: 720, tone: "brand", animar: true });
    const despues = anilloDelTemporizador({ ...base, modo: "stopwatch", timeCapSegundos: 720, elapsedSeconds: 800 });
    expect(despues).toMatchObject({ value: 720, tone: "danger" });
  });

  it("cronómetro sin time cap: una vuelta por minuto, sin animar el reinicio", () => {
    expect(anilloDelTemporizador({ ...base, modo: "stopwatch", elapsedSeconds: 75 })).toEqual({
      value: 15, max: 60, tone: "brand", animar: false,
    });
  });

  it("EMOM: lo que queda del minuto actual", () => {
    expect(anilloDelTemporizador({ ...base, modo: "emom", totalSegundos: 600, elapsedSeconds: 0 })).toMatchObject({ value: 60, max: 60 });
    expect(anilloDelTemporizador({ ...base, modo: "emom", totalSegundos: 600, elapsedSeconds: 125 })).toMatchObject({ value: 55, max: 60 });
  });

  it("Tabata: 20 s de trabajo y 10 s de descanso, cada fase con su color", () => {
    expect(anilloDelTemporizador({ ...base, modo: "tabata", totalSegundos: 240, elapsedSeconds: 5 })).toEqual({
      value: 15, max: 20, tone: "brand", animar: true,
    });
    expect(anilloDelTemporizador({ ...base, modo: "tabata", totalSegundos: 240, elapsedSeconds: 25 })).toEqual({
      value: 5, max: 10, tone: "muted", animar: true,
    });
    expect(anilloDelTemporizador({ ...base, modo: "tabata", totalSegundos: 240, elapsedSeconds: 30 })).toMatchObject({ value: 20, tone: "brand" });
  });

  it("al terminar el anillo queda en verde", () => {
    expect(anilloDelTemporizador({ ...base, modo: "countdown", totalSegundos: 60, elapsedSeconds: 60, terminado: true }).tone).toBe("done");
    expect(anilloDelTemporizador({ ...base, modo: "stopwatch", timeCapSegundos: 60, elapsedSeconds: 90, terminado: true }).tone).toBe("done");
  });
});
