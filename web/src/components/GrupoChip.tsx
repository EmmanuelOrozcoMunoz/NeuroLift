import { useState } from "react";

import { Sheet } from "@/components/ui";
import { useMyGroups } from "@/lib/myGroups";
import type { MyGroup } from "@/lib/myGroups";
import { useProtectedImageUrl } from "@/lib/useImageUrl";

function iniciales(nombre: string): string {
  const partes = nombre.trim().split(/\s+/).filter(Boolean);
  return ((partes[0]?.[0] ?? "") + (partes[1]?.[0] ?? "")).toUpperCase() || "G";
}

/** La portada del grupo, o sus iniciales si no tiene. */
function InsigniaDeGrupo({ grupo, className }: { grupo: MyGroup; className: string }) {
  const url = useProtectedImageUrl(`/users/me/groups/${grupo.id}/cover`, grupo.has_cover_image);
  if (url) return <img src={url} alt="" className={`${className} shrink-0 rounded-full object-cover`} />;
  return (
    <span
      aria-hidden
      className={`${className} flex shrink-0 items-center justify-center rounded-full bg-brand-soft text-[11px] font-bold text-brand`}
    >
      {iniciales(grupo.name)}
    </span>
  );
}

/**
 * El grupo del atleta, arriba a la derecha: su portada (o iniciales) y el nombre. Si está en varios, muestra
 * el primero con "+N"; al tocarlo se ven todos, con su coach. No se pinta si el atleta no está en ningún grupo.
 */
export function GrupoChip() {
  const grupos = useMyGroups();
  const [abierto, setAbierto] = useState(false);
  const lista = grupos.data ?? [];
  if (lista.length === 0) return null;
  const [primero, ...resto] = lista;

  return (
    <>
      <button
        type="button"
        onClick={() => setAbierto(true)}
        aria-label={lista.length === 1 ? `Tu grupo: ${primero.name}` : `Tus grupos: ${lista.map((g) => g.name).join(", ")}`}
        className="flex max-w-36 min-h-11 items-center gap-2 rounded-full bg-surface-2 py-1 pr-3 pl-1 active:opacity-80"
      >
        <InsigniaDeGrupo grupo={primero} className="h-8 w-8" />
        <span className="min-w-0 truncate text-sm font-semibold">{primero.name}</span>
        {resto.length > 0 && <span className="shrink-0 text-xs font-semibold text-muted">+{resto.length}</span>}
      </button>

      <Sheet open={abierto} onClose={() => setAbierto(false)} title={lista.length === 1 ? "Tu grupo" : "Tus grupos"}>
        <ul className="space-y-2 pb-4">
          {lista.map((g) => (
            <li key={g.id} className="flex items-center gap-3 rounded-2xl border border-line bg-surface p-3">
              <InsigniaDeGrupo grupo={g} className="h-12 w-12" />
              <div className="min-w-0">
                <p className="font-bold break-words">{g.name}</p>
                {g.coach_name && <p className="text-sm text-muted">Coach: {g.coach_name}</p>}
              </div>
            </li>
          ))}
        </ul>
      </Sheet>
    </>
  );
}
