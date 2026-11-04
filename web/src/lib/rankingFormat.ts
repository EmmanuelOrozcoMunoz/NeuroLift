/** "Ana Demo Pérez" -> "Ana D.": en el podio no cabe el nombre completo. */
export function nombreCorto(nombre: string): string {
  const partes = nombre.trim().split(/\s+/);
  return partes.length > 1 ? `${partes[0]} ${partes[1][0].toUpperCase()}.` : (partes[0] ?? "");
}

/** "Por tiempo: 3:05" -> "3:05": el formato ya está arriba, en el título del WOD, y el resultado es lo que
 *  importa en un podio angosto. Una etiqueta sin ": " (como "120 cal") queda igual. */
export function soloElResultado(etiqueta: string | null): string {
  if (!etiqueta) return "—";
  const i = etiqueta.indexOf(": ");
  return i >= 0 ? etiqueta.slice(i + 2) : etiqueta;
}
