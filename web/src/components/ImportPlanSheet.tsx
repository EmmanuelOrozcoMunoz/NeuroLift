import { useRef, useState } from "react";

import { Button, Field, Sheet } from "@/components/ui";
import { WEEKDAY_NAMES } from "@/components/WeekdayPicker";
import { useConfirmPlanImport, usePreviewPlanImport } from "@/lib/coachQueries";
import type { PlanImportDay, PlanImportPreviewResponse, PlanLevel, Weekday } from "@/lib/types";

const DISCIPLINAS = ["Powerbuilding", "Powerlifting", "Hipertrofia", "Weightlifting", "CrossFit"];
const NIVELES: PlanLevel[] = ["Principiante", "Intermedio", "Avanzado"];
const MAX_MB = 5;

const selectClass = "min-h-12 w-full rounded-xl border border-line bg-surface-2 px-3.5 text-fg";

const FORMATO_WOD: Record<string, string> = {
  for_time: "For time",
  amrap: "AMRAP",
  emom: "EMOM",
  rounds_for_time: "Rondas por tiempo",
  intervals: "Intervalos",
  chipper: "Chipper",
  max_reps: "Máx. repeticiones",
  max_load: "Máx. carga",
  distance: "Distancia",
};

function DiaVistaPrevia({ dia }: { dia: PlanImportDay }) {
  const nombreDia = WEEKDAY_NAMES[dia.weekday as Weekday] ?? "";
  return (
    <div className="rounded-xl border border-line bg-surface-2 p-3">
      <p className="text-sm font-semibold">
        {nombreDia}
        {dia.label && dia.label.toLowerCase() !== nombreDia.toLowerCase() ? ` · ${dia.label}` : ""}
      </p>
      {dia.warmup && <p className="mt-1 text-xs whitespace-pre-line text-muted">Calentamiento: {dia.warmup}</p>}
      <ul className="mt-1.5 space-y-0.5 text-sm">
        {dia.exercises.map((ej, i) => (
          <li key={i} className="flex justify-between gap-3">
            <span className="min-w-0 truncate">{ej.name}</span>
            <span className="shrink-0 text-muted tabular-nums">{ej.summary}</span>
          </li>
        ))}
      </ul>
      {dia.wod && (
        <p className="mt-1.5 text-xs text-muted">
          WOD ({FORMATO_WOD[dia.wod.format] ?? dia.wod.format}
          {dia.wod.time_cap_seconds ? ` · ${Math.round(dia.wod.time_cap_seconds / 60)} min` : ""}): {dia.wod.description}
        </p>
      )}
    </div>
  );
}

/** Importa un plan desde un PDF, Word o Excel en dos pasos: primero se lee el archivo y se muestra
 *  cómo quedaría (sin guardar nada); al confirmar se crea la plantilla en borrador, que se termina de
 *  ajustar en el editor de planes. */
