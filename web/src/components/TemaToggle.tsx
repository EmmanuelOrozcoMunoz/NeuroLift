import { Segmented } from "@/components/ui";
import { setTema, useTema } from "@/lib/theme";
import type { Tema } from "@/lib/theme";

/** Oscuro (por defecto, pensado para el gimnasio), claro o el del sistema. Es de este dispositivo, no de la
 *  cuenta: se guarda en el navegador (ver lib/theme.ts). */
export function TemaToggle() {
  const tema = useTema();
  return (
    <div>
      <span className="mb-1.5 block text-sm font-medium text-muted">Tema</span>
      <Segmented<Tema>
        value={tema}
        onChange={setTema}
        options={[
          { value: "oscuro", label: "Oscuro" },
          { value: "claro", label: "Claro" },
          { value: "sistema", label: "Automático" },
        ]}
      />
      <p className="mt-1.5 text-xs text-muted">Se guarda en este dispositivo. Automático sigue el modo de tu teléfono.</p>
    </div>
  );
}
