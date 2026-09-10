import { BLOCK_OPTIONS } from "@/lib/blocks";

/** Selector del bloque de un ejercicio (calentamiento, fuerza, weightlifting, skills, metcon...).
 *  Un <select> nativo: son pocas opciones y ya es el patrón usado en el resto de la app
 *  (disciplina/nivel en Plans.tsx) para listas cortas de valores fijos. */
export function BlockSelect({
  value,
  onChange,
  label = "Bloque",
  className = "mb-3",
}: {
  value: string;
  onChange: (value: string) => void;
  label?: string;
  className?: string;
}) {
  return (
    <label className={`block ${className}`}>
      <span className="mb-1.5 block text-xs font-medium text-muted">{label}</span>
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="min-h-12 w-full rounded-xl border border-line bg-surface-2 px-3.5 text-fg"
      >
        {BLOCK_OPTIONS.map((option) => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </select>
    </label>
  );
}
