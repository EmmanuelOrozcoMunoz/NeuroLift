interface IconProps {
  className?: string;
}

const base = "h-6 w-6";

export function IconToday({ className = base }: IconProps) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
      <rect x="3" y="5" width="18" height="16" rx="3" strokeLinejoin="round" />
      <path d="M8 3v4M16 3v4M3 10h18" strokeLinecap="round" />
      <circle cx="12" cy="15.5" r="2" fill="currentColor" stroke="none" />
    </svg>
  );
}

export function IconDumbbell({ className = base }: IconProps) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
      <path d="M4 9v6M7 7v10M17 7v10M20 9v6M7 12h10" strokeLinecap="round" />
    </svg>
  );
}

export function IconStore({ className = base }: IconProps) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
      <path d="M4 8h16l-1 12H5L4 8Z" strokeLinejoin="round" />
      <path d="M9 8V6a3 3 0 0 1 6 0v2" strokeLinecap="round" />
    </svg>
  );
}

export function IconUser({ className = base }: IconProps) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
      <circle cx="12" cy="8.5" r="3.5" />
      <path d="M4.5 20c.8-3.7 3.8-5.5 7.5-5.5s6.7 1.8 7.5 5.5" strokeLinecap="round" />
    </svg>
  );
}

export function IconCheck({ className = base }: IconProps) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.6">
      <path d="M5 12.5 10 17.5 19 7" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

export function IconChevronRight({ className = base }: IconProps) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M9 5l7 7-7 7" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

export function IconBack({ className = base }: IconProps) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M15 5l-7 7 7 7" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

export function IconClock({ className = base }: IconProps) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
      <circle cx="12" cy="12" r="8.5" />
      <path d="M12 7.5V12l3 2" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

export function IconLogout({ className = base }: IconProps) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
      <path d="M14 4h3.5A2.5 2.5 0 0 1 20 6.5v11A2.5 2.5 0 0 1 17.5 20H14" strokeLinecap="round" />
      <path d="M10 8l-4 4 4 4M6 12h9" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

export function IconSpark({ className = base }: IconProps) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
      <path
        d="M12 3l1.8 4.7L18.5 9.5l-4.7 1.8L12 16l-1.8-4.7L5.5 9.5l4.7-1.8L12 3Z"
        strokeLinejoin="round"
      />
      <path d="M18 16l.9 2.1L21 19l-2.1.9L18 22l-.9-2.1L15 19l2.1-.9L18 16Z" strokeLinejoin="round" />
    </svg>
  );
}

export function IconUsers({ className = base }: IconProps) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
      <circle cx="9" cy="8.5" r="3" />
      <path d="M3 20c.7-3.4 3.3-5 6-5s5.3 1.6 6 5" strokeLinecap="round" />
      <circle cx="17" cy="9" r="2.3" />
      <path d="M15.5 12.2c1.9.3 3.6 1.6 4.1 3.8" strokeLinecap="round" />
    </svg>
  );
}

export function IconCamera({ className = base }: IconProps) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
      <path d="M4 8.5A1.5 1.5 0 0 1 5.5 7H8l1-2h6l1 2h2.5A1.5 1.5 0 0 1 20 8.5V17a1.5 1.5 0 0 1-1.5 1.5h-13A1.5 1.5 0 0 1 4 17V8.5Z" strokeLinejoin="round" />
      <circle cx="12" cy="12.5" r="3.3" />
    </svg>
  );
}

export function IconTrash({ className = base }: IconProps) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
      <path d="M5 7h14M9 7V5a1 1 0 0 1 1-1h4a1 1 0 0 1 1 1v2m-9 0 1 13a1 1 0 0 0 1 1h8a1 1 0 0 0 1-1l1-13" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

export function IconTrophy({ className = base }: IconProps) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
      <path d="M7 4h10v5a5 5 0 0 1-10 0V4Z" strokeLinejoin="round" />
      <path d="M7 5H4.5A1.5 1.5 0 0 0 3 6.5C3 8.5 4.5 10 7 10M17 5h2.5A1.5 1.5 0 0 1 21 6.5C21 8.5 19.5 10 17 10" strokeLinecap="round" />
      <path d="M12 14v3M9 20.5h6M9.5 20.5c0-2 .8-2.7 1-3.5M14.5 20.5c0-2-.8-2.7-1-3.5" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

export function IconImage({ className = base }: IconProps) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
      <rect x="3.5" y="4.5" width="17" height="15" rx="2.5" strokeLinejoin="round" />
      <circle cx="9" cy="10" r="1.7" />
      <path d="M4.5 16.5 9 12l3 3 4-4 3.5 3.5" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

export function IconOffline({ className = base }: IconProps) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
      <path d="M3 3l18 18" strokeLinecap="round" />
      <path d="M8.5 16.5a5 5 0 0 1 7 0" strokeLinecap="round" />
      <path d="M5 13a9 9 0 0 1 3-2M16 11a9 9 0 0 1 3 2" strokeLinecap="round" />
    </svg>
  );
}

export function IconShield({ className = base }: IconProps) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
      <path d="M12 3.5 19 6.5V11c0 5-3 8-7 9.5-4-1.5-7-4.5-7-9.5V6.5L12 3.5Z" strokeLinejoin="round" />
      <path d="M9 12l2 2 4-4.5" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

export function IconList({ className = base }: IconProps) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
      <path d="M8 6.5h12M8 12h12M8 17.5h12" strokeLinecap="round" />
      <circle cx="4" cy="6.5" r="1.3" fill="currentColor" stroke="none" />
      <circle cx="4" cy="12" r="1.3" fill="currentColor" stroke="none" />
      <circle cx="4" cy="17.5" r="1.3" fill="currentColor" stroke="none" />
    </svg>
  );
}

export function IconDownload({ className = base }: IconProps) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
      <path d="M12 4v11M7.5 10.5 12 15l4.5-4.5" strokeLinecap="round" strokeLinejoin="round" />
      <path d="M5 19h14" strokeLinecap="round" />
    </svg>
  );
}

/** El ícono de "Compartir" de Safari (cuadro con flecha hacia arriba). */
export function IconShare({ className = base }: IconProps) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
      <path d="M12 3v12M8 7l4-4 4 4" strokeLinecap="round" strokeLinejoin="round" />
      <path d="M8 10H6a1 1 0 0 0-1 1v9a1 1 0 0 0 1 1h12a1 1 0 0 0 1-1v-9a1 1 0 0 0-1-1h-2" strokeLinecap="round" />
    </svg>
  );
}

/** Logo de NeuroLift (la mancuerna del ícono de la app). Toma el color de acento del box vía
 *  text-brand; el ícono PNG de la pantalla de inicio sí es fijo. */
export function Logo({ className = "h-8 w-8" }: IconProps) {
  return (
    <svg className={className} viewBox="0 0 32 32" aria-hidden>
      <rect width="32" height="32" rx="8" className="fill-surface" />
      <path
        d="M8 12v8M11 9v14M21 9v14M24 12v8M11 16h10"
        className="stroke-brand"
        strokeWidth="2.6"
        strokeLinecap="round"
        fill="none"
      />
    </svg>
  );
}
