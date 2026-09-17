/** Ejercicios de fuerza/halterofilia estándar para registrar una marca (1RM). Antes este campo
 *  era texto libre: un mismo levantamiento escrito de dos formas ("Back Squat" vs "back squat ")
 *  crea DOS marcas en vez de actualizar la misma — y como la IA arma su prompt listando TODAS
 *  las marcas del atleta, terminaba tratándolas como ejercicios distintos y generando sesiones
 *  redundantes con pesos distintos (uno por cada "duplicado"). Restringir a una lista fija
 *  elimina el problema de raíz: solo puede existir una marca por levantamiento. */
export const COMMON_PR_EXERCISES = [
  "Back Squat",
  "Front Squat",
  "Overhead Squat",
  "Deadlift",
  "Sumo Deadlift",
  "Snatch",
  "Clean & Jerk",
  "Clean",
  "Jerk",
  "Push Press",
  "Push Jerk",
  "Strict Press",
  "Bench Press",
  "Thruster",
] as const;
