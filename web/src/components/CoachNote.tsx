import { IconNote } from "@/components/icons";

export const COACH_NOTE_MAX = 500;

/** Campo del editor: lo que el coach quiere remarcarle al atleta en este ejercicio. */
export function CoachNoteField({
  value,
  onChange,
  className,
}: {
  value: string;
  onChange: (value: string) => void;
  className?: string;
}) {
  return (
    <label className={className ?? "mt-3 block"}>
      <span className="mb-1.5 block text-xs font-medium text-muted">Nota para el atleta (opcional)</span>
      <textarea
        rows={2}
        maxLength={COACH_NOTE_MAX}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder="Ej. Codos arriba en la recepción. Si molesta el hombro, baja el peso."
        className="w-full rounded-xl border border-line bg-surface-2 p-3 text-sm text-fg placeholder:text-muted/50 focus:border-brand focus:outline-none"
      />
    </label>
  );
}

/** Lo que ve el atleta debajo del nombre del ejercicio. */
export function CoachNoteCallout({ note, className }: { note: string | null | undefined; className?: string }) {
  if (!note) return null;
  return (
    <div className={`flex gap-2 rounded-xl bg-brand-soft px-3 py-2 text-sm ${className ?? "mt-2"}`}>
      <IconNote className="mt-0.5 h-4 w-4 shrink-0 text-brand" aria-hidden />
      <p className="min-w-0 break-words whitespace-pre-line">
        <span className="font-semibold text-brand">Nota del coach: </span>
        {note}
      </p>
    </div>
  );
}
