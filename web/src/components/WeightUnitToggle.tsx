import { Segmented } from "@/components/ui";
import { useAuth } from "@/lib/auth";
import { useUpdateMyPreferences } from "@/lib/queries";
import { useWeightUnit } from "@/lib/units";
import type { WeightUnit } from "@/lib/types";

/** Preferencia de kg/lb — la usa tanto el atleta como el coach, cada quien la suya (aplica a
 *  TODO lo que esa persona ve/edita en la app, sea su propio dato o el de un atleta). */
export function WeightUnitToggle() {
  const unit = useWeightUnit();
  const { refreshUser } = useAuth();
  const update = useUpdateMyPreferences();

  return (
    <div>
      <span className="mb-1.5 block text-sm font-medium text-muted">Unidad de peso</span>
      <Segmented<WeightUnit>
        value={unit}
        onChange={(next) => update.mutate(next, { onSuccess: () => void refreshUser() })}
        options={[
          { value: "kg", label: "kg" },
          { value: "lb", label: "lb" },
        ]}
      />
    </div>
  );
}
