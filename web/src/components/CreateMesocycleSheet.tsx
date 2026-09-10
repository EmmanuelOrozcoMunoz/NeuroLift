import { useState } from "react";

import { Button, Field, Segmented, Sheet, Stepper } from "@/components/ui";
import { WeekdayPicker } from "@/components/WeekdayPicker";
import {
  useCreateManualMesocycle,
  useCreateManualMesocycleForGroup,
  useGenerateAIMesocycle,
  useGenerateAIMesocycleForGroup,
} from "@/lib/coachQueries";
import { todayIso } from "@/lib/dates";
import type { Weekday } from "@/lib/types";

const DISCIPLINAS = ["Powerbuilding", "Powerlifting", "Hipertrofia", "Weightlifting", "CrossFit"];

/**
 * Crea un mesociclo (manual o con IA) para UN atleta o para UN grupo completo. Se usa igual
 * desde AthleteDetail (target={type:"athlete", id}) y desde GroupDetail (target={type:"group", id}).
 */
export function CreateMesocycleSheet({
  open,
  onClose,
  target,
  onCreated,
}: {
  open: boolean;
  onClose: () => void;
  target: { type: "athlete"; id: string } | { type: "group"; id: string };
  onCreated: (message: string) => void;
}) {
  const [modo, setModo] = useState<"ia" | "manual">("ia");
  const [name, setName] = useState("Bloque de Fuerza 1");
  const [discipline, setDiscipline] = useState(DISCIPLINAS[0]);
  const [startDate, setStartDate] = useState(todayIso());
  const [weeks, setWeeks] = useState(4);
  const [days, setDays] = useState<Weekday[]>([0, 2, 4]);
  const [context, setContext] = useState("");
  const [sessionMinutes, setSessionMinutes] = useState(0);
  const [error, setError] = useState<string | null>(null);

  const createManual = useCreateManualMesocycle();
  const createManualGroup = useCreateManualMesocycleForGroup(target.type === "group" ? target.id : "none");
  const generateAI = useGenerateAIMesocycle();
  const generateAIGroup = useGenerateAIMesocycleForGroup(target.type === "group" ? target.id : "none");

  const busy =
    createManual.isPending || createManualGroup.isPending || generateAI.isPending || generateAIGroup.isPending;

  function reset() {
    setName("Bloque de Fuerza 1");
    setContext("");
    setSessionMinutes(0);
    setError(null);
  }

  function handleSubmit() {
    setError(null);
    if (!name.trim()) return setError("Dale un nombre al mesociclo.");
    if (days.length === 0) return setError("Selecciona al menos un día de entrenamiento.");

    const base = { name: name.trim(), discipline, start_date: startDate, weeks_count: weeks, training_days: days };
    const onOk = (message: string) => {
      onCreated(message);
      reset();
      onClose();
    };
    const onErr = (err: unknown) =>
      setError(err instanceof Error ? err.message : "No se pudo crear el mesociclo.");

    if (modo === "manual") {
      if (target.type === "athlete") {
        createManual.mutate(
          { ...base, user_id: target.id },
          { onSuccess: () => onOk("¡Mesociclo creado! Añádele ejercicios desde la rutina."), onError: onErr },
        );
      } else {
        createManualGroup.mutate(
          { ...base, group_id: target.id },
          { onSuccess: (r) => onOk(r.message), onError: onErr },
        );
      }
    } else {
      const aiBase = {
        ...base,
        context: context.trim() || "Progreso lineal y mejora técnica general.",
        session_duration_minutes: sessionMinutes > 0 ? sessionMinutes : null,
      };
      if (target.type === "athlete") {
        generateAI.mutate(
          { ...aiBase, user_id: target.id },
          { onSuccess: () => onOk("¡Mesociclo generado con IA!"), onError: onErr },
        );
      } else {
        generateAIGroup.mutate(
          { ...aiBase, group_id: target.id },
          { onSuccess: (r) => onOk(r.message), onError: onErr },
        );
      }
    }
  }

  return (
    <Sheet open={open} onClose={onClose} title="Crear mesociclo">
      <div className="space-y-4">
        <Segmented<"ia" | "manual">
          value={modo}
          onChange={setModo}
          options={[
            { value: "ia", label: "✨ Con IA" },
            { value: "manual", label: "✍️ Manual" },
          ]}
        />

        <Field label="Nombre" value={name} onChange={(e) => setName(e.target.value)} />

        <label className="block">
          <span className="mb-1.5 block text-sm font-medium text-muted">Disciplina</span>
          <select
            value={discipline}
            onChange={(e) => setDiscipline(e.target.value)}
            className="min-h-12 w-full rounded-xl border border-line bg-surface-2 px-3.5 text-fg"
          >
            {DISCIPLINAS.map((d) => (
              <option key={d} value={d}>
                {d}
              </option>
            ))}
          </select>
        </label>

        <Field
          label="Fecha de inicio"
          type="date"
          value={startDate}
          onChange={(e) => setStartDate(e.target.value)}
        />

        <div>
          <span className="mb-1.5 block text-sm font-medium text-muted">Semanas de duración</span>
          <Stepper value={weeks} onChange={setWeeks} min={1} max={modo === "ia" ? 16 : 52} />
        </div>

        <div>
          <span className="mb-1.5 block text-sm font-medium text-muted">Días de entrenamiento</span>
          <WeekdayPicker value={days} onChange={setDays} />
        </div>

        {modo === "ia" && (
          <>
            <label className="block">
              <span className="mb-1.5 block text-sm font-medium text-muted">
                Objetivo y contexto (opcional)
              </span>
              <textarea
                value={context}
                onChange={(e) => setContext(e.target.value)}
                rows={3}
                maxLength={2000}
                placeholder="Ej. Priorizar sentadilla, dolor leve en hombro derecho..."
                className="w-full rounded-xl border border-line bg-surface-2 px-3.5 py-2.5 text-fg placeholder:text-muted/50 focus:border-brand focus:outline-none"
              />
            </label>

            <div>
              <span className="mb-1.5 block text-sm font-medium text-muted">
                Duración objetivo por sesión (min) — 0 = sin restricción
              </span>
              <Stepper value={sessionMinutes} onChange={setSessionMinutes} step={5} min={0} max={180} />
            </div>
          </>
        )}

        {error && <p className="text-sm font-medium text-danger">{error}</p>}

        <Button full loading={busy} onClick={handleSubmit}>
          {modo === "ia" ? "✨ Generar con IA" : "Construir esqueleto"}
        </Button>
        {modo === "ia" && (
          <p className="text-center text-xs text-muted">
            Puede tardar hasta un minuto: la IA calcula pesos y volumen por sesión.
          </p>
        )}
      </div>
    </Sheet>
  );
}
