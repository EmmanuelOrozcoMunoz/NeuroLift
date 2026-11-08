import { useMemo, useState } from "react";

import { IconChevronRight } from "@/components/icons";
import { Badge } from "@/components/ui";
import { blockLabel } from "@/lib/blocks";
import { longDate, relativeDay } from "@/lib/dates";
import type { CoachTrainingItem } from "@/lib/types";

/** Cuántos entrenos próximos se ven de entrada dentro de cada grupo; el resto, tras «Ver más». */
const PROXIMOS_VISIBLES = 4;
const ID_DE_PERSONALIZADOS = "personalizados";

function capitalizar(texto: string): string {
  return texto.charAt(0).toUpperCase() + texto.slice(1);
}

function resumenDe(item: CoachTrainingItem): string {
  if (item.is_empty) return "Todavía no tiene contenido";
  const bloques = item.blocks.map((b) => blockLabel(b)).join(" · ");
  const ejercicios = item.exercise_count > 0 ? ` · ${item.exercise_count} ${item.exercise_count === 1 ? "ejercicio" : "ejercicios"}` : "";
  return bloques + ejercicios;
}

/** «Ana, Beto y 2 más» */
function nombresDe(nombres: string[]): string {
  const primeros = nombres.slice(0, 2).map((n) => n.split(" ")[0]);
  const resto = nombres.length - primeros.length;
  if (resto <= 0) return primeros.length > 1 ? `${primeros.slice(0, -1).join(", ")} y ${primeros[primeros.length - 1]}` : primeros[0];
  return `${primeros.join(", ")} y ${resto} más`;
}

/**
 * Un entreno programado: qué trae, quiénes lo terminaron y, si alguien lo terminó, un botón para ver el ranking.
 * `enfoque` dice qué va de título: la fecha (dentro de la tarjeta de un grupo) o a quién pertenece (en el calendario).
 * Tocar el cuerpo abre el editor; el ranking tiene su propio botón.
 */
export function FilaDeEntreno({
  item,
  enfoque,
  hoy,
  onEditar,
  onRanking,
}: {
  item: CoachTrainingItem;
  enfoque: "fecha" | "quien";
  hoy: string;
  onEditar: () => void;
  onRanking: () => void;
}) {
  const esGrupo = item.kind === "group";
  const terminaron = item.athletes_completed;
  const yaPaso = item.date <= hoy;
  return (
    <div className="overflow-hidden rounded-2xl border border-line bg-surface">
      <button type="button" onClick={onEditar} className="flex w-full items-center gap-3 p-4 text-left active:bg-surface-2">
        <div className="min-w-0 grow">
          {enfoque === "quien" ? (
            <div className="flex flex-wrap items-center gap-2">
              <Badge tone={esGrupo ? "brand" : "neutral"}>{esGrupo ? "Grupo" : "Atleta"}</Badge>
              <span className="truncate font-bold">{esGrupo ? item.group_name : item.athlete_name}</span>
              {item.is_draft && <Badge tone="warn">Borrador</Badge>}
            </div>
          ) : (
            <div className="flex flex-wrap items-center gap-x-2 gap-y-1">
              <span className="font-bold">{capitalizar(longDate(item.date))}</span>
              <span className="text-xs font-semibold text-muted">{relativeDay(item.date)}</span>
              {item.is_draft && <Badge tone="warn">Borrador</Badge>}
            </div>
          )}
          {enfoque === "fecha" && !esGrupo && item.athlete_name && (
            <p className="mt-1 truncate text-sm font-semibold">{item.athlete_name}</p>
          )}
          <p className="mt-1 text-sm break-words text-muted">{resumenDe(item)}</p>

          {terminaron > 0 ? (
            <p className="mt-1.5 text-xs font-semibold break-words text-done">
              ✓ {esGrupo ? `${terminaron} de ${item.athletes_total}: ${nombresDe(item.completed_names)}` : "Lo terminó"}
            </p>
          ) : (
            yaPaso &&
            !item.is_empty && (
              <p className="mt-1.5 text-xs text-muted">{esGrupo ? "Nadie lo ha terminado todavía" : "Aún no lo termina"}</p>
            )
          )}
        </div>
        <IconChevronRight className="h-5 w-5 shrink-0 text-muted" />
      </button>
      {terminaron > 0 && (
        <button
          type="button"
          onClick={onRanking}
          className="flex min-h-11 w-full items-center justify-center gap-2 border-t border-line bg-done-soft/40 text-sm font-semibold text-done active:bg-done-soft"
        >
          🏆 Ver ranking
        </button>
      )}
    </div>
  );
}

