import { useQueries } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import type { ReactNode } from "react";

import { PageHeader } from "@/components/AppShell";
import { IconCheck, IconChevronRight, IconClock, IconDumbbell, IconStore } from "@/components/icons";
import { ProgressRing } from "@/components/ProgressRing";
import { SessionCard } from "@/components/SessionCard";
import { EmptyState, ErrorState, Skeleton, cx } from "@/components/ui";
import { apiFetch } from "@/lib/api";
import { useCurrentUser } from "@/lib/auth";
import { daysFromToday, formatSeconds, longDate, parseApiDate, relativeDay, todayIso, toApiDate } from "@/lib/dates";
import { queryKeys, useMesocycles } from "@/lib/queries";
import { groupSets, isSetLogged, sessionProgress, splitSessions } from "@/lib/sessions";
import type { ExerciseGroup } from "@/lib/sessions";
import { kgTo, useWeightUnit } from "@/lib/units";
import { WOD_FORMAT_LABELS } from "@/lib/wod";
import type { MesocycleFull, TrainingSession, WeightUnit } from "@/lib/types";

interface SessionRef {
  session: TrainingSession;
  mesocycleId: string;
  mesocycleName: string;
  adapted?: TrainingSession;
}

const WEEKDAY_INITIALS = ["L", "M", "X", "J", "V", "S", "D"];
const WEEKDAY_NAMES = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"];
// Ejercicios que se ven en la tarjeta de hoy antes de resumir el resto en "+N más"
const HERO_MAX_EXERCISES = 5;

export default function Today() {
  const user = useCurrentUser();
  const mesocycles = useMesocycles(user.id);

  // Un atleta puede tener a la vez el mesociclo de su coach y un plan que adquirió, así que
  // "hoy" se busca en todos los mesociclos activos, no en uno solo.
  const activos = (mesocycles.data ?? []).filter((mesocycle) => mesocycle.is_active).slice(0, 5);

  const detalles = useQueries({
    queries: activos.map((mesocycle) => ({
      queryKey: queryKeys.mesocycle(mesocycle.id),
      queryFn: () => apiFetch<MesocycleFull>(`/mesocycles/${mesocycle.id}`),
    })),
  });

  // isPending solo es true la PRIMERA vez: si ya hay datos en caché (volver a esta pestaña),
  // se muestran al instante mientras TanStack Query revalida en segundo plano.
  const cargando = mesocycles.isPending || detalles.some((query) => query.isPending);
  const error = mesocycles.error ?? detalles.find((query) => query.error)?.error;

  const todas: SessionRef[] = [];
  for (const query of detalles) {
    const mesocycle = query.data;
    if (!mesocycle) continue;
    const { originals, adaptedByParent } = splitSessions(mesocycle.sessions);
    for (const session of originals) {
      todas.push({
        session,
        mesocycleId: mesocycle.id,
        mesocycleName: mesocycle.name ?? "Mi rutina",
        adapted: adaptedByParent.get(session.id),
      });
    }
  }

  const hoyIso = todayIso();
  const deHoy = todas.filter((item) => item.session.scheduled_date === hoyIso);
  const proximas = todas
    .filter((item) => daysFromToday(item.session.scheduled_date) > 0)
    .sort(
      (a, b) => parseApiDate(a.session.scheduled_date).getTime() - parseApiDate(b.session.scheduled_date).getTime(),
    )
    .slice(0, 3);
  const pendientesAtras = todas
    .filter(
      (item) =>
        daysFromToday(item.session.scheduled_date) < 0 &&
        item.session.status !== "completed" &&
        item.session.sets.length > 0,
    )
    .slice(-2);

  const nombreCorto = user.full_name.split(" ")[0];

  return (
    <>
      <PageHeader title={`Hola, ${nombreCorto}`} subtitle={capitalize(longDate(hoyIso))} />

      {cargando && <TodaySkeleton />}

      {!cargando && error && <ErrorState error={error} onRetry={() => void mesocycles.refetch()} />}

      {!cargando && !error && todas.length === 0 && (
        <EmptyState
          icon={<IconStore className="h-10 w-10" />}
          title="Todavía no tienes entrenamientos"
          action={
            <Link
              to="/planes"
              className="press inline-flex h-touch items-center rounded-xl bg-brand px-5 font-semibold text-on-brand"
            >
              Ver planes disponibles
            </Link>
          }
        >
          Pídele a tu coach que te programe un mesociclo, o adquiere un plan hecho por un entrenador y empieza por tu
          cuenta.
        </EmptyState>
      )}

      {!cargando && !error && todas.length > 0 && (
        <div className="space-y-8">
          <WeekProgress sessions={todas} todayIso={hoyIso} />

          <section aria-labelledby="hoy-titulo">
            <h2 id="hoy-titulo" className="label-caps mb-3">
              {deHoy.length > 1 ? "Tus sesiones de hoy" : "Tu sesión de hoy"}
            </h2>
            {deHoy.length > 0 ? (
              <div className="space-y-4">
                {deHoy.map((item) => (
                  <TodayHero key={item.session.id} item={item} />
                ))}
              </div>
            ) : (
              <RestDay next={proximas[0]} />
            )}
          </section>

          {pendientesAtras.length > 0 && (
            <SessionList title="Sin registrar" items={pendientesAtras} />
          )}

          {proximas.length > 0 && (
            <SessionList
              title="Lo que viene"
              items={proximas}
              action={
                <Link to="/entrenos" className="flex min-h-touch items-center text-sm font-semibold text-muted active:text-fg">
                  Ver todo
                </Link>
              }
            />
          )}
        </div>
      )}
    </>
  );
}

