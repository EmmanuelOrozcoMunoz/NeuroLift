/** Lógica pura del temporizador del WOD (sin React ni reloj), para poder probarla. La usa
 *  components/WodTimer.tsx. */

/** Cuenta regresiva antes de arrancar: nadie empieza un WOD en el instante en que toca "Iniciar"
 *  (tiene que dejar el teléfono, ponerse en posición). Son los 10 s habituales de un box. */
export const PREPARACION_SEGUNDOS = 10;

/** Segundos que faltan para que termine la preparación (redondeado hacia arriba: se muestra "10"
 *  durante el primer segundo y "1" durante el último, nunca "0" mientras aún falta tiempo). */
export function segundosDePreparacion(finMs: number, ahoraMs: number): number {
  return Math.max(0, Math.ceil((finMs - ahoraMs) / 1000));
}

export type ModoDelTimer = "stopwatch" | "countdown" | "emom" | "tabata" | "none";
export type TonoDelAnillo = "brand" | "muted" | "warn" | "danger" | "done";

export interface AnilloDelTimer {
  /** Cuánto del anillo está lleno: `value` de `max`. */
  value: number;
  max: number;
  tone: TonoDelAnillo;
  /** false cuando el anillo da la vuelta completa (cronómetro sin time cap): animar el regreso a
   *  cero lo mostraría "rebobinando" en vez de reiniciar. */
  animar: boolean;
}

/** Estado del anillo del timer. Es lo que ESTÁ POR PASAR en la cuenta regresiva, EMOM y Tabata
 *  (el anillo se vacía), y lo que YA PASÓ en el cronómetro (el anillo se llena hacia el time cap;
 *  sin time cap da una vuelta por minuto, como el segundero de un reloj). */
export function anilloDelTemporizador({
  modo,
  elapsedSeconds,
  totalSegundos,
  timeCapSegundos,
  terminado = false,
}: {
  modo: ModoDelTimer;
  elapsedSeconds: number;
  totalSegundos: number | null;
  timeCapSegundos: number | null;
  terminado?: boolean;
}): AnilloDelTimer {
  const tonoFinal = (tono: TonoDelAnillo): TonoDelAnillo => (terminado ? "done" : tono);

  if (modo === "tabata") {
    const ciclo = elapsedSeconds % 30;
    const trabajo = ciclo < 20;
    const duracion = trabajo ? 20 : 10;
    const restante = trabajo ? 20 - ciclo : 30 - ciclo;
    return { value: terminado ? 0 : restante, max: duracion, tone: tonoFinal(trabajo ? "brand" : "muted"), animar: true };
  }

  if (modo === "emom") {
    return { value: terminado ? 0 : 60 - (elapsedSeconds % 60), max: 60, tone: tonoFinal("brand"), animar: true };
  }

  if (modo === "countdown") {
    const total = totalSegundos ?? 0;
    const restante = Math.max(0, total - elapsedSeconds);
    // Los últimos 10 s avisan: el atleta mira el anillo de reojo mientras entrena.
    return { value: restante, max: Math.max(1, total), tone: tonoFinal(restante <= 10 ? "warn" : "brand"), animar: true };
  }

  if (modo === "stopwatch") {
    if (timeCapSegundos != null) {
      const pasado = elapsedSeconds >= timeCapSegundos;
      return {
        value: Math.min(elapsedSeconds, timeCapSegundos),
        max: Math.max(1, timeCapSegundos),
        tone: terminado ? "done" : pasado ? "danger" : "brand",
        animar: true,
      };
    }
    return { value: elapsedSeconds % 60, max: 60, tone: tonoFinal("brand"), animar: false };
  }

  return { value: 0, max: 1, tone: "muted", animar: false };
}
