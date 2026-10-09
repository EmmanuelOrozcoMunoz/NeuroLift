import { IconTrash } from "@/components/icons";
import { groupSummary } from "@/lib/sessions";
import type { ExerciseGroup } from "@/lib/sessions";
import { useWeightUnit } from "@/lib/units";

/**
 * Un ejercicio del día en una línea compacta (nombre, series x repeticiones @ carga y la nota del
 * coach), para ver todo el día de un vistazo agrupado por bloques. Es la vista del editor de
 * planes, que ahora comparte el de sesiones: ahí el lápiz abre el formulario de ese ejercicio.
 */
export function ExerciseSummaryRow({
  group,
  onRemove,
  removing,
  onEdit,
}: {
  group: ExerciseGroup;
  onRemove: () => void;
  removing?: boolean;
  /** Si se pasa, aparece el lápiz para editar el ejercicio (los planes todavía no lo permiten). */
  onEdit?: () => void;
}) {
  const unit = useWeightUnit();
  const nota = group.sets.find((s) => s.coach_note)?.coach_note;

  return (
    <div className="flex items-center justify-between gap-2 rounded-xl bg-surface-2 px-3 py-2.5">
      <div className="min-w-0">
        <p className="truncate text-sm font-semibold">🏋️ {group.name}</p>
        <p className="truncate text-xs text-muted">{groupSummary(group, unit)}</p>
        {nota && <p className="mt-0.5 line-clamp-2 text-xs text-brand">📝 {nota}</p>}
      </div>
      <div className="flex shrink-0 items-center gap-0.5">
        {onEdit && (
          <button
            type="button"
            aria-label={`Editar ${group.name}`}
            onClick={onEdit}
            className="rounded-lg p-1.5 text-sm active:bg-line"
          >
            ✏️
          </button>
        )}
        <button
          type="button"
          aria-label="Quitar ejercicio"
          disabled={removing}
          onClick={onRemove}
          className="rounded-lg p-1.5 text-danger active:bg-danger/10 disabled:opacity-40"
        >
          <IconTrash className="h-4 w-4" />
        </button>
      </div>
    </div>
  );
}