// ------------------------------------------------------------------ semana

/** Anillo con las sesiones hechas de la semana + los 7 días (hecho / hoy / programado). */
function WeekProgress({ sessions, todayIso: hoyIso }: { sessions: SessionRef[]; todayIso: string }) {
  const lunes = startOfWeek(hoyIso);
  const dias = WEEKDAY_INITIALS.map((inicial, i) => {
    const iso = addDays(lunes, i);
    const delDia = sessions.filter((item) => item.session.scheduled_date === iso);
    const hecho = delDia.length > 0 && delDia.every((item) => item.session.status === "completed");
    return { iso, inicial, nombre: WEEKDAY_NAMES[i], programado: delDia.length > 0, hecho, esHoy: iso === hoyIso };
  });
  const deLaSemana = sessions.filter((item) => item.session.scheduled_date >= lunes && item.session.scheduled_date <= addDays(lunes, 6));
  if (deLaSemana.length === 0) return null;
  const hechas = deLaSemana.filter((item) => item.session.status === "completed").length;

  return (
    <section className="flex items-center gap-5 rounded-3xl bg-surface p-5" aria-label="Progreso de la semana">
      <ProgressRing
        value={hechas}
        max={deLaSemana.length}
        size={92}
        label={`${hechas} de ${deLaSemana.length} sesiones completadas esta semana`}
      >
        <span className="num text-metric-sm">
          {hechas}
          <span className="text-muted">/{deLaSemana.length}</span>
        </span>
      </ProgressRing>

      <div className="min-w-0 grow">
        <p className="label-caps">Esta semana</p>
        <ol className="mt-3 grid grid-cols-7 gap-1">
          {dias.map((dia) => {
            const estado = dia.hecho ? "completado" : dia.programado ? (dia.esHoy ? "hoy, pendiente" : "programado") : "descanso";
            return (
              <li key={dia.iso} className="flex flex-col items-center gap-1.5" aria-label={`${dia.nombre}: ${estado}`}>
                <span className={cx("text-[11px] font-semibold", dia.esHoy ? "text-fg" : "text-muted")} aria-hidden>
                  {dia.inicial}
                </span>
                <span aria-hidden className="flex h-7 w-7 items-center justify-center">
                  {dia.programado || dia.esHoy ? (
                    <span
                      className={cx(
                        "flex h-7 w-7 items-center justify-center rounded-full",
                        dia.hecho && "bg-done text-ink",
                        !dia.hecho && !dia.esHoy && "bg-surface-2",
                        !dia.hecho && dia.esHoy && "ring-2 ring-fg ring-inset",
                      )}
                    >
                      {dia.hecho && <IconCheck className="h-4 w-4" />}
                    </span>
                  ) : (
                    // Descanso: un punto, no un círculo, para no confundirlo con un día programado
                    <span className="h-1.5 w-1.5 rounded-full bg-surface-3" />
                  )}
                </span>
              </li>
            );
          })}
        </ol>
      </div>
    </section>
  );
}

