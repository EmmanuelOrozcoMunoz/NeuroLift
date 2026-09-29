import { useNavigate } from "react-router-dom";

import { IconDumbbell } from "@/components/icons";
import { Button, Card } from "@/components/ui";
import { useCurrentUser } from "@/lib/auth";
import { todayIso } from "@/lib/dates";
import { useCreatePersonalSession } from "@/lib/queries";

/** Crea (o recupera, si ya existía) la sesión propia de una fecha y abre su editor para armar los
 *  ejercicios ahí mismo, sin pasar por el calendario. */
export function useAbrirSesionPropia(onError?: (mensaje: string) => void) {
  const user = useCurrentUser();
  const navigate = useNavigate();
  const crear = useCreatePersonalSession(user.id);

  function abrir(fecha: string) {
    crear.mutate(fecha, {
      onSuccess: (sesion) => navigate(`/entrenos/${sesion.mesocycle_id}/sesion/${sesion.id}/editar`),
      onError: () => onError?.("No se pudo abrir tu entreno. Intenta de nuevo."),
    });
  }

  return { abrir, pendiente: crear.isPending, error: crear.error };
}

/** Atajo en "Hoy": armar (o retomar) el entreno propio de hoy. Sirve con o sin coach. */
export function SesionPropiaCard() {
  const { abrir, pendiente, error } = useAbrirSesionPropia();
  return (
    <Card className="flex items-center gap-4">
      <IconDumbbell className="h-8 w-8 shrink-0 text-brand" aria-hidden />
      <div className="min-w-0 grow">
        <p className="font-bold">Tu propio entreno</p>
        <p className="text-sm text-muted">Arma tus ejercicios de hoy, sin depender de nadie.</p>
        {error && <p className="mt-1 text-sm font-medium text-danger">No se pudo abrir. Intenta de nuevo.</p>}
      </div>
      <Button loading={pendiente} onClick={() => abrir(todayIso())}>
        Armar
      </Button>
    </Card>
  );
}

/** Botón «+ Entreno» de Entrenos: crea (o retoma) la sesión de hoy y abre el editor de una vez. Para
 *  otro día basta tocarlo en el calendario. */
export function NuevaSesionPropiaBoton({ onError }: { onError?: (mensaje: string) => void }) {
  const { abrir, pendiente } = useAbrirSesionPropia(onError);
  return (
    <Button loading={pendiente} onClick={() => abrir(todayIso())}>
      + Entreno
    </Button>
  );
}
