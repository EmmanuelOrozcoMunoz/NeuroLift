import { Link } from "react-router-dom";
import type { ReactNode } from "react";

import { InstallButton } from "@/components/InstallApp";
import {
  IconCheck,
  IconClock,
  IconDumbbell,
  IconOffline,
  IconSpark,
  IconToday,
  IconTrophy,
  IconUsers,
  Logo,
} from "@/components/icons";
import { cx } from "@/components/ui";
import { useInstallPrompt } from "@/lib/pwa";

/**
 * Página pública: lo primero que ve alguien que abre el link sin sesión, antes de instalar la
 * app o crear cuenta. Si la app ya corre instalada (abierta desde el ícono) no se muestra: el
 * router manda directo al login (ver RequireAppAccess en App.tsx).
 */
export default function Landing() {
  const { installed, canPrompt, isIOS } = useInstallPrompt();
  // Si el navegador no puede instalar (ej. Firefox de escritorio), crear cuenta pasa a ser la
  // acción principal en vez de quedar como botón secundario junto a un hueco.
  const installable = !installed && (canPrompt || isIOS);

  return (
    <div className="min-h-dvh overflow-x-hidden">
      {/* ------------------------------------------------------------ barra superior */}
      <header className="pt-safe mx-auto flex max-w-5xl items-center justify-between px-5">
        <div className="flex min-h-16 items-center gap-2.5">
          <Logo className="h-8 w-8" />
          <span className="font-bold tracking-tight">NeuroLift</span>
        </div>
        <Link to="/login" className="rounded-xl px-3 py-2 text-sm font-semibold text-muted active:bg-surface-2">
          Entrar
        </Link>
      </header>

      {/* ---------------------------------------------------------------------- hero */}
      <section className="relative mx-auto grid max-w-5xl items-center gap-12 px-5 pt-8 pb-16 md:grid-cols-2 md:pt-16">
        {/* Halo del color de acento detrás del teléfono: da profundidad sin imágenes externas */}
        <div
          aria-hidden
          className="pointer-events-none absolute top-40 left-1/2 h-80 w-80 -translate-x-1/2 rounded-full bg-brand/25 blur-3xl md:top-24 md:left-3/4"
        />

        <div className="relative">
          <p className="text-sm font-semibold tracking-[0.2em] text-brand uppercase">Entrena con método</p>
          <h1 className="mt-3 text-4xl leading-[1.1] font-bold tracking-tight md:text-5xl">
            Tu entrenamiento, listo cuando llegas.
          </h1>
          <p className="mt-4 text-lg text-muted">
            La sesión del día que programó tu coach, tus series, tus marcas y tu progreso. Todo en el celular, con
            botones pensados para usarse con la barra en la mano.
          </p>

          <div className="mt-8 space-y-3 sm:max-w-sm">
            <InstallButton />
            <Link
              to="/registro"
              className={cx(
                "flex min-h-12 w-full items-center justify-center rounded-xl px-4 font-semibold transition-colors",
                installable
                  ? "border border-line bg-surface-2 text-fg active:bg-line"
                  : "bg-brand text-on-brand active:bg-brand/85",
              )}
            >
              Crear cuenta
            </Link>
            <p className="text-center text-sm text-muted">
              ¿Ya tienes cuenta?{" "}
              <Link to="/login" className="font-semibold text-brand">
                Inicia sesión
              </Link>
            </p>
          </div>
        </div>

        <PhonePreview />
      </section>

      {/* --------------------------------------------------------------- funciones */}
      <section className="mx-auto max-w-5xl px-5 py-12">
        <h2 className="text-sm font-semibold tracking-wide text-muted uppercase">Lo que puedes hacer</h2>
        <div className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          <Feature icon={<IconToday />} title="Tu sesión de hoy">
            Abres la app y ya está ahí: ejercicios, series, repeticiones y pesos, según tu mesociclo.
          </Feature>
          <Feature icon={<IconDumbbell />} title="Registra sin soltar la barra">
            Botones grandes de −/+, cálculo de discos por lado y cambio entre kg y lb en un toque.
          </Feature>
          <Feature icon={<IconTrophy />} title="Marcas y Fit Level">
            Guarda tus 1RM, los pesos se calculan solos a partir de ellos y mide tu nivel con baremos.
          </Feature>
          <Feature icon={<IconClock />} title="Timer de WODs">
            AMRAP, EMOM, Tabata y por tiempo, con cuenta regresiva, y tu resultado queda guardado.
          </Feature>
          <Feature icon={<IconUsers />} title="Para coaches">
            Grupos, mesociclos por atleta, planes y un tablero de actividad para ver quién entrenó.
          </Feature>
          <Feature icon={<IconSpark />} title="Rutinas con IA">
            El coach genera una base de rutina en segundos y la ajusta a su manera antes de publicarla.
          </Feature>
        </div>
      </section>

      {/* -------------------------------------------------------- por qué instalarla */}
      <section className="mx-auto max-w-5xl px-5 py-12">
        <div className="rounded-2xl border border-line bg-surface p-6 md:p-10">
          <div className="grid gap-8 md:grid-cols-2 md:items-center">
            <div>
              <h2 className="text-2xl font-bold tracking-tight md:text-3xl">Instálala como app, sin tienda.</h2>
              <p className="mt-3 text-muted">
                NeuroLift es una app web instalable: se agrega a tu pantalla de inicio directo desde el navegador y
                se abre a pantalla completa, como cualquier otra app.
              </p>
            </div>
            <ul className="space-y-3">
              {[
                "Sin App Store ni Play Store: se instala en segundos",
                "Casi no ocupa espacio en tu celular",
                "Abre aunque la señal del gimnasio falle",
                "Siempre en su última versión, sin descargar actualizaciones",
              ].map((item) => (
                <li key={item} className="flex items-start gap-3">
                  <span className="mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-done-soft text-done">
                    <IconCheck className="h-4 w-4" />
                  </span>
                  <span>{item}</span>
                </li>
              ))}
            </ul>
          </div>
          <div className="mt-8 sm:max-w-sm">
            <InstallButton />
          </div>
        </div>
      </section>

      {/* ------------------------------------------------------------------- footer */}
      <footer className="pb-safe mx-auto flex max-w-5xl flex-col items-center gap-2 px-5 pt-6 pb-10 text-center text-sm text-muted">
        <div className="flex items-center gap-2">
          <IconOffline className="h-4 w-4" />
          <span>Hecha para el gimnasio: tema oscuro, botones grandes y poca señal.</span>
        </div>
        <p>© {new Date().getFullYear()} NeuroLift</p>
      </footer>
    </div>
  );
}

