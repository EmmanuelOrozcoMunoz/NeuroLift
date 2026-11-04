import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";

import { Button, Field, Segmented, Sheet } from "@/components/ui";
import { useAthletes, useCreateAthleteDay, useCreateGroupDay, useGroups } from "@/lib/coachQueries";
import { todayIso } from "@/lib/dates";

type Destino = "grupo" | "atleta";

const selectClass = "min-h-12 w-full rounded-xl border border-line bg-surface-2 px-3.5 text-fg";

/** Ruta del editor de un día de un grupo: el programa se identifica por su nombre y fecha de inicio, y la fecha
 *  llega abierta. */
export function rutaDeDiaDeGrupo(groupId: string, programName: string, programStartDate: string, fecha: string) {
  return `/coach/grupos/${groupId}/programas/${encodeURIComponent(programName)}/${programStartDate}?fecha=${fecha}`;
}

/** Ruta del editor de un día de un atleta. */
export function rutaDeDiaDeAtleta(mesocycleId: string, sessionId: string) {
  return `/coach/mesociclos/${mesocycleId}/sesion/${sessionId}`;
}

/** "Nuevo entreno": se elige la fecha y PARA QUIÉN es (un grupo, o un atleta personalizado); se crea el día y se
 *  abre su editor. Es el único lugar desde donde se programa un día, para que no haya un calendario por cada grupo
 *  y por cada atleta. */
export function NewTrainingSheet({
  open,
  onClose,
  fechaInicial,
  grupoInicial,
  atletaInicial,
}: {
  open: boolean;
  onClose: () => void;
  fechaInicial?: string;
  grupoInicial?: string;
  atletaInicial?: string;
}) {
  const navigate = useNavigate();
  const groups = useGroups();
  const athletes = useAthletes();
  const [fecha, setFecha] = useState(fechaInicial ?? todayIso());
  const [destino, setDestino] = useState<Destino>(atletaInicial ? "atleta" : "grupo");
  const [grupoId, setGrupoId] = useState(grupoInicial ?? "");
  const [atletaId, setAtletaId] = useState(atletaInicial ?? "");
  const [error, setError] = useState<string | null>(null);

  // Cada vez que se abre, parte de lo que se le pasó (el día tocado, o el grupo/atleta que se está viendo)
  useEffect(() => {
    if (!open) return;
    setFecha(fechaInicial ?? todayIso());
    setDestino(atletaInicial ? "atleta" : "grupo");
    setGrupoId(grupoInicial ?? "");
    setAtletaId(atletaInicial ?? "");
    setError(null);
  }, [open, fechaInicial, grupoInicial, atletaInicial]);

  const createGroupDay = useCreateGroupDay(grupoId || "none");
  const createAthleteDay = useCreateAthleteDay(atletaId || "none");

  // Los mesociclos y los días son solo de atletas con coach personal
  const atletas = (athletes.data ?? []).filter((a) => a.coach_id);
  const ocupado = createGroupDay.isPending || createAthleteDay.isPending;

  function programar() {
    setError(null);
    if (!fecha) return setError("Elige la fecha.");
    const alFallar = (err: unknown) => setError(err instanceof Error ? err.message : "No se pudo programar el entreno.");

    if (destino === "grupo") {
      if (!grupoId) return setError("Elige el grupo.");
      createGroupDay.mutate(fecha, {
        onSuccess: (r) => {
          onClose();
          navigate(rutaDeDiaDeGrupo(grupoId, r.program_name, r.program_start_date, r.scheduled_date));
        },
        onError: alFallar,
      });
    } else {
      if (!atletaId) return setError("Elige el atleta.");
      createAthleteDay.mutate(fecha, {
        onSuccess: (r) => {
          onClose();
          navigate(rutaDeDiaDeAtleta(r.mesocycle_id, r.session_id));
        },
        onError: alFallar,
      });
    }
  }

  return (
    <Sheet open={open} onClose={onClose} title="Nuevo entreno">
      <div className="space-y-4 pb-4">
        <Field label="¿Qué día?" type="date" value={fecha} onChange={(e) => setFecha(e.target.value)} />

        <div>
          <span className="mb-1.5 block text-sm font-medium text-muted">¿Para quién es?</span>
          <Segmented<Destino>
            value={destino}
            onChange={setDestino}
            options={[
              { value: "grupo", label: "Un grupo" },
              { value: "atleta", label: "Un atleta" },
            ]}
          />
        </div>

        {destino === "grupo" ? (
          <label className="block">
            <span className="mb-1.5 block text-sm font-medium text-muted">Grupo</span>
            <select value={grupoId} onChange={(e) => setGrupoId(e.target.value)} className={selectClass}>
              <option value="">Elige un grupo…</option>
              {groups.data?.map((g) => (
                <option key={g.id} value={g.id}>
                  {g.name} ({g.member_count})
                </option>
              ))}
            </select>
            {groups.data?.length === 0 && (
              <span className="mt-1 block text-xs text-muted">Todavía no tienes grupos: créalos en Programar → Grupos.</span>
            )}
          </label>
        ) : (
          <label className="block">
            <span className="mb-1.5 block text-sm font-medium text-muted">Atleta</span>
            <select value={atletaId} onChange={(e) => setAtletaId(e.target.value)} className={selectClass}>
              <option value="">Elige un atleta…</option>
              {atletas.map((a) => (
                <option key={a.id} value={a.id}>
                  {a.full_name}
                </option>
              ))}
            </select>
            {athletes.data && atletas.length === 0 && (
              <span className="mt-1 block text-xs text-muted">No tienes atletas con coach personal todavía.</span>
            )}
          </label>
        )}

        {error && <p className="text-sm font-medium text-danger">{error}</p>}
        <Button full loading={ocupado} onClick={programar}>
          Programar y abrir
        </Button>
        <p className="text-center text-xs text-muted">
          Se crea el día vacío y se abre para que lo escribas bloque por bloque.
        </p>
      </div>
    </Sheet>
  );
}
