import { cx } from "@/components/ui";
import type { Weekday } from "@/lib/types";

const DAYS: { value: Weekday; label: string }[] = [
  { value: 0, label: "L" },
  { value: 1, label: "M" },
  { value: 2, label: "X" },
  { value: 3, label: "J" },
  { value: 4, label: "V" },
  { value: 5, label: "S" },
  { value: 6, label: "D" },
];

/** Nombre completo de cada día (0=Lunes..6=Domingo) — para mostrarlo junto a un campo de texto,
 *  donde la letra sola de DAYS no basta. */
export const WEEKDAY_NAMES: Record<Weekday, string> = {
  0: "Lunes",
  1: "Martes",
  2: "Miércoles",
  3: "Jueves",
  4: "Viernes",
  5: "Sábado",
  6: "Domingo",
};

export function WeekdayPicker({
  value,
  onChange,
}: {
  value: Weekday[];
  onChange: (days: Weekday[]) => void;
}) {
  function toggle(day: Weekday) {
    onChange(value.includes(day) ? value.filter((d) => d !== day) : [...value, day].sort());
  }

  return (
    <div className="flex gap-1.5">
      {DAYS.map((day) => {
        const active = value.includes(day.value);
        return (
          <button
            key={day.value}
            type="button"
            onClick={() => toggle(day.value)}
            className={cx(
              "flex h-10 w-10 items-center justify-center rounded-full text-sm font-bold transition-colors",
              active ? "bg-brand text-white" : "bg-surface-2 text-muted",
            )}
          >
            {day.label}
          </button>
        );
      })}
    </div>
  );
}
