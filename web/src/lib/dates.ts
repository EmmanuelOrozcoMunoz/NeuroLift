const DIAS = ["Domingo", "Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado"];
const DIAS_CORTOS = ["Dom", "Lun", "Mar", "Mié", "Jue", "Vie", "Sáb"];
const MESES = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"];

/**
 * Convierte "2026-09-15" en una fecha LOCAL. `new Date("2026-09-15")` la interpretaría como
 * medianoche UTC, que en Colombia (UTC-5) cae el día anterior — y eso haría que "hoy" nunca
 * coincidiera con la sesión de hoy.
 */
export function parseApiDate(iso: string): Date {
  const [year, month, day] = iso.split("-").map(Number);
  return new Date(year, (month ?? 1) - 1, day ?? 1);
}

/** La fecha de hoy en formato YYYY-MM-DD según el reloj del dispositivo. */
export function todayIso(): string {
  return toApiDate(new Date());
}

export function toApiDate(date: Date): string {
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  return `${date.getFullYear()}-${month}-${day}`;
}

export function weekdayName(iso: string): string {
  return DIAS[parseApiDate(iso).getDay()] ?? "";
}

export function shortWeekdayName(iso: string): string {
  return DIAS_CORTOS[parseApiDate(iso).getDay()] ?? "";
}

/** "Mié 15 sep" — compacto para las tarjetas de sesión en pantalla de celular. */
export function shortDate(iso: string): string {
  const date = parseApiDate(iso);
  return `${DIAS_CORTOS[date.getDay()]} ${date.getDate()} ${MESES[date.getMonth()]}`;
}

/** "Miércoles 15 de septiembre" — para el encabezado de la sesión. */
export function longDate(iso: string): string {
  const date = parseApiDate(iso);
  const mesLargo = date.toLocaleDateString("es", { month: "long" });
  return `${DIAS[date.getDay()]} ${date.getDate()} de ${mesLargo}`;
}

/** Días de diferencia respecto a hoy (negativo = pasado). */
export function daysFromToday(iso: string): number {
  const target = parseApiDate(iso);
  const now = new Date();
  const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  return Math.round((target.getTime() - today.getTime()) / 86_400_000);
}

/** "hoy", "mañana", "ayer", "en 3 días", "hace 5 días" */
export function relativeDay(iso: string): string {
  const diff = daysFromToday(iso);
  if (diff === 0) return "hoy";
  if (diff === 1) return "mañana";
  if (diff === -1) return "ayer";
  if (diff > 1) return `en ${diff} días`;
  return `hace ${Math.abs(diff)} días`;
}

export function formatSeconds(total: number): string {
  const minutes = Math.floor(total / 60);
  const seconds = total % 60;
  return `${minutes}:${String(seconds).padStart(2, "0")}`;
}

export function formatPrice(price: number | null | undefined): string {
  if (!price) return "Gratis";
  return `$${price.toLocaleString("es-CO", { maximumFractionDigits: 0 })}`;
}

/** Quita el .0 de los pesos: 135.0 -> "135", 77.5 -> "77.5" */
export function formatKg(value: number): string {
  return Number.isInteger(value) ? String(value) : value.toFixed(1);
}

/**
 * "septiembre 2026" — para "Miembro desde" en el perfil. `created_at` es un datetime COMPLETO
 * (con hora), a diferencia de las fechas YYYY-MM-DD de sesiones/mesociclos — así que acá sí es
 * seguro usar `new Date()` directo, sin el ajuste de zona horaria que hace parseApiDate.
 */
export function monthYear(isoDatetime: string): string {
  const date = new Date(isoDatetime);
  const mes = date.toLocaleDateString("es", { month: "long" });
  return `${mes} ${date.getFullYear()}`;
}