interface Seccion {
  id: string;
  titulo: string;
  esGrupo: boolean;
  proximos: CoachTrainingItem[];
  anteriores: CoachTrainingItem[];
  deHoy: CoachTrainingItem[];
}

function agrupar(items: CoachTrainingItem[], hoy: string): Seccion[] {
  const mapa = new Map<string, Seccion>();
  for (const item of items) {
    const esGrupo = item.kind === "group" && item.group_id !== null;
    const id = esGrupo ? (item.group_id as string) : ID_DE_PERSONALIZADOS;
    let seccion = mapa.get(id);
    if (!seccion) {
      seccion = {
        id,
        titulo: esGrupo ? (item.group_name ?? "Grupo") : "Atletas personalizados",
        esGrupo,
        proximos: [],
        anteriores: [],
        deHoy: [],
      };
      mapa.set(id, seccion);
    }
    if (item.date === hoy) seccion.deHoy.push(item);
    if (item.date >= hoy) seccion.proximos.push(item);
    else seccion.anteriores.push(item);
  }
  for (const s of mapa.values()) {
    s.proximos.sort((a, b) => a.date.localeCompare(b.date));
    s.anteriores.sort((a, b) => b.date.localeCompare(a.date)); // el más reciente primero
  }
  // Primero los grupos con entreno hoy, luego por nombre; los personalizados al final
  return [...mapa.values()].sort((a, b) => {
    if (a.id === ID_DE_PERSONALIZADOS) return 1;
    if (b.id === ID_DE_PERSONALIZADOS) return -1;
    if ((a.deHoy.length > 0) !== (b.deHoy.length > 0)) return a.deHoy.length > 0 ? -1 : 1;
    return a.titulo.localeCompare(b.titulo, "es");
  });
}

/** Lo que se ve con la tarjeta cerrada: cómo va el entreno de hoy (y quiénes ya lo terminaron) o cuál es el próximo. */
function resumenDeSeccion(s: Seccion): { texto: string; quienes: string[] } {
  const hoyConGente = s.deHoy.filter((i) => i.athletes_total > 0);
  if (hoyConGente.length > 0) {
    const total = hoyConGente.reduce((n, i) => n + i.athletes_total, 0);
    const listos = hoyConGente.reduce((n, i) => n + i.athletes_completed, 0);
    return { texto: `Hoy: ${listos} de ${total} lo terminaron`, quienes: hoyConGente.flatMap((i) => i.completed_names) };
  }
  const siguiente = s.proximos[0];
  if (siguiente) return { texto: `Próximo: ${relativeDay(siguiente.date)}`, quienes: [] };
  return { texto: "Sin entrenos próximos", quienes: [] };
}

/**
 * La lista de entrenos del coach, separada por grupo: una tarjeta por grupo (y una para los atletas
 * personalizados) que se abre y se cierra. Dentro, lo próximo primero y lo anterior plegado. En cada
 * entreno se ve quién lo terminó y se abre su ranking.
 */
