import { useCurrentUser } from "@/lib/auth";
import { barWeightKg, calculatePlates, PLATE_COLORS } from "@/lib/plates";

/** Alto/ancho relativo de cada disco en el dibujo — los más pesados se ven más grandes,
 *  como en la vida real, para que el golpe de vista alcance sin tener que leer el número. */
function plateSize(kg: number): { width: number; height: number } {
  const height = 34 + kg * 1.5;
  const width = kg >= 15 ? 16 : kg >= 5 ? 12 : 9;
  return { width, height };
}

function PlateStack({ plates }: { plates: number[] }) {
  return (
    <div className="flex items-center gap-0.5">
      {plates.map((kg, i) => {
        const { width, height } = plateSize(kg);
        return (
          <div
            key={i}
            title={`${kg}kg`}
            // Borde claro fijo (no solo un borde oscuro) — el disco negro de 2.5kg, siendo
            // real, se perdería por completo contra el fondo oscuro de la app sin esto.
            className="shrink-0 rounded-[3px] border border-white/35"
            style={{ backgroundColor: PLATE_COLORS[kg], width, height }}
          />
        );
      })}
    </div>
  );
}

/** Diagrama de qué discos poner de cada lado de la barra para un peso dado — pensado para
 *  cargarla de un vistazo, sin tener que calcular a mano cuánto va de cada lado. Los colores
 *  son los estándar de competencia (25kg rojo, 20kg azul, 15kg amarillo, 10kg verde, 5kg
 *  blanco, 2.5kg negro, 1.25kg cromado), independientes de si el atleta ve el peso en lb. */
export function BarbellPlates({ weightKg }: { weightKg: number }) {
  const user = useCurrentUser();
  const bar = barWeightKg(user.sex);
  const has25kg = user.has_25kg_plates ?? true;
  const { perSide, remainderKg } = calculatePlates(weightKg, bar, has25kg);

  if (perSide.length === 0) {
    return (
      <p className="mt-2 text-center text-xs text-muted">
        Con solo la barra ({bar}kg) ya alcanza o se pasa este peso — no hace falta ningún disco.
      </p>
    );
  }

  return (
    <div className="mt-2 rounded-xl bg-surface-2/60 p-3">
      <div className="flex items-center justify-center gap-1.5">
        <PlateStack plates={[...perSide].reverse()} />
        <div className="h-1.5 w-8 shrink-0 rounded-full bg-muted/50" />
        <PlateStack plates={perSide} />
      </div>
      <p className="mt-2 text-center text-xs text-muted">
        Barra {bar}kg + {perSide.join(" + ")}kg por lado
        {remainderKg > 0 && ` · sobran ${remainderKg}kg (no se puede armar exacto)`}
      </p>
    </div>
  );
}
