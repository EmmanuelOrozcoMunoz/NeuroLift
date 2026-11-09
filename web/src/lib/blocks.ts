// Espejo de backend/schemas.py:Bloque — mismos valores, mismo orden canónico de despliegue.

export const BLOCK_KEYS = [
  "warmup",
  "strength",
  "weightlifting",
  "skills",
  "metcon",
  "accessory",
  "main",
] as const;

export type BlockKey = (typeof BLOCK_KEYS)[number];

export const BLOCK_LABELS: Record<BlockKey, string> = {
  warmup: "Calentamiento",
  strength: "Fuerza",
  weightlifting: "Weightlifting",
  skills: "Skills / Gimnasia",
  metcon: "Metabólico",
  accessory: "Accesorios",
  main: "Principal",
};

/** Los bloques cuyo texto libre vive en `Session.block_notes`. El calentamiento y el WOD usan sus
 *  propios campos (warmup_notes y wod_notes, este último con su formato y temporizador). */
export const TEXT_BLOCK_KEYS = ["strength", "weightlifting", "skills", "accessory", "main"] as const;

/** Un bloque con nombre propio ("Activación", "Finisher"...): su clave es "x:" + el nombre y siempre lleva
 *  texto libre (Session.block_notes). Espejo de backend/services/block_notes.py:es_bloque_personalizado. */
export const PREFIJO_PERSONALIZADO = "x:";
export const MAX_NOMBRE_DE_BLOQUE = 30;

export function esBloquePersonalizado(key: string | null | undefined): key is string {
  return typeof key === "string" && key.startsWith(PREFIJO_PERSONALIZADO) && key.length > PREFIJO_PERSONALIZADO.length;
}

/** La clave de un bloque personalizado a partir de lo que escribió el usuario, o null si no vale (vacío o demasiado
 *  largo). Colapsa los espacios y cambia las comas y los signos < > por espacios, porque rompen el orden de los
 *  bloques y el HTML. */
export function clavePersonalizada(nombre: string): string | null {
  const limpio = nombre.replace(/[,<>]/g, " ").replace(/\s+/g, " ").trim();
  if (limpio.length === 0 || limpio.length > MAX_NOMBRE_DE_BLOQUE) return null;
  return PREFIJO_PERSONALIZADO + limpio;
}

/** Etiqueta legible de un bloque. Un bloque personalizado se llama como lo nombró el usuario. Si es un valor
 *  desconocido (dato viejo o externo) lo muestra tal cual en vez de ocultarlo. */
export function blockLabel(key: string | null | undefined): string {
  if (!key) return "Sin bloque";
  if (esBloquePersonalizado(key)) return key.slice(PREFIJO_PERSONALIZADO.length);
  return (BLOCK_LABELS as Record<string, string>)[key] ?? key;
}

/** Opciones para un <select>: "Sin bloque" primero, luego los bloques en el orden canónico. */
export const BLOCK_OPTIONS: { value: string; label: string }[] = [
  { value: "", label: "Sin bloque" },
  ...BLOCK_KEYS.map((key) => ({ value: key, label: BLOCK_LABELS[key] })),
];