export function ImportPlanSheet({
  open,
  onClose,
  onCreated,
}: {
  open: boolean;
  onClose: () => void;
  onCreated: (message: string) => void;
}) {
  const preview = usePreviewPlanImport();
  const confirm = useConfirmPlanImport();
  const inputRef = useRef<HTMLInputElement>(null);
  const [archivo, setArchivo] = useState<File | null>(null);
  const [resultado, setResultado] = useState<PlanImportPreviewResponse | null>(null);
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [discipline, setDiscipline] = useState(DISCIPLINAS[0]);
  const [level, setLevel] = useState<PlanLevel>("Intermedio");
  const [error, setError] = useState<string | null>(null);

  function cerrar() {
    setArchivo(null);
    setResultado(null);
    setError(null);
    preview.reset();
    confirm.reset();
    onClose();
  }

  function elegir(file: File | null) {
    setError(null);
    if (file && file.size > MAX_MB * 1024 * 1024) {
      setArchivo(null);
      return setError(`El archivo pesa más de ${MAX_MB} MB.`);
    }
    setArchivo(file);
  }

  function leer() {
    if (!archivo) return setError("Elige un archivo.");
    setError(null);
    preview.mutate(archivo, {
      onSuccess: (r) => {
        setResultado(r);
        setName(r.preview.name ?? archivo.name.replace(/\.[^.]+$/, ""));
        setDescription(r.preview.description ?? "");
        setDiscipline(r.preview.discipline ?? DISCIPLINAS[0]);
        setLevel(r.preview.level ?? "Intermedio");
      },
      onError: (err) => setError(err instanceof Error ? err.message : "No se pudo leer el archivo."),
    });
  }

  function crear() {
    if (!resultado) return;
    if (!name.trim()) return setError("Dale un nombre al plan.");
    setError(null);
    confirm.mutate(
      { name: name.trim(), description: description.trim(), discipline, level, document: resultado.document },
      {
        onSuccess: () => {
          onCreated("¡Plan importado en borrador! Revísalo y ajústalo antes de asignarlo o publicarlo.");
          cerrar();
        },
        onError: (err) => setError(err instanceof Error ? err.message : "No se pudo crear el plan."),
      },
    );
  }

  const vista = resultado?.preview;
  const disciplinas = discipline && !DISCIPLINAS.includes(discipline) ? [discipline, ...DISCIPLINAS] : DISCIPLINAS;
  const semanas = vista ? [...new Set(vista.days.map((d) => d.week))] : [];

  return (
    <Sheet open={open} onClose={cerrar} title="Importar plan">
      {!vista ? (
        <div className="space-y-4 pb-4">
          <p className="text-sm text-muted">
            Sube un plan que ya tengas en <strong>PDF, Word (.docx) o Excel (.xlsx)</strong>. La IA lo lee y verás cómo
            quedaría antes de crear nada. No se leen PDFs escaneados ni fotos.
          </p>

          <input
            ref={inputRef}
            type="file"
            accept=".pdf,.docx,.xlsx,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            className="hidden"
            onChange={(e) => elegir(e.target.files?.[0] ?? null)}
          />
          <button
            type="button"
            onClick={() => inputRef.current?.click()}
            className="w-full rounded-xl border border-dashed border-line bg-surface-2 px-4 py-6 text-center active:bg-line"
          >
            {archivo ? (
              <>
                <span className="block font-semibold break-all">{archivo.name}</span>
                <span className="text-xs text-muted">{(archivo.size / 1024).toFixed(0)} KB · toca para cambiarlo</span>
              </>
            ) : (
              <span className="font-semibold">Elegir archivo</span>
            )}
          </button>

          {error && <p className="text-sm font-medium text-danger">{error}</p>}
          <Button full loading={preview.isPending} disabled={!archivo} onClick={leer}>
            Leer documento
          </Button>
          {preview.isPending && (
            <p className="text-center text-xs text-muted">Puede tardar hasta un minuto: la IA está leyendo el plan.</p>
          )}
        </div>
      ) : (
        <div className="space-y-4 pb-4">
          <p className="text-sm">
            Encontré <strong>{vista.sessions_count} sesiones</strong> en <strong>{vista.weeks_count} semana(s)</strong>.
            Revisa que sea lo que esperabas; después de crearlo podrás editar todo.
          </p>

          {vista.warnings.length > 0 && (
            <div className="rounded-xl border border-line bg-surface-2 p-3 text-sm">
              <p className="mb-1 font-semibold">Ten en cuenta:</p>
              <ul className="list-disc space-y-0.5 pl-5 text-muted">
                {vista.warnings.slice(0, 8).map((aviso, i) => (
                  <li key={i}>{aviso}</li>
                ))}
                {vista.warnings.length > 8 && <li>y {vista.warnings.length - 8} aviso(s) más</li>}
              </ul>
            </div>
          )}

          <div className="max-h-72 space-y-3 overflow-y-auto pr-1">
            {semanas.map((semana) => (
              <section key={semana}>
                <p className="mb-1.5 text-xs font-semibold tracking-wide text-muted uppercase">Semana {semana}</p>
                <div className="space-y-2">
                  {vista.days
                    .filter((d) => d.week === semana)
                    .map((dia, i) => (
                      <DiaVistaPrevia key={`${semana}-${i}`} dia={dia} />
                    ))}
                </div>
              </section>
            ))}
          </div>

          <Field label="Nombre del plan" value={name} onChange={(e) => setName(e.target.value)} />
          <label className="block">
            <span className="mb-1.5 block text-sm font-medium text-muted">Disciplina</span>
            <select value={discipline} onChange={(e) => setDiscipline(e.target.value)} className={selectClass}>
              {disciplinas.map((d) => (
                <option key={d} value={d}>
                  {d}
                </option>
              ))}
            </select>
          </label>
          <label className="block">
            <span className="mb-1.5 block text-sm font-medium text-muted">Nivel</span>
            <select value={level} onChange={(e) => setLevel(e.target.value as PlanLevel)} className={selectClass}>
              {NIVELES.map((n) => (
                <option key={n} value={n}>
                  {n}
                </option>
              ))}
            </select>
          </label>

          {error && <p className="text-sm font-medium text-danger">{error}</p>}
          <div className="flex gap-2">
            <Button variant="secondary" className="flex-1" onClick={() => setResultado(null)}>
              Cambiar archivo
            </Button>
            <Button className="flex-1" loading={confirm.isPending} onClick={crear}>
              Crear plan
            </Button>
          </div>
        </div>
      )}
    </Sheet>
  );
}
