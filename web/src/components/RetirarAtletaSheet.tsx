import { Button, Sheet } from "@/components/ui";
import type { AccionPrograma } from "@/lib/types";

/**
 * Pregunta qué hacer con el programa de un atleta que sale. Dos caminos:
 * - conservar su mesociclo (con su historial) como programa individual, o
 * - eliminarlo con todo lo que registró.
 * `alcance` dice desde dónde se retira: del grupo entero, solo de un programa o de la cuenta del coach.
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
  alcance: "grupo" | "programa" | "cuenta";
  onElegir: (accion: AccionPrograma) => void;
  onClose: () => void;
  pendiente: boolean;
}) {
  const delGrupo = alcance === "grupo";
  const deLaCuenta = alcance === "cuenta";
  const titulo = deLaCuenta ? "Sacar de tu cuenta" : delGrupo ? "Quitar del grupo" : "Retirar del programa";
  const pregunta = deLaCuenta
    ? `${nombre} dejará de ser tu atleta y volverá a una cuenta personal. Conserva su cuenta, sus marcas y su historial, y podrá unirse a otro coach con su código. ¿Qué hacemos con los programas que le diste?`
    : delGrupo
      ? `${nombre} dejará de recibir los cambios del grupo. ¿Qué hacemos con sus programas del grupo?`
      : `${nombre} sigue en el grupo, pero deja de recibir los cambios de este programa. ¿Qué hacemos con su mesociclo?`;
  return (
    <Sheet open={nombre !== null} onClose={onClose} title={titulo}>
      <p className="mb-4 text-sm text-muted">{pregunta}</p>
      <div className="space-y-2">
        <Button full loading={pendiente} onClick={() => onElegir("desvincular")}>
          Conservarlo como programa individual
        </Button>
        <p className="px-1 pb-2 text-xs text-muted">
          {deLaCuenta
            ? "Mantiene sus sesiones y lo que ya registró; solo deja de ser tuyo."
            : "Mantiene sus sesiones y lo que ya registró; solo deja de ser del grupo."}
        </p>
        <Button
          full
          variant="danger"
          disabled={pendiente}
          onClick={() => {
            const aviso = deLaCuenta
              ? `Se borrarán los programas que le diste a ${nombre}, con todo lo que registró en ellos. ¿Eliminarlos?`
              : `Se borrará el mesociclo de ${nombre} con todo lo que registró. ¿Eliminarlo?`;
            if (window.confirm(aviso)) {
              onElegir("eliminar");
            }
          }}
        >
          {deLaCuenta ? "Eliminar sus programas" : "Eliminar su mesociclo"}
        </Button>
        <Button full variant="ghost" onClick={onClose}>
          Cancelar
        </Button>
      </div>
    </Sheet>
  );
}
