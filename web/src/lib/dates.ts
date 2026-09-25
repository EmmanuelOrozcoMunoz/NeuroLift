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

/** "Agosto 2026" — encabezado del calendario mensual, con el mes en mayúscula inicial. */
export function monthLabel(year: number, month: number): string {
  const mes = new Date(year, month, 1).toLocaleDateString("es", { month: "long" });
  return `${mes.charAt(0).toUpperCase()}${mes.slice(1)} ${year}`;
}

export interface CalendarCell {
  iso: string;
  inMonth: boolean;
}

/**
 * Rejilla de un mes calendario (lunes a domingo), con los días de los meses vecinos que hacen
 * falta para completar la primera y la última semana — igual que cualquier calendario mensual.
 * Solo trae tantas filas como el mes necesite (5 o 6), no siempre 6.
 */
export function monthGrid(year: number, month: number): CalendarCell[] {
  const first = new Date(year, month, 1);
  const last = new Date(year, month + 1, 0);
  const firstWeekday = (first.getDay() + 6) % 7; // 0 = lunes
  const lastWeekday = (last.getDay() + 6) % 7;

  const cells: CalendarCell[] = [];
  const cursor = new Date(year, month, 1 - firstWeekday);
  const end = new Date(year, month, last.getDate() + (6 - lastWeekday));
  while (cursor <= end) {
    cells.push({ iso: toApiDate(cursor), inMonth: cursor.getMonth() === month });
    cursor.setDate(cursor.getDate() + 1);
  }
  return cells;
}

/**
 * El backend guarda los datetimes en UTC pero SIN zona (ej. "2026-10-09T14:03:00"), y
 * `new Date()` interpreta ese formato como hora LOCAL: en Colombia (UTC-5) corría todo 5 horas
 * y "14 días de prueba" se mostraba como 15. Si el texto no trae zona, se le agrega la de UTC.
 */
export function parseUtcDateTime(iso: string): Date {
  return new Date(/[zZ]|[+-]\d{2}:?\d{2}$/.test(iso) ? iso : `${iso}Z`);
}