// --------------------------------------------------------- sesión de hoy

function TodayHero({ item }: { item: SessionRef }) {
  const unit = useWeightUnit();
  const { session, mesocycleId, mesocycleName, adapted } = item;
  const grupos = groupSets(session.sets);
  const { logged, total } = sessionProgress(session);
  const completada = session.status === "completed";
  const empezada = logged > 0 && !completada;
  const visibles = grupos.slice(0, HERO_MAX_EXERCISES);
  const ocultos = grupos.length - visibles.length;
  const href = `/entrenos/${mesocycleId}/sesion/${session.id}`;

  return (
    <article className="rounded-3xl bg-surface p-5">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="truncate text-sm text-muted">{mesocycleName}</p>
          <p className="mt-0.5 text-xl font-extrabold tracking-tight">
            {grupos.length > 0 ? `${grupos.length} ${grupos.length === 1 ? "ejercicio" : "ejercicios"}` : "Sesión libre"}
          </p>
        </div>
        {completada && (
          <span className="inline-flex shrink-0 items-center gap-1 rounded-full bg-done-soft px-3 py-1 text-sm font-semibold text-done">
            <IconCheck className="h-4 w-4" /> Hecha
          </span>
        )}
      </div>

      {session.wod_format && (
        <p className="mt-3 inline-flex items-center gap-2 rounded-full bg-surface-2 px-3 py-1.5 text-sm font-semibold">
          <IconClock className="h-4 w-4 text-muted" />
          WOD · {WOD_FORMAT_LABELS[session.wod_format]}
          {session.wod_time_cap_seconds ? <span className="num text-muted">{formatSeconds(session.wod_time_cap_seconds)}</span> : null}
        </p>
      )}

      {visibles.length > 0 && (
        <ul className="mt-4">
          {visibles.map((grupo, i) => (
            <ExerciseRow key={`${grupo.name}-${i}`} group={grupo} unit={unit} />
          ))}
        </ul>
      )}
      {ocultos > 0 && <p className="mt-2 text-sm text-muted">+{ocultos} más en la sesión</p>}

      {empezada && (
        <div className="mt-4 flex items-center gap-3">
          <div className="h-1.5 grow overflow-hidden rounded-full bg-surface-2" aria-hidden>
            <div className="h-full rounded-full bg-brand" style={{ width: `${(logged / total) * 100}%` }} />
          </div>
          <span className="num text-sm font-semibold text-muted">
            {logged}/{total}
          </span>
        </div>
      )}

      {adapted && !completada && (
        <p className="mt-4 inline-flex items-center gap-1.5 text-sm text-muted">
          <IconClock className="h-4 w-4" /> Tienes una versión de {adapted.duration_minutes ?? "?"} min
        </p>
      )}

      <Link
        to={href}
        className={cx(
          "press mt-5 flex h-touch-lg w-full items-center justify-center gap-2 rounded-2xl text-lg font-bold",
          completada ? "bg-surface-2 text-fg" : "bg-brand text-on-brand",
        )}
      >
        {completada ? "Ver sesión" : empezada ? `Continuar · ${logged}/${total} series` : "Empezar sesión"}
        <IconChevronRight className="h-5 w-5" />
      </Link>
    </article>
  );
}

/** Fila de ejercicio: nombre a la izquierda, CIFRAS protagonistas a la derecha. */
function ExerciseRow({ group, unit }: { group: ExerciseGroup; unit: WeightUnit }) {
  const primera = group.sets[0];
  const reps = [...new Set(group.sets.map((set) => set.prescribed_reps))];
  const hecho = group.sets.length > 0 && group.sets.every(isSetLogged);
  const carga = loadParts(primera, unit);

  return (
    <li className="flex items-center gap-3 py-3 [&+li]:border-t [&+li]:border-line">
      <span
        aria-hidden
        className={cx(
          "flex h-6 w-6 shrink-0 items-center justify-center rounded-full",
          hecho ? "bg-done text-ink" : "bg-surface-2",
        )}
      >
        {hecho && <IconCheck className="h-3.5 w-3.5" />}
      </span>
      {/* Dos líneas antes que cortar: "Peso muerto rumano" se lee completo en 375px */}
      <span className={cx("line-clamp-2 min-w-0 grow leading-snug font-medium", hecho && "text-muted")}>
        {group.name}
        {hecho && <span className="sr-only"> (hecho)</span>}
      </span>
      <span className="flex shrink-0 items-baseline gap-2 text-right">
        <span className="num text-lg font-extrabold">
          {group.sets.length}×{reps.join("/")}
        </span>
        {carga && (
          <span className="num min-w-[4.5rem] text-lg font-extrabold">
            {carga.value}
            <span className="ml-0.5 text-xs font-semibold text-muted">{carga.unit}</span>
          </span>
        )}
      </span>
    </li>
  );
}

