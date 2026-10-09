import { useState } from "react";
import type { ReactNode } from "react";

import { IconChevronRight, IconTrash } from "@/components/icons";
import { Card } from "@/components/ui";
import { blockLabel } from "@/lib/blocks";
import type { TrainingSession } from "@/lib/types";

/**
 * Lo que el coach ajusta de UN día aparte de sus ejercicios: pautas de calentamiento y orden de
 * los bloques. Lo comparten el editor de sesiones (mesociclos y entrenos propios) y el de planes:
 * cada uno solo dice CÓMO se guarda (`guardar`), porque un plan no tiene dueño y usa otro
 * endpoint (ver useUpdateSessionMeta / useUpdatePlanSessionMeta).
 */
export interface MetaGuardado {
  /** Guarda los campos que vengan en `body`; `alTerminar` se llama solo si salió bien. */
  guardar: (body: { block_order?: string | null; warmup_notes?: string | null }, alTerminar: () => void) => void;
  guardando: boolean;
}

/** Con `integrado` se dibuja sin su propia tarjeta, para ir dentro de otra (el día de un plan). */
function Envoltorio({ integrado, children }: { integrado?: boolean; children: ReactNode }) {
  return integrado ? <div className="border-b border-line pb-3">{children}</div> : <Card>{children}</Card>;
}

/** Pautas de calentamiento/aproximaciones que el coach escribe como TEXTO para esta sesión. Vive
 *  DENTRO del bloque Calentamiento (igual que el texto del WOD dentro del Metabólico), así que
 *  sigue al bloque si se reordena, y el atleta lo ve bajo el título del bloque. Convive con los
 *  ejercicios estructurados que ya tenga ese bloque. Guarda al perder el foco, sin botón aparte. */
export function WarmupNotesCard({
  session,
  meta,
  onSaved,
  onRemoved,
}: {
  session: TrainingSession;
  meta: MetaGuardado;
  onSaved: () => void;
  /** Se llama al quitar el texto, para que el editor deje de forzar el bloque si no tiene ejercicios. */
  onRemoved: () => void;
}) {
  const [texto, setTexto] = useState(session.warmup_notes ?? "");

  function guardar() {
    if (texto === (session.warmup_notes ?? "")) return;
    meta.guardar({ warmup_notes: texto.trim() || "" }, onSaved);
  }

  function quitar() {
    if (texto.trim() && !window.confirm("¿Borrar el texto del calentamiento?")) return;
    setTexto("");
    if (session.warmup_notes) meta.guardar({ warmup_notes: "" }, () => {});
    onRemoved();
  }

  return (
    <Card>
      <div className="mb-2 flex items-center justify-between gap-2">
        <p className="text-sm font-semibold text-muted">📋 Escribir el calentamiento como texto (opcional)</p>
        <button
          type="button"
          onClick={quitar}
          className="rounded-lg p-1.5 text-danger active:bg-danger/10"
          aria-label="Borrar el texto del calentamiento"
        >
          <IconTrash className="h-4 w-4" />
        </button>
      </div>
      <textarea
        rows={4}
        maxLength={1000}
        value={texto}
        onChange={(e) => setTexto(e.target.value)}
        onBlur={guardar}
        placeholder="Ej. 5 min de movilidad de cadera, 3 series de aproximación subiendo desde 40% hasta el primer set de trabajo..."
        className="w-full rounded-xl border border-line bg-surface-2 p-3 text-sm text-fg placeholder:text-muted/50 focus:border-brand focus:outline-none"
      />
    </Card>
  );
}

/** El orden en que se muestran los bloques de ESTA sesión — el coach lo sube/baja con flechas
 *  (nada de drag-and-drop: más fácil de acertar con el dedo). Solo aparece si hay 2+ bloques. */
export function BlockOrderEditor({
  blockKeys,
  meta,
  onSaved,
  integrado,
}: {
  blockKeys: string[];
  meta: MetaGuardado;
  onSaved: () => void;
  integrado?: boolean;
}) {
  function move(index: number, delta: number) {
    const target = index + delta;
    if (target < 0 || target >= blockKeys.length) return;
    const next = [...blockKeys];
    [next[index], next[target]] = [next[target], next[index]];
    meta.guardar({ block_order: next.join(",") }, onSaved);
  }

  if (blockKeys.length < 2) return null;

  return (
    <Envoltorio integrado={integrado}>
      <p className="mb-2 text-sm font-semibold text-muted">🔀 Orden de los bloques</p>
      <div className="space-y-1.5">
        {blockKeys.map((key, index) => (
          <div key={key} className="flex items-center justify-between rounded-xl bg-surface-2 px-3 py-2">
            <span className="text-sm font-medium">{blockLabel(key)}</span>
            <div className="flex gap-1">
              <button
                type="button"
                aria-label={`Subir ${blockLabel(key)}`}
                disabled={index === 0 || meta.guardando}
                onClick={() => move(index, -1)}
                className="rounded-lg p-1.5 text-muted disabled:opacity-30 active:bg-line"
              >
                <IconChevronRight className="h-4 w-4 -rotate-90" />
              </button>
              <button
                type="button"
                aria-label={`Bajar ${blockLabel(key)}`}
                disabled={index === blockKeys.length - 1 || meta.guardando}
                onClick={() => move(index, 1)}
                className="rounded-lg p-1.5 text-muted disabled:opacity-30 active:bg-line"
              >
                <IconChevronRight className="h-4 w-4 rotate-90" />
              </button>
            </div>
          </div>
        ))}
      </div>
    </Envoltorio>
  );
}
