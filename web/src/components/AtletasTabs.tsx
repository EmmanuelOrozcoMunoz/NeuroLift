import { useNavigate } from "react-router-dom";

import { Segmented } from "@/components/ui";

export type VistaDeAtletas = "atletas" | "grupos" | "ranking";

/** Las tres vistas de "Atletas": la lista (con su actividad de la semana), los grupos y el ranking del box. Lo
 *  comparten la lista de atletas y la de grupos, para que sean una sola sección del menú y no tres botones. */
export function AtletasTabs({ activa }: { activa: VistaDeAtletas }) {
  const navigate = useNavigate();
  return (
    <Segmented<VistaDeAtletas>
      value={activa}
      onChange={(v) => {
        if (v === activa) return;
        navigate(v === "grupos" ? "/coach/grupos" : v === "ranking" ? "/coach/atletas?vista=ranking" : "/coach/atletas");
      }}
      options={[
        { value: "atletas", label: "Atletas" },
        { value: "grupos", label: "Grupos" },
        { value: "ranking", label: "Leaderboard" },
      ]}
    />
  );
}