/** La carga de la primera serie separada en cifra y unidad, para darle peso tipográfico a la cifra. */
function loadParts(set: ExerciseGroup["sets"][number] | undefined, unit: WeightUnit): { value: string; unit: string } | null {
  if (!set) return null;
  if (set.prescribed_weight) {
    const v = kgTo(set.prescribed_weight, unit);
    return { value: Number.isInteger(v) ? String(v) : v.toFixed(1), unit };
  }
  if (set.prescribed_percentage) return { value: String(Math.round(set.prescribed_percentage)), unit: "%" };
  return null;
}

function RestDay({ next }: { next?: SessionRef }) {
  return (
    <div className="rounded-3xl bg-surface p-5">
      <div className="flex items-center gap-4">
        <span className="flex h-12 w-12 shrink-0 items-center justify-center rounded-2xl bg-surface-2 text-muted">
          <IconDumbbell className="h-6 w-6" />
        </span>
        <div>
          <p className="text-xl font-extrabold tracking-tight">Hoy descansas</p>
          <p className="text-sm text-muted">Recuperar también es entrenar.</p>
        </div>
      </div>
      {next && (
        <p className="mt-4 text-sm text-muted">
          Próxima sesión: <span className="font-semibold text-fg">{relativeDay(next.session.scheduled_date)}</span>
        </p>
      )}
    </div>
  );
}

function SessionList({ title, items, action }: { title: string; items: SessionRef[]; action?: ReactNode }) {
  return (
    <section>
      <div className="mb-1 flex items-center justify-between">
        <h2 className="label-caps">{title}</h2>
        {action}
      </div>
      <div className={cx("space-y-2", !action && "mt-3")}>
        {items.map((item) => (
          <SessionCard key={item.session.id} session={item.session} mesocycleId={item.mesocycleId} adapted={item.adapted} />
        ))}
      </div>
    </section>
  );
}

// ------------------------------------------------------------- skeleton

/** Misma silueta que la pantalla real: el contenido no "salta" al llegar los datos. */
function TodaySkeleton() {
  return (
    <div className="space-y-8" aria-busy="true" aria-label="Cargando tu entrenamiento">
      <div className="flex items-center gap-5 rounded-3xl bg-surface p-5">
        <Skeleton className="h-[92px] w-[92px] rounded-full" />
        <div className="grow space-y-3">
          <Skeleton className="h-3 w-24" />
          <Skeleton className="h-7 w-full" />
        </div>
      </div>
      <div className="space-y-3">
        <Skeleton className="h-3 w-32" />
        <div className="space-y-4 rounded-3xl bg-surface p-5">
          <Skeleton className="h-6 w-40" />
          {[0, 1, 2].map((i) => (
            <div key={i} className="flex items-center gap-3">
              <Skeleton className="h-6 w-6 rounded-full" />
              <Skeleton className="h-5 grow" />
              <Skeleton className="h-5 w-24" />
            </div>
          ))}
          <Skeleton className="h-touch-lg w-full rounded-2xl" />
        </div>
      </div>
    </div>
  );
}

// -------------------------------------------------------------- fechas

function startOfWeek(iso: string): string {
  const date = parseApiDate(iso);
  const dayOfWeek = (date.getDay() + 6) % 7; // 0 = lunes
  date.setDate(date.getDate() - dayOfWeek);
  return toApiDate(date);
}

function addDays(iso: string, days: number): string {
  const date = parseApiDate(iso);
  date.setDate(date.getDate() + days);
  return toApiDate(date);
}

function capitalize(text: string): string {
  return text.charAt(0).toUpperCase() + text.slice(1);
}