export function ListaDeEntrenos({
  items,
  hoy,
  onEditar,
  onRanking,
}: {
  items: CoachTrainingItem[];
  hoy: string;
  onEditar: (item: CoachTrainingItem) => void;
  onRanking: (item: CoachTrainingItem) => void;
}) {
  const secciones = useMemo(() => agrupar(items, hoy), [items, hoy]);
  // Lo que el coach abrió o cerró a mano; el resto usa el valor por defecto
  const [manual, setManual] = useState<Record<string, boolean>>({});
  const [conTodos, setConTodos] = useState<Record<string, boolean>>({});
  const [conAnteriores, setConAnteriores] = useState<Record<string, boolean>>({});

  // Con varios grupos, todos cerrados: la cabecera ya dice cómo va hoy y se ven todos de un vistazo
  const abiertaPorDefecto = () => secciones.length === 1;

  return (
    <div className="space-y-3">
      {secciones.map((s) => {
        const abierta = manual[s.id] ?? abiertaPorDefecto();
        const resumen = resumenDeSeccion(s);
        const verTodos = conTodos[s.id] ?? false;
        const proximos = verTodos ? s.proximos : s.proximos.slice(0, PROXIMOS_VISIBLES);
        const ocultos = s.proximos.length - proximos.length;
        return (
          <section key={s.id} className="overflow-hidden rounded-2xl border border-line bg-surface-2/40">
            <button
              type="button"
              aria-expanded={abierta}
              onClick={() => setManual((m) => ({ ...m, [s.id]: !abierta }))}
              className="flex w-full items-center gap-3 p-4 text-left active:bg-surface-2"
            >
              <div className="min-w-0 grow">
                <div className="flex flex-wrap items-center gap-2">
                  <Badge tone={s.esGrupo ? "brand" : "neutral"}>{s.esGrupo ? "Grupo" : "Individual"}</Badge>
                  <span className="truncate text-base font-bold">{s.titulo}</span>
                </div>
                <p className="mt-1 text-sm text-muted">
                  {resumen.texto} · {s.proximos.length} {s.proximos.length === 1 ? "próximo" : "próximos"}
                </p>
                {resumen.quienes.length > 0 && (
                  <p className="mt-0.5 text-xs font-semibold break-words text-done">✓ {nombresDe(resumen.quienes)}</p>
                )}
              </div>
              <IconChevronRight className={`h-5 w-5 shrink-0 text-muted transition-transform ${abierta ? "rotate-90" : ""}`} />
            </button>

            {abierta && (
              <div className="space-y-2 border-t border-line p-3">
                {s.proximos.length === 0 && <p className="px-1 py-2 text-sm text-muted">No hay entrenos próximos en este periodo.</p>}
                {proximos.map((item) => (
                  <FilaDeEntreno
                    key={`${item.kind}-${item.session_id}`}
                    item={item}
                    enfoque="fecha"
                    hoy={hoy}
                    onEditar={() => onEditar(item)}
                    onRanking={() => onRanking(item)}
                  />
                ))}
                {ocultos > 0 && (
                  <button
                    type="button"
                    onClick={() => setConTodos((m) => ({ ...m, [s.id]: true }))}
                    className="w-full rounded-xl py-2 text-sm font-semibold text-brand active:bg-surface-2"
                  >
                    Ver {ocultos} más
                  </button>
                )}

                {s.anteriores.length > 0 && (
                  <div className="pt-1">
                    <button
                      type="button"
                      aria-expanded={conAnteriores[s.id] ?? false}
                      onClick={() => setConAnteriores((m) => ({ ...m, [s.id]: !(m[s.id] ?? false) }))}
                      className="flex w-full items-center justify-between rounded-xl px-1 py-2 text-sm font-semibold text-muted active:bg-surface-2"
                    >
                      <span>
                        Anteriores ({s.anteriores.length})
                      </span>
                      <IconChevronRight className={`h-4 w-4 transition-transform ${conAnteriores[s.id] ? "rotate-90" : ""}`} />
                    </button>
                    {conAnteriores[s.id] && (
                      <div className="mt-1 space-y-2">
                        {s.anteriores.map((item) => (
                          <FilaDeEntreno
                            key={`${item.kind}-${item.session_id}`}
                            item={item}
                            enfoque="fecha"
                            hoy={hoy}
                            onEditar={() => onEditar(item)}
                            onRanking={() => onRanking(item)}
                          />
                        ))}
                      </div>
                    )}
                  </div>
                )}
              </div>
            )}
          </section>
        );
      })}
    </div>
  );
}
