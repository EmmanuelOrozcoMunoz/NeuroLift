import type { User } from "@/lib/types";

/**
 * Con quién compite uno en el leaderboard: los demás atletas de un box o, si la cuenta es de un coach
 * independiente (no hay box), los demás atletas de ese coach. Así los textos no dicen "box" donde no hay.
 */
export function equipoDe(user: User, esAtleta: boolean) {
  const deCoach = user.box?.kind === "coach";
  return {
    /** "Todo el box" / "Todos los atletas de tu coach" / "Todos tus atletas" */
    todos: deCoach ? (esAtleta ? "Todos los atletas de tu coach" : "Todos tus atletas") : "Todo el box",
    /** "los atletas del box que lo permiten" */
    de: deCoach ? (esAtleta ? "de tu coach" : "de tu cuenta") : "del box",
    /** "¿Aparecer en el leaderboard de tu box?" */
    tu: deCoach ? "de tu coach" : "de tu box",
    /** Subtítulo de la pantalla del atleta */
    subtitulo: deCoach ? `Atletas de ${user.box?.name ?? "tu coach"}` : (user.box?.name ?? "Tu box"),
  };
}
