import { Stepper } from "@/components/ui";

/** «¿Cuántos intervalos?» para un WOD por intervalos. El atleta anota el tiempo de cada uno y gana el menor total. */
export function IntervalosCampo({ value, onChange }: { value: number; onChange: (value: number) => void }) {
  return (
    <div className="mt-3 border-t border-line pt-3">
      <p className="mb-1.5 text-xs font-medium text-muted">
        🔁 ¿Cuántos intervalos? El atleta anota el tiempo de cada uno y gana el menor total.
      </p>
      <Stepper value={value} onChange={onChange} min={2} max={30} suffix="intervalos" compact />
    </div>
  );
}
