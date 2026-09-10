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

/** Etiqueta legible de un bloque. Si es un valor desconocido (dato viejo o externo) lo muestra
 *  tal cual en vez de ocultarlo. */
export function blockLabel(key: string | null | undefined): string {
  if (!key) return "Sin bloque";
  return (BLOCK_LABELS as Record<string, string>)[key] ?? key;
}

/** Opciones para un <select>: "Sin bloque" primero, luego los bloques en el orden canónico. */
export const BLOCK_OPTIONS: { value: string; label: string }[] = [
  { value: "", label: "Sin bloque" },
  ...BLOCK_KEYS.map((key) => ({ value: key, label: BLOCK_LABELS[key] })),
];
