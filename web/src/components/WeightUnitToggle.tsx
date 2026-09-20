import { Segmented } from "@/components/ui";
import { useAuth, useCurrentUser } from "@/lib/auth";
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
        onChange={(next) => update.mutate({ weight_unit: next }, { onSuccess: () => void refreshUser() })}
        options={[
          { value: "kg", label: "kg" },
          { value: "lb", label: "lb" },
        ]}
      />
    </div>
  );
}

type PlateAvailability = "si" | "no";

/** Si el box de este atleta tiene discos de 25kg — algunos solo llegan hasta 20kg. Afecta
 *  solo la calculadora de discos de las series (SetRow.tsx / BarbellPlates.tsx). */
export function PlateAvailabilityToggle() {
  const user = useCurrentUser();
  const { refreshUser } = useAuth();
  const update = useUpdateMyPreferences();
  const value: PlateAvailability = (user.has_25kg_plates ?? true) ? "si" : "no";

  return (
    <div>
      <span className="mb-1.5 block text-sm font-medium text-muted">¿Tu box tiene discos de 25kg?</span>
      <Segmented<PlateAvailability>
        value={value}
        onChange={(next) =>
          update.mutate({ has_25kg_plates: next === "si" }, { onSuccess: () => void refreshUser() })
        }
        options={[
          { value: "si", label: "Sí" },
          { value: "no", label: "No, solo hasta 20kg" },
        ]}
      />
    </div>
  );
}
