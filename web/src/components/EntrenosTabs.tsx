import { Segmented } from "@/components/ui";

export type VistaDeEntrenos = "lista" | "calendario" | "planes";

/** Las tres vistas de "Entrenos": la lista y el calendario de lo programado, y los planes (las plantillas con las
 *  que se programa). Lo comparten la pantalla de Entrenos y la de Planes, para que sean una sola sección del menú
 *  y no dos botones distintos. Cada pantalla decide qué hace cada opción (cambiar su vista o ir a la otra). */
export function EntrenosTabs({
  activa,
  onElegir,
}: {
  activa: VistaDeEntrenos;
  onElegir: (vista: VistaDeEntrenos) => void;
}) {
  return (
    <Segmented<VistaDeEntrenos>
      value={activa}
      onChange={onElegir}
      options={[
        { value: "lista", label: "Lista" },
        { value: "calendario", label: "Calendario" },
        { value: "planes", label: "Planes" },
      ]}
    />
  );
}