function Feature({ icon, title, children }: { icon: ReactNode; title: string; children: ReactNode }) {
  return (
    <div className="rounded-2xl border border-line bg-surface p-5">
      <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-brand-soft text-brand [&>svg]:h-5 [&>svg]:w-5">
        {icon}
      </div>
      <h3 className="mt-4 font-bold">{title}</h3>
      <p className="mt-1 text-sm text-muted">{children}</p>
    </div>
  );
}

/**
 * Maqueta estática de la pantalla "Hoy" dentro de un teléfono. Es una ilustración (datos de
 * ejemplo, sin llamadas a la API) para que se entienda la app antes de crear cuenta.
 */
function PhonePreview() {
  const sets = [
    { reps: 5, kg: 100, done: true },
    { reps: 5, kg: 100, done: true },
    { reps: 5, kg: 100, done: false },
  ];

  return (
    <div className="relative mx-auto w-full max-w-[18rem]" aria-hidden>
      <div className="rounded-[2.5rem] border border-line bg-ink p-2.5 shadow-2xl shadow-brand/20">
        <div className="overflow-hidden rounded-[2rem] border border-line/60 bg-ink">
          {/* notch */}
          <div className="flex justify-center pt-2.5">
            <div className="h-5 w-24 rounded-full bg-surface" />
          </div>

          <div className="px-4 pt-4 pb-3">
            <p className="text-xs text-muted">Jueves · Semana 3 de 6</p>
            <p className="text-xl font-bold">Hoy</p>
          </div>

          <div className="space-y-3 px-4 pb-4">
            <div className="rounded-2xl border border-line bg-surface p-3">
              <div className="flex items-center justify-between">
                <p className="font-semibold">Back Squat</p>
                <span className="rounded-full bg-brand-soft px-2 py-0.5 text-[10px] font-semibold text-brand">
                  75% 1RM
                </span>
              </div>
              <div className="mt-2.5 space-y-1.5">
                {sets.map((set, i) => (
                  <div
                    key={i}
                    className="flex items-center justify-between rounded-xl bg-surface-2 px-2.5 py-2 text-sm"
                  >
                    <span className="text-muted">Serie {i + 1}</span>
                    <span className="font-semibold">
                      {set.reps} × {set.kg} kg
                    </span>
                    <span
                      className={cx(
                        "flex h-5 w-5 items-center justify-center rounded-full",
                        set.done ? "bg-done text-ink" : "border border-line",
                      )}
                    >
                      {set.done && <IconCheck className="h-3.5 w-3.5" />}
                    </span>
                  </div>
                ))}
              </div>
              {/* discos por lado: 100 kg = barra de 20 + 40 por lado */}
              <div className="mt-2.5 flex items-center justify-center gap-0.5">
                <div className="h-2 w-8 rounded-l bg-muted/50" />
                <div className="h-10 w-2.5 rounded-sm bg-danger" />
                <div className="h-8 w-2 rounded-sm bg-brand" />
                <div className="h-2 w-10 bg-muted/50" />
              </div>
              <p className="mt-1 text-center text-[10px] text-muted">25 + 15 kg por lado</p>
            </div>

            <div className="flex items-center gap-3 rounded-2xl border border-line bg-surface p-3">
              <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-done-soft text-done">
                <IconClock className="h-5 w-5" />
              </div>
              <div>
                <p className="text-sm font-semibold">WOD · AMRAP 12'</p>
                <p className="text-xs text-muted">Toca para iniciar el timer</p>
              </div>
            </div>
          </div>

          {/* barra inferior */}
          <div className="flex justify-around border-t border-line px-2 pt-2 pb-3 text-[9px] font-semibold text-muted">
            <span className="flex flex-col items-center gap-0.5 text-brand">
              <IconToday className="h-4 w-4" />
              Hoy
            </span>
            <span className="flex flex-col items-center gap-0.5">
              <IconDumbbell className="h-4 w-4" />
              Entrenos
            </span>
            <span className="flex flex-col items-center gap-0.5">
              <IconTrophy className="h-4 w-4" />
              Marcas
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}
