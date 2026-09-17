import { Stepper } from "@/components/ui";
import { useCurrentUser } from "@/lib/auth";
import type { WeightUnit } from "@/lib/types";

const KG_PER_LB = 0.45359237;

/** kg -> unidad de destino, para MOSTRAR un peso que ya viene guardado en kg. */
export function kgTo(kg: number, unit: WeightUnit): number {
  return unit === "lb" ? kg / KG_PER_LB : kg;
}

/** unidad de origen -> kg, para GUARDAR lo que el usuario acaba de escribir. El backend
 *  (% de 1RM, redondeo a 2.5kg, etc.) siempre trabaja en kg — la conversión pasa por aquí
 *  para que ningún flujo de guardado tenga que saber en qué unidad estaba escribiendo el usuario. */
export function toKg(value: number, unit: WeightUnit): number {
  return unit === "lb" ? value * KG_PER_LB : value;
}

/** "step" razonable del Stepper en la unidad de destino, a partir del step "natural" en kg
 *  (casi siempre 2.5kg) — 2.5kg redondeado a lb da un paso feo (5.51...), así que en lb se
 *  usa un paso propio, más cómodo de tocar (5lb ≈ 2.27kg, similar granularidad que 2.5kg). */
export function stepFor(unit: WeightUnit, kgStep = 2.5): number {
  return unit === "lb" ? 5 : kgStep;
}

/** Texto de un peso en kg, formateado en la unidad preferida del usuario (ej. "225 lb"). */
export function formatWeight(kg: number | null | undefined, unit: WeightUnit): string {
  if (kg === null || kg === undefined) return "";
  const value = kgTo(kg, unit);
  const rounded = Number.isInteger(value) ? value : Math.round(value * 10) / 10;
  return `${Number.isInteger(rounded) ? rounded : rounded.toFixed(1)} ${unit}`;
}

/** Unidad preferida del usuario actualmente autenticado (coach o atleta) — se aplica a TODO lo
 *  que esa persona ve/edita en la app, sea su propio dato o el de un atleta que está mirando.
 *  null en el perfil == "kg" (default silencioso, sin migrar datos existentes). */
export function useWeightUnit(): WeightUnit {
  return useCurrentUser().weight_unit ?? "kg";
}

/** Stepper de peso: el que lo usa siempre lee/escribe en KG (igual que antes, cero cambios en
 *  el resto del código que ya guarda/envía en kg al backend) — la conversión a la unidad
 *  preferida del usuario (y el "step" correcto en esa unidad) pasa aquí, una sola vez. */
export function WeightStepper({
  valueKg,
  onChangeKg,
  min = 0,
  max = 1000,
  compact,
}: {
  valueKg: number;
  onChangeKg: (kg: number) => void;
  min?: number;
  max?: number;
  compact?: boolean;
}) {
  const unit = useWeightUnit();
  return (
    <Stepper
      value={kgTo(valueKg, unit)}
      onChange={(displayValue) => onChangeKg(toKg(displayValue, unit))}
      step={stepFor(unit)}
      min={kgTo(min, unit)}
      max={kgTo(max, unit)}
      suffix={unit}
      compact={compact}
    />
  );
}
