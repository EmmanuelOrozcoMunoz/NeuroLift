import { useQueryClient } from "@tanstack/react-query";
import { useMemo, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";

import { PageHeader } from "@/components/AppShell";
import { AssignPlanSheet } from "@/components/AssignPlanSheet";
import { CreateMesocycleSheet } from "@/components/CreateMesocycleSheet";
import { EntrenosTabs } from "@/components/EntrenosTabs";
import type { VistaDeEntrenos } from "@/components/EntrenosTabs";
import { IconChevronRight } from "@/components/icons";
import { NewTrainingSheet, rutaDeDiaDeAtleta, rutaDeDiaDeGrupo } from "@/components/NewTrainingSheet";
import type { DestinoDeEntreno } from "@/components/NewTrainingSheet";
import { TrainingCalendar } from "@/components/TrainingCalendar";
import type { CalendarSession } from "@/components/TrainingCalendar";
import { TrainingResultsSheet } from "@/components/TrainingResultsSheet";
import { Badge, Button, EmptyState, ErrorState, LoadingList, Sheet, Toast } from "@/components/ui";
import { blockLabel } from "@/lib/blocks";
import { useAthletes, useCoachTrainings, useGroups } from "@/lib/coachQueries";
import { longDate, monthGrid, parseApiDate, relativeDay, toApiDate, todayIso } from "@/lib/dates";
import type { CoachTrainingItem } from "@/lib/types";

const DIAS_ATRAS_LISTA = 14;
const DIAS_ADELANTE_LISTA = 60;
const DIAS_POR_TANDA_ANTERIORES = 60;

function sumarDias(iso: string, dias: number): string {
  const fecha = parseApiDate(iso);
  fecha.setDate(fecha.getDate() + dias);
  return toApiDate(fecha);
}

function capitalizar(texto: string): string {
  return texto.charAt(0).toUpperCase() + texto.slice(1);
}

/** Adónde lleva editar un entreno: el editor del día del grupo, o el de la sesión del atleta. */
function rutaDelEntreno(item: CoachTrainingItem): string {
  if (item.kind === "group" && item.group_id) {
    return rutaDeDiaDeGrupo(item.group_id, item.program_name ?? "", item.program_start_date, item.date);
  }
  return rutaDeDiaDeAtleta(item.mesocycle_id, item.session_id);
}

function resumenDe(item: CoachTrainingItem): string {
  if (item.is_empty) return "Todavía no tiene contenido";
  const bloques = item.blocks.map((b) => blockLabel(b)).join(" · ");
  const ejercicios = item.exercise_count > 0 ? ` · ${item.exercise_count} ${item.exercise_count === 1 ? "ejercicio" : "ejercicios"}` : "";
  return bloques + ejercicios;
}

function FilaDeEntreno({ item, onClick }: { item: CoachTrainingItem; onClick: () => void }) {
  const esGrupo = item.kind === "group";
  const terminaron = item.athletes_completed;
  return (
    <button
      type="button"
      onClick={onClick}
      className="flex w-full items-center gap-3 rounded-2xl border border-line bg-surface p-4 text-left active:bg-surface-2"
    >
      <div className="min-w-0 grow">
        <div className="flex flex-wrap items-center gap-2">
          <Badge tone={esGrupo ? "brand" : "neutral"}>{esGrupo ? "Grupo" : "Atleta"}</Badge>
          <span className="truncate font-bold">{esGrupo ? item.group_name : item.athlete_name}</span>
          {item.is_draft && <Badge tone="warn">Borrador</Badge>}
        </div>
        <p className="mt-1 truncate text-sm text-muted">{resumenDe(item)}</p>
        {terminaron > 0 && (
          <p className="mt-0.5 text-xs font-semibold text-done">
            🏆 {esGrupo ? `${terminaron} de ${item.athletes_total} lo terminaron` : "Lo terminó"} · ver resultados
          </p>
        )}
      </div>
      <IconChevronRight className="h-5 w-5 shrink-0 text-muted" />
    </button>
  );
}

/** "Entrenos": el centro del coach. Todo lo que programó, para sus grupos y para cada atleta personalizado, en lista
 *  o en calendario; el único lugar desde donde se programa ("+ Nuevo" pregunta qué y para quién); y, al tocar un
 *  entreno que ya terminaron, cómo quedaron sus miembros (el ranking del WOD). Los planes son su tercera vista. */
export default function Trainings() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [params, setParams] = useSearchParams();
  const groups = useGroups();
  const athletes = useAthletes();

  const vista: "lista" | "calendario" = params.get("vista") === "calendario" ? "calendario" : "lista";
  const grupoFiltro = params.get("grupo") ?? "";
  const atletaFiltro = params.get("atleta") ?? "";
  const valorFiltro = grupoFiltro ? `g:${grupoFiltro}` : atletaFiltro ? `a:${atletaFiltro}` : "";

  const hoy = todayIso();
  const [masAtras, setMasAtras] = useState(0);
  const celdasDeHoy = useMemo(() => {
    const ahora = new Date();
    return monthGrid(ahora.getFullYear(), ahora.getMonth());
  }, []);
  const [rangoCalendario, setRangoCalendario] = useState({
    desde: celdasDeHoy[0].iso,
    hasta: celdasDeHoy[celdasDeHoy.length - 1].iso,
  });

  const desdeLista = sumarDias(hoy, -(DIAS_ATRAS_LISTA + masAtras));
  const hastaLista = sumarDias(hoy, DIAS_ADELANTE_LISTA);
  const desde = vista === "lista" ? desdeLista : rangoCalendario.desde;
  const hasta = vista === "lista" ? hastaLista : rangoCalendario.hasta;
  const entrenos = useCoachTrainings(desde, hasta);

  const [nuevo, setNuevo] = useState<{ fecha?: string } | null>(null);
  const [dia, setDia] = useState<string | null>(null);
  const [resultados, setResultados] = useState<CoachTrainingItem | null>(null);
  const [mesociclo, setMesociclo] = useState<DestinoDeEntreno | null>(null);
  const [plan, setPlan] = useState<DestinoDeEntreno | null>(null);
  const [aviso, setAviso] = useState<string | null>(null);

  function cambiarParametros(cambios: Record<string, string | null>) {
    const siguiente = new URLSearchParams(params);
    for (const [clave, valor] of Object.entries(cambios)) {
      if (valor) siguiente.set(clave, valor);
      else siguiente.delete(clave);
    }
    setParams(siguiente, { replace: true });
  }

  function elegirVista(v: VistaDeEntrenos) {
    if (v === "planes") return navigate("/coach/planes");
    cambiarParametros({ vista: v === "calendario" ? "calendario" : null });
  }

  function elegirFiltro(valor: string) {
    cambiarParametros({
      grupo: valor.startsWith("g:") ? valor.slice(2) : null,
      atleta: valor.startsWith("a:") ? valor.slice(2) : null,
    });
  }

  const visibles = useMemo(() => {
    const todos = entrenos.data ?? [];
    if (grupoFiltro) return todos.filter((i) => i.kind === "group" && i.group_id === grupoFiltro);
    if (atletaFiltro) return todos.filter((i) => i.kind === "athlete" && i.athlete_id === atletaFiltro);
    return todos;
  }, [entrenos.data, grupoFiltro, atletaFiltro]);

  const porFecha = useMemo(() => {
    const mapa = new Map<string, CoachTrainingItem[]>();
    for (const item of visibles) mapa.set(item.date, [...(mapa.get(item.date) ?? []), item]);
    return mapa;
  }, [visibles]);

  const marcas: CalendarSession[] = visibles.map((i) => ({
    id: i.session_id,
    mesocycle_id: i.mesocycle_id,
    scheduled_date: i.date,
    status: (i.athletes_total > 0 && i.athletes_completed === i.athletes_total ? "completed" : "pending") as CalendarSession["status"],
  }));

  /** Un entreno que ya alguien terminó muestra cómo quedó; uno sin terminar se abre directo para editarlo. */
  function abrirEntreno(item: CoachTrainingItem) {
    if (item.athletes_completed > 0) setResultados(item);
    else navigate(rutaDelEntreno(item));
  }

  function alTocarUnDia(iso: string) {
    if ((porFecha.get(iso) ?? []).length > 0) setDia(iso);
    else setNuevo({ fecha: iso });
  }

  // Lo que se crea desde las hojas de mesociclo y de plan cambia la lista
  function alCrear(mensaje: string) {
    setAviso(mensaje);
    void queryClient.invalidateQueries({ queryKey: ["coach-trainings"] });
  }

  const itemsDelDia = dia ? (porFecha.get(dia) ?? []) : [];

  return (
    <>
      <PageHeader title="Entrenos" subtitle="Tus grupos y atletas" action={<Button onClick={() => setNuevo({})}>+ Nuevo</Button>} />

      <div className="mb-3 space-y-3">
        <EntrenosTabs activa={vista} onElegir={elegirVista} />
        <select
          value={valorFiltro}
          onChange={(e) => elegirFiltro(e.target.value)}
          aria-label="Ver los entrenos de"
          className="min-h-12 w-full rounded-xl border border-line bg-surface-2 px-3.5 text-fg"
        >
          <option value="">Todos los entrenos</option>
          {(groups.data?.length ?? 0) > 0 && (
            <optgroup label="Grupos">
              {groups.data?.map((g) => (
                <option key={g.id} value={`g:${g.id}`}>
                  {g.name}
                </option>
              ))}
            </optgroup>
          )}
          {(athletes.data ?? []).some((a) => a.coach_id) && (
            <optgroup label="Atletas">
              {(athletes.data ?? [])
                .filter((a) => a.coach_id)
                .map((a) => (
                  <option key={a.id} value={`a:${a.id}`}>
                    {a.full_name}
                  </option>
                ))}
            </optgroup>
          )}
        </select>
      </div>

      {entrenos.isPending && <LoadingList rows={3} />}
      {!entrenos.isPending && entrenos.error && <ErrorState error={entrenos.error} onRetry={() => void entrenos.refetch()} />}

      {vista === "calendario" && !entrenos.error && (
        <>
          <TrainingCalendar
            sessions={marcas}
            onDayTap={alTocarUnDia}
            onVisibleRangeChange={(d, h) =>
              setRangoCalendario((previo) => (previo.desde === d && previo.hasta === h ? previo : { desde: d, hasta: h }))
            }
          />
          <p className="mt-2 text-center text-xs text-muted">Toca un día para ver lo programado o añadir un entreno.</p>
        </>
      )}

      {vista === "lista" && !entrenos.isPending && !entrenos.error && (
        <>
          <div className="mb-2 flex justify-center">
            <button
              type="button"
              onClick={() => setMasAtras((m) => m + DIAS_POR_TANDA_ANTERIORES)}
              className="rounded-xl px-3 py-2 text-sm font-semibold text-brand active:bg-surface-2"
            >
              Ver anteriores
            </button>
          </div>

          {visibles.length === 0 ? (
            <EmptyState title="No hay entrenos en este periodo">
              Programa uno con «+ Nuevo»: eliges qué y si es para un grupo o para un atleta.
            </EmptyState>
          ) : (
            <div className="space-y-5">
              {[...porFecha.entries()].map(([fecha, delDia]) => (
                <section key={fecha}>
                  <p className="mb-2 px-1 text-xs font-semibold tracking-wide text-muted uppercase">
                    {capitalizar(longDate(fecha))} · {relativeDay(fecha)}
                  </p>
                  <div className="space-y-2">
                    {delDia.map((item) => (
                      <FilaDeEntreno key={`${item.kind}-${item.session_id}`} item={item} onClick={() => abrirEntreno(item)} />
                    ))}
                  </div>
                </section>
              ))}
            </div>
          )}
        </>
      )}

      {/* Un día del calendario que ya tiene entrenos: ver cada uno o añadir otro */}
      <Sheet open={dia !== null} onClose={() => setDia(null)} title={dia ? capitalizar(longDate(dia)) : ""}>
        <div className="space-y-3 pb-4">
          {itemsDelDia.map((item) => (
            <FilaDeEntreno
              key={`${item.kind}-${item.session_id}`}
              item={item}
              onClick={() => {
                setDia(null);
                abrirEntreno(item);
              }}
            />
          ))}
          <Button
            full
            variant="secondary"
            onClick={() => {
              const fecha = dia ?? undefined;
              setDia(null);
              setNuevo({ fecha });
            }}
          >
            + Añadir un entreno este día
          </Button>
        </div>
      </Sheet>

      <TrainingResultsSheet
        sessionId={resultados?.session_id ?? null}
        onClose={() => setResultados(null)}
        onEdit={() => {
          const item = resultados;
          setResultados(null);
          if (item) navigate(rutaDelEntreno(item));
        }}
      />

      <NewTrainingSheet
        open={nuevo !== null}
        onClose={() => setNuevo(null)}
        fechaInicial={nuevo?.fecha}
        grupoInicial={grupoFiltro || undefined}
        atletaInicial={atletaFiltro || undefined}
        onMesociclo={setMesociclo}
        onPlan={setPlan}
      />

      {mesociclo && (
        <CreateMesocycleSheet
          open
          onClose={() => setMesociclo(null)}
          target={{ type: mesociclo.type, id: mesociclo.id }}
          onCreated={alCrear}
        />
      )}
      {plan && (
        <AssignPlanSheet
          open
          onClose={() => {
            setPlan(null);
            void queryClient.invalidateQueries({ queryKey: ["coach-trainings"] });
          }}
          group={plan.type === "group" ? { id: plan.id, name: plan.name } : undefined}
          athlete={plan.type === "athlete" ? { id: plan.id, name: plan.name } : undefined}
        />
      )}

      {aviso && <Toast message={aviso} onDismiss={() => setAviso(null)} />}
    </>
  );
}
