// Tipos genéricos que usan varias pantallas.

export interface MessageResponse {
  message: string;
}

export type Weekday = 0 | 1 | 2 | 3 | 4 | 5 | 6; // 0 = lunes ... 6 = domingo

export interface BulkResultRow {
  full_name: string;
  status: string;
  /** Solo en la generación grupal con IA: lo que la IA hizo mal y el servidor corrigió (ver lib/ia.ts). */
  advertencias?: string[];
}

export interface BulkResponse {
  message: string;
  results: BulkResultRow[];
}
