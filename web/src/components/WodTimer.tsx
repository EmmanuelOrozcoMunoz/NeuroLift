import { useCallback, useEffect, useRef, useState } from "react";
import type { ReactNode } from "react";

import { Badge, Button, cx } from "@/components/ui";
import { formatSeconds } from "@/lib/dates";
import type { WodFormat } from "@/lib/types";

type Fase = "idle" | "running" | "paused" | "done";

/** Pita corto sintetizado con Web Audio (sin archivo de audio que alojar) — se degrada en
 *  silencio si el navegador bloquea el audio (falta de gesto del usuario, etc.). */
function pitar(frecuencia = 880, duracionMs = 150) {
  try {
    const Ctx = window.AudioContext || (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext;
    const ctx = new Ctx();
    const osc = ctx.createOscillator();
    const gain = ctx.createGain();
    osc.frequency.value = frecuencia;
    osc.connect(gain);
    gain.connect(ctx.destination);
    gain.gain.setValueAtTime(0.25, ctx.currentTime);
    osc.start();
    osc.stop(ctx.currentTime + duracionMs / 1000);
    osc.onended = () => void ctx.close();
  } catch {
    /* audio bloqueado o no soportado: no pasa nada, el timer sigue funcionando */
  }
  if (typeof navigator !== "undefined" && "vibrate" in navigator) navigator.vibrate(200);
}

type Modo = "stopwatch" | "countdown" | "emom" | "tabata" | "none";

function resolverModo(formato: WodFormat, capSegundos: number | null): { modo: Modo; totalSegundos: number | null } {
  if (formato === "for_time") return { modo: "stopwatch", totalSegundos: capSegundos };
  if (formato === "tabata") return { modo: "tabata", totalSegundos: 240 }; // protocolo fijo: 8 rondas de 20s+10s
  if (formato === "emom") return capSegundos ? { modo: "emom", totalSegundos: capSegundos } : { modo: "none", totalSegundos: null };
  if (formato === "amrap" || formato === "amrap_reps" || formato === "calories" || formato === "distance" || formato === "watts") {
    return capSegundos ? { modo: "countdown", totalSegundos: capSegundos } : { modo: "stopwatch", totalSegundos: null };
  }
  return { modo: "none", totalSegundos: null }; // "1rm": no necesita timer
}

/**
 * Cronómetro real del WOD, según el formato y el time cap que fijó el coach — el atleta lo
 * arranca mientras entrena en vez de solo escribir el resultado al terminar:
 * - "for_time": cronómetro hacia ARRIBA (con el time cap como referencia si existe).
 * - "amrap"/"amrap_reps"/"calories"/"distance"/"watts": cuenta regresiva desde el time cap (o
 *   cronómetro hacia arriba si el coach no puso time cap).
 * - "emom": cuenta regresiva por ronda de 1 minuto, usa el time cap como duración total.
 * - "tabata": protocolo fijo 20s trabajo / 10s descanso x 8 rondas — no necesita time cap.
 * `onDone` se dispara al terminar (con los segundos transcurridos si aplica, para "for_time")
 * para que el padre abra la hoja de registro de resultado ya con ese dato precargado.
 */
export function WodTimer({
  format,
  timeCapSeconds,
  onDone,
  fallback = null,
}: {
  format: WodFormat;
  timeCapSeconds: number | null;
  onDone: (segundosTranscurridos?: number) => void;
  /** Se muestra cuando el formato no puede armar un timer (ej. EMOM sin duración fijada por el
   *  coach) — para "1rm" (que nunca necesita timer) se ignora y no se muestra nada. */
  fallback?: ReactNode;
}) {
  const { modo, totalSegundos } = resolverModo(format, timeCapSeconds);

  const [fase, setFase] = useState<Fase>("idle");
  const [tick, setTick] = useState(0);
  const inicioRef = useRef<number | null>(null);
  const acumuladoMsRef = useRef(0);
  const ultimoBeepSegundoRef = useRef(-1);
  const terminadoRef = useRef(false);

  // Late-tick del reloj: fuerza un re-render cada 250ms mientras corre, para que
  // elapsedSeconds (derivado de Date.now(), no de un contador) se mantenga al día incluso si
  // el navegador retrasa algún intervalo.
  useEffect(() => {
    if (fase !== "running") return;
    const id = window.setInterval(() => setTick((n) => n + 1), 250);
    return () => window.clearInterval(id);
  }, [fase]);

  const elapsedMs = acumuladoMsRef.current + (fase === "running" && inicioRef.current ? Date.now() - inicioRef.current : 0);
  const elapsedSeconds = Math.floor(elapsedMs / 1000);

  const terminar = useCallback(
    (segundosParaResultado?: number) => {
      if (terminadoRef.current) return;
      terminadoRef.current = true;
      // Congela el elapsed final leyendo los refs directamente (no la variable `elapsedMs` del
      // render en que se creó este callback, que quedaría vieja): así el reloj no "rebota" al
      // valor inicial cuando fase pasa a "done" y el término `fase === "running"` deja de sumar.
      acumuladoMsRef.current = acumuladoMsRef.current + (inicioRef.current ? Date.now() - inicioRef.current : 0);
      inicioRef.current = null;
      setFase("done");
      pitar(660, 400);
      onDone(segundosParaResultado);
    },
    [onDone],
  );

  // Auto-fin (cuenta regresiva/EMOM/Tabata) y beeps de intervalo — efectos, no durante el
  // render: aquí sí es seguro disparar setState y el callback onDone del padre.
  useEffect(() => {
    if (fase !== "running") return;
    if (totalSegundos != null && elapsedSeconds >= totalSegundos) {
      terminar(modo === "stopwatch" ? elapsedSeconds : undefined);
      return;
    }
    if (elapsedSeconds !== ultimoBeepSegundoRef.current) {
      if (modo === "emom" && elapsedSeconds > 0 && elapsedSeconds % 60 === 0) pitar(880, 150);
      if (modo === "tabata" && elapsedSeconds > 0 && elapsedSeconds % 10 === 0 && elapsedSeconds % 30 !== 10) pitar(880, 150);
      ultimoBeepSegundoRef.current = elapsedSeconds;
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [tick, fase, elapsedSeconds, totalSegundos, modo, terminar]);

  if (modo === "none") return format === "1rm" ? null : <>{fallback}</>;

  function iniciar() {
    inicioRef.current = Date.now();
    setFase("running");
  }

  function pausar() {
    acumuladoMsRef.current = elapsedMs;
    inicioRef.current = null;
    setFase("paused");
  }

  function reanudar() {
    inicioRef.current = Date.now();
    setFase("running");
  }

  const botones = (
    <div className="mt-3 flex gap-2">
      {fase === "idle" && (
        <Button full onClick={iniciar}>
          ▶ Iniciar
        </Button>
      )}
      {fase === "running" && (
        <>
          <Button variant="secondary" className="grow" onClick={pausar}>
            ⏸ Pausar
          </Button>
          <Button variant="done" className="grow" onClick={() => terminar(modo === "stopwatch" ? elapsedSeconds : undefined)}>
            ⏹ Detener
          </Button>
        </>
      )}
      {fase === "paused" && (
        <>
          <Button className="grow" onClick={reanudar}>
            ▶ Reanudar
          </Button>
          <Button variant="done" className="grow" onClick={() => terminar(modo === "stopwatch" ? elapsedSeconds : undefined)}>
            ⏹ Detener
          </Button>
        </>
      )}
      {fase === "done" && (
        <p className="w-full text-center text-sm font-semibold text-done">¡Tiempo! Registra tu resultado abajo.</p>
      )}
    </div>
  );

  if (modo === "tabata") {
    const cicloSegundo = elapsedSeconds % 30;
    const enTrabajo = cicloSegundo < 20;
    const rondaActual = Math.min(8, Math.floor(elapsedSeconds / 30) + 1);
    const restante = enTrabajo ? 20 - cicloSegundo : 30 - cicloSegundo;
    return (
      <div className="mt-3 border-t border-line pt-3">
        <div className="mb-1 flex items-center justify-between">
          <Badge tone={enTrabajo ? "brand" : "neutral"}>{enTrabajo ? "🔥 TRABAJO" : "😮‍💨 DESCANSO"}</Badge>
          <span className="text-xs font-medium text-muted">Ronda {rondaActual}/8</span>
        </div>
        <p className={cx("text-center text-4xl font-black tabular-nums", fase === "done" && "text-done")}>
          {fase === "done" ? "0:00" : formatSeconds(restante)}
        </p>
        {botones}
      </div>
    );
  }

  if (modo === "emom") {
    const totalRondas = Math.ceil((totalSegundos ?? 0) / 60);
    const rondaActual = Math.min(totalRondas, Math.floor(elapsedSeconds / 60) + 1);
    const restanteEnRonda = 60 - (elapsedSeconds % 60);
    return (
      <div className="mt-3 border-t border-line pt-3">
        <div className="mb-1 flex items-center justify-between">
          <Badge tone="brand">⏱ EMOM</Badge>
          <span className="text-xs font-medium text-muted">
            Ronda {rondaActual}/{totalRondas}
          </span>
        </div>
        <p className={cx("text-center text-4xl font-black tabular-nums", fase === "done" && "text-done")}>
          {fase === "done" ? "0:00" : formatSeconds(fase === "idle" ? 60 : restanteEnRonda)}
        </p>
        {botones}
      </div>
    );
  }

  if (modo === "countdown") {
    const restante = Math.max(0, (totalSegundos ?? 0) - elapsedSeconds);
    return (
      <div className="mt-3 border-t border-line pt-3">
        <p className={cx("text-center text-4xl font-black tabular-nums", fase === "done" && "text-done")}>
          {formatSeconds(restante)}
        </p>
        {botones}
      </div>
    );
  }

  // stopwatch (for_time, o cualquier otro formato sin time cap)
  const pasoCap = timeCapSeconds != null && elapsedSeconds >= timeCapSeconds;
  return (
    <div className="mt-3 border-t border-line pt-3">
      <p
        className={cx(
          "text-center text-4xl font-black tabular-nums",
          pasoCap ? "text-danger" : fase === "done" ? "text-done" : undefined,
        )}
      >
        {formatSeconds(elapsedSeconds)}
      </p>
      {timeCapSeconds != null && (
        <p className={cx("mt-1 text-center text-xs font-medium", pasoCap ? "text-danger" : "text-muted")}>
          Time cap: {formatSeconds(timeCapSeconds)}
          {pasoCap ? " — ¡superado!" : ""}
        </p>
      )}
      {botones}
    </div>
  );
}
