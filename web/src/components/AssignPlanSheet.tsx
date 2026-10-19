import { useState } from "react";

import { Button, Field, Segmented, Sheet } from "@/components/ui";
import { useAssignPlanToAthlete, useAssignPlanToGroup, useAthletes, useGroups, useMyPlans } from "@/lib/coachQueries";
import { todayIso } from "@/lib/dates";
import type { GroupPlanAssignResponse } from "@/lib/types";

type Elegible = { id: string; name: string };

const selectClass = "min-h-12 w-full rounded-xl border border-line bg-surface-2 px-3.5 text-fg";

type Destino = "grupo" | "atleta";

/** Asigna una plantilla a un grupo o a un solo atleta. Se abre desde un plan (elige a quién), desde un
 *  grupo o desde un atleta (elige el plan): lo que ya viene fijo no se pregunta. Las cargas en % se calculan con las marcas
 *  de cada atleta; si a alguien le falta una marca, se le avisa al entrenador. */
export function AssignPlanSheet({
  open,
  onClose,
  plan,
  group,
  athlete,
}: {
  open: boolean;
  onClose: () => void;
  plan?: Elegible;
  group?: Elegible;
  athlete?: Elegible;
}) {
  const plans = useMyPlans();
  const groups = useGroups();
  const athletes = useAthletes();
  const assignGroup = useAssignPlanToGroup();
  const assignAthlete = useAssignPlanToAthlete();
  const [destino, setDestino] = useState<Destino>("grupo");
  const [athleteId, setAthleteId] = useState("");
  const [planId, setPlanId] = useState("");
  const [groupId, setGroupId] = useState("");
  const [startDate, setStartDate] = useState(todayIso());
  const [error, setError] = useState<string | null>(null);
  const [resultado, setResultado] = useState<GroupPlanAssignResponse | null>(null);

  const planElegido = plan?.id ?? planId;
  const grupoElegido = group?.id ?? groupId;
  const atletaElegido = athlete?.id ?? athleteId;
  // Si viene un grupo o un atleta fijo, el destino ya está decidido.
  const destinoFinal: Destino = athlete ? "atleta" : group ? "grupo" : destino;
  const assign = destinoFinal === "atleta" ? assignAthlete : assignGroup;

  function cerrar() {
    setResultado(null);
    setError(null);
    onClose();
  }

  function asignar() {
    setError(null);
    if (!planElegido) return setError("Elige un plan.");
    if (destinoFinal === "grupo" && !grupoElegido) return setError("Elige un grupo.");
    if (destinoFinal === "atleta" && !atletaElegido) return setError("Elige un atleta.");
    if (!startDate) return setError("Elige la fecha de inicio.");
    const opciones = {
      onSuccess: setResultado,
      onError: (err: unknown) => setError(err instanceof Error ? err.message : "No se pudo asignar el plan."),
    };
    if (destinoFinal === "atleta") {
      assignAthlete.mutate({ athleteId: atletaElegido, plan_id: planElegido, start_date: startDate }, opciones);
    } else {
      assignGroup.mutate({ groupId: grupoElegido, plan_id: planElegido, start_date: startDate }, opciones);
    }
  }

  const sinMarca = resultado?.results.filter((r) => r.status === "assigned" && r.missing_prs.length > 0) ?? [];

  return (
    <Sheet open={open} onClose={cerrar} title={resultado ? "Plan asignado" : "Asignar plan"}>
      {resultado ? (
        <div className="space-y-3 pb-4">
          <p className="text-sm">{resultado.message}</p>
          {sinMarca.length > 0 && (
            <div className="rounded-xl border border-line bg-surface-2 p-3 text-sm">
              <p className="mb-1 font-semibold">Les falta una marca para calcular los kg:</p>
              <ul className="space-y-0.5 text-muted">
                {sinMarca.map((r) => (
                  <li key={r.user_id}>
                    {r.full_name}: {r.missing_prs.join(", ")}
                  </li>
                ))}
              </ul>
              <p className="mt-2 text-xs text-muted">
                Su carga queda en % hasta que registren su 1RM; los kg se actualizan solos cuando lo hagan.
              </p>
            </div>
          )}
          <Button full onClick={cerrar}>
            Listo
          </Button>
        </div>
      ) : (
        <div className="space-y-4 pb-4">
          {plan ? (
            <p className="text-sm">
              Plan: <span className="font-semibold">{plan.name}</span>
            </p>
          ) : (
            <label className="block">
              <span className="mb-1.5 block text-sm font-medium text-muted">Plan</span>
              <select value={planId} onChange={(e) => setPlanId(e.target.value)} className={selectClass}>
                <option value="">Elige una plantilla…</option>
                {plans.data?.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.name}
                  </option>
                ))}
              </select>
              {plans.data?.length === 0 && (
                <span className="mt-1 block text-xs text-muted">Todavía no tienes planes: crea uno en «Mis planes».</span>
              )}
            </label>
          )}

          {!group && !athlete && (
            <Segmented<Destino>
              value={destino}
              onChange={setDestino}
              options={[
                { value: "grupo", label: "A un grupo" },
                { value: "atleta", label: "A un atleta" },
              ]}
            />
          )}

          {athlete ? (
            <p className="text-sm">
              Atleta: <span className="font-semibold">{athlete.name}</span>
            </p>
          ) : destinoFinal === "atleta" ? (
            <label className="block">
              <span className="mb-1.5 block text-sm font-medium text-muted">Atleta</span>
              <select value={athleteId} onChange={(e) => setAthleteId(e.target.value)} className={selectClass}>
                <option value="">Elige un atleta…</option>
                {athletes.data
                  ?.filter((u) => u.coach_id)
                  .map((u) => (
                    <option key={u.id} value={u.id}>
                      {u.full_name}
                    </option>
                  ))}
              </select>
            </label>
          ) : group ? (
            <p className="text-sm">
              Grupo: <span className="font-semibold">{group.name}</span>
            </p>
          ) : (
            <label className="block">
              <span className="mb-1.5 block text-sm font-medium text-muted">Grupo</span>
              <select value={groupId} onChange={(e) => setGroupId(e.target.value)} className={selectClass}>
                <option value="">Elige un grupo…</option>
                {groups.data?.map((g) => (
                  <option key={g.id} value={g.id}>
                    {g.name} ({g.member_count})
                  </option>
                ))}
              </select>
            </label>
          )}

          <Field
            label="¿Qué día empieza?"
            type="date"
            value={startDate}
            onChange={(e) => setStartDate(e.target.value)}
          />
          <p className="text-xs text-muted">
            La primera sesión cae en esa fecha. {destinoFinal === "atleta" ? "El atleta recibe" : "Cada atleta recibe"}{" "}
            su copia con los kg calculados con sus propias marcas. Si vuelves a asignar el mismo plan en la misma
            fecha, {destinoFinal === "atleta" ? "no se duplica" : "solo llega a quienes aún no lo tienen"}.
          </p>

          {error && <p className="text-sm font-medium text-danger">{error}</p>}
          <Button full loading={assign.isPending} onClick={asignar}>
            Asignar
          </Button>
        </div>
      )}
    </Sheet>
  );
}
