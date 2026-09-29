import { Button, Sheet } from "@/components/ui";
import type { AccionPrograma } from "@/lib/types";

/**
 * Pregunta qué hacer con el programa de un atleta que sale. Dos caminos:
 * - conservar su mesociclo (con su historial) como programa individual, o
 * - eliminarlo con todo lo que registró.
 * `alcance` dice desde dónde se retira: del grupo entero o solo de un programa.
 */
export function RetirarAtletaSheet({
  nombre,
  alcance,
  onElegir,
  onClose,
  pendiente,
}: {
  /** null = cerrado */
  nombre: string | null;
  alcance: "grupo" | "programa";
  onElegir: (accion: AccionPrograma) => void;
  onClose: () => void;
  pendiente: boolean;
}) {
  const delGrupo = alcance === "grupo";
  return (
    <Sheet open={nombre !== null} onClose={onClose} title={delGrupo ? "Quitar del grupo" : "Retirar del programa"}>
      <p className="mb-4 text-sm text-muted">
        {delGrupo
          ? `${nombre} dejará de recibir los cambios del grupo. ¿Qué hacemos con sus programas del grupo?`
          : `${nombre} sigue en el grupo, pero deja de recibir los cambios de este programa. ¿Qué hacemos con su mesociclo?`}
      </p>
      <div className="space-y-2">
        <Button full loading={pendiente} onClick={() => onElegir("desvincular")}>
          Conservarlo como programa individual
        </Button>
        <p className="px-1 pb-2 text-xs text-muted">Mantiene sus sesiones y lo que ya registró; solo deja de ser del grupo.</p>
        <Button
          full
          variant="danger"
          disabled={pendiente}
          onClick={() => {
            if (window.confirm(`Se borrará el mesociclo de ${nombre} con todo lo que registró. ¿Eliminarlo?`)) {
              onElegir("eliminar");
            }
          }}
        >
          Eliminar su mesociclo
        </Button>
        <Button full variant="ghost" onClick={onClose}>
          Cancelar
        </Button>
      </div>
    </Sheet>
  );
}
