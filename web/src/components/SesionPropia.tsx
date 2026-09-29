import { useState } from "react";
import { useNavigate } from "react-router-dom";

import { IconDumbbell } from "@/components/icons";
import { Button, Card, ErrorState, Field, Sheet } from "@/components/ui";
import { useCurrentUser } from "@/lib/auth";
import { todayIso } from "@/lib/dates";
import { useCreatePersonalSession } from "@/lib/queries";

/** Crea (o recupera, si ya existía) la sesión propia de una fecha y abre su editor para armar los
 *  ejercicios ahí mismo, sin pasar por el calendario. */
export function useAbrirSesionPropia() {
  const user = useCurrentUser();
  const navigate = useNavigate();
  const crear = useCreatePersonalSession(user.id);

  function abrir(fecha: string) {
    crear.mutate(fecha, {
      onSuccess: (sesion) => navigate(`/entrenos/${sesion.mesocycle_id}/sesion/${sesion.id}/editar`),
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

/** Botón «+ Sesión» de Entrenos: elige la fecha (hoy por defecto) y abre el editor. */
export function NuevaSesionPropiaBoton() {
  const [abierto, setAbierto] = useState(false);
  const [fecha, setFecha] = useState(todayIso());
  const { abrir, pendiente, error } = useAbrirSesionPropia();

  return (
    <>
      <Button
        onClick={() => {
          setFecha(todayIso());
          setAbierto(true);
        }}
      >
        + Sesión
      </Button>
      <Sheet open={abierto} onClose={() => setAbierto(false)} title="Armar una sesión propia">
        <p className="mb-4 text-sm text-muted">
          Elige el día y arma tus ejercicios. Si ya tenías una sesión propia ese día, la retomas.
        </p>
        <Field label="Fecha" type="date" value={fecha} onChange={(e) => setFecha(e.target.value)} />
        {error && <ErrorState error={error} />}
        <Button full className="mt-4" loading={pendiente} disabled={!fecha} onClick={() => abrir(fecha)}>
          Crear y armar ejercicios
        </Button>
      </Sheet>
    </>
  );
}
