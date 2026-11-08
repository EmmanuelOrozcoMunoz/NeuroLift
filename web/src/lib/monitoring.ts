/**
 * Monitoreo de errores (Sentry). Solo se activa si hay VITE_SENTRY_DSN; sin él no se descarga nada.
 * Sentry se carga bajo demanda (import dinámico) para no sumar peso al arranque de la app.
 * No se activa ningún envío de datos personales (el SDK no los manda por defecto: ni IP ni cuerpos de petición).
 */
const DSN = import.meta.env.VITE_SENTRY_DSN as string | undefined;

type Sentry = typeof import("@sentry/react");
let cargado: Promise<Sentry | null> | null = null;

function cargar(): Promise<Sentry | null> {
  if (!DSN) return Promise.resolve(null);
  cargado ??= import("@sentry/react")
    .then((sentry) => {
      sentry.init({
        dsn: DSN,
        environment: import.meta.env.MODE,
        tracesSampleRate: 0,
      });
      return sentry;
    })
    .catch(() => null);
  return cargado;
}

/** Arranca el monitoreo (al abrir la app). Seguro de llamar sin DSN: no hace nada. */
export function initMonitoring(): void {
  void cargar();
}

/** Reporta un error que la app atrapó (p. ej. el ErrorBoundary). Nunca lanza. */
export function reportError(error: unknown, contexto?: Record<string, unknown>): void {
  void cargar().then((sentry) => sentry?.captureException(error, contexto ? { extra: contexto } : undefined));
}
