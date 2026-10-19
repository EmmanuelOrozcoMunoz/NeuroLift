/**
 * Cuando la IA genera un mesociclo, el backend corrige o descarta lo que hizo mal (un kg inventado
 * sin marca de 1RM, un ejercicio ilegible...) y lo devuelve como avisos para el coach: él es quien
 * decide si lo arregla a mano. Esto arma el mensaje de confirmación con los primeros avisos, para
 * que no pasen desapercibidos.
 */
export function mensajeConAvisos(mensaje: string, avisos: string[] | undefined): string {
  const lista = avisos ?? [];
  if (lista.length === 0) return mensaje;
  const primeros = lista.slice(0, 2).join(" · ");
  const resto = lista.length > 2 ? ` · y ${lista.length - 2} aviso(s) más` : "";
  return `${mensaje} Revisa: ${primeros}${resto}`;
}
