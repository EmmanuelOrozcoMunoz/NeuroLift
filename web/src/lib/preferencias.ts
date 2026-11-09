/** Recuerda una elección sencilla de pantalla (p. ej. si el formulario de ejercicio queda abierto) en el dispositivo. */
export function leerPreferencia(clave: string): string | null {
  try {
    return window.localStorage.getItem(clave);
  } catch {
    return null;
  }
}

export function guardarPreferencia(clave: string, valor: string): void {
  try {
    window.localStorage.setItem(clave, valor);
  } catch {
    // sin almacenamiento (modo privado, etc.): la pantalla funciona igual, solo no recuerda la elección
  }
}
