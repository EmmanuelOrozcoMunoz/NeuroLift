import type { ReactNode } from "react";

import { cx } from "@/components/ui";

/**
 * Anillo de progreso (SVG). Es uno de los pocos lugares donde se usa el color de acento: el
 * progreso. El contenido del centro (normalmente una cifra) va como children.
 */
export function ProgressRing({
  value,
  max,
  size = 96,
  stroke = 8,
  label,
  className,
  children,
}: {
  value: number;
  max: number;
  size?: number;
  stroke?: number;
  /** Texto para lectores de pantalla, ej. "3 de 4 sesiones completadas esta semana". */
  label: string;
  className?: string;
  children?: ReactNode;
}) {
  const radius = (size - stroke) / 2;
  const circumference = 2 * Math.PI * radius;
  const progress = max > 0 ? Math.min(1, Math.max(0, value / max)) : 0;

  return (
    <div className={cx("relative shrink-0", className)} style={{ width: size, height: size }} role="img" aria-label={label}>
      {/* -rotate-90: el progreso arranca arriba, como un reloj */}
      <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`} className="-rotate-90" aria-hidden>
        <circle cx={size / 2} cy={size / 2} r={radius} fill="none" strokeWidth={stroke} className="stroke-surface-2" />
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          strokeWidth={stroke}
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={circumference * (1 - progress)}
          className="stroke-brand transition-[stroke-dashoffset] duration-700 ease-out-expo"
        />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center" aria-hidden>
        {children}
      </div>
    </div>
  );
}
