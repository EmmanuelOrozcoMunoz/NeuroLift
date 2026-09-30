// Espejo de backend/schemas/. Se mantiene a mano a propósito: el backend expone /openapi.json solo
// fuera de producción, así que generar tipos automáticamente ataría el build del frontend a tener
// el backend corriendo. Se importa siempre desde "@/lib/types" (index.ts reexporta todo).

export * from "./auth";
export * from "./common";
export * from "./boxes";
export * from "./admin";
export * from "./sessions";
export * from "./mesocycles";
export * from "./plans";
export * from "./ranking";
export * from "./fitness";
export * from "./groups";
export * from "./classes";
export * from "./dashboard";
