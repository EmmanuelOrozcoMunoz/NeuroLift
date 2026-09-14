"""Puntuación y ranking de WODs — compartido entre el leaderboard general de un atleta
(backend/routers/users.py) y el leaderboard por WOD de un grupo (backend/routers/groups.py),
por eso vive aparte en vez de dentro de cualquiera de los dos routers."""
from backend import models

# Formatos donde un número MENOR es mejor resultado (todos los demás: mayor es mejor).
_WOD_LOWER_IS_BETTER = {"for_time"}


def format_wod_summary(sesion: "models.Session | None") -> str | None:
    """Texto corto y legible del resultado de un WOD, según su formato — para la tabla de
    posiciones del coach (el detalle completo vive en /users/{id}/recent-activity)."""
    if sesion is None or not sesion.wod_format:
        return None
    if sesion.wod_format == "for_time" and sesion.wod_time_seconds is not None:
        minutos, segundos = divmod(sesion.wod_time_seconds, 60)
        return f"Por tiempo: {minutos}:{segundos:02d}"
    if sesion.wod_format == "amrap" and (sesion.wod_rounds is not None or sesion.wod_extra_reps is not None):
        rondas = sesion.wod_rounds or 0
        reps = sesion.wod_extra_reps or 0
        return f"AMRAP: {rondas} rondas + {reps} reps" if reps else f"AMRAP: {rondas} rondas"
    if sesion.wod_format == "amrap_reps" and sesion.wod_extra_reps is not None:
        return f"AMRAP: {sesion.wod_extra_reps} reps"
    if sesion.wod_format == "tabata" and sesion.wod_extra_reps is not None:
        return f"Tabata: {sesion.wod_extra_reps} reps (peor ronda)"
    if sesion.wod_format == "emom" and sesion.wod_emom_completed is not None:
        return "EMOM: cumplido ✓" if sesion.wod_emom_completed else "EMOM: no completo ✗"
    if sesion.wod_format == "1rm":
        pesos = [s.actual_weight for s in sesion.sets if s.actual_weight]
        if pesos:
            return f"1RM: {max(pesos):g} kg"
    if sesion.wod_format == "calories" and sesion.wod_calories is not None:
        return f"{sesion.wod_calories:g} cal"
    if sesion.wod_format == "distance" and sesion.wod_distance_meters is not None:
        return f"{sesion.wod_distance_meters:g} m"
    if sesion.wod_format == "watts" and sesion.wod_watts is not None:
        return f"{sesion.wod_watts:g} W"
    return None


def wod_score_value(sesion: "models.Session") -> float | None:
    """Valor numérico para ordenar el leaderboard de un WOD — None si el atleta no reportó
    (o no le aplica) resultado para el formato prescrito."""
    fmt = sesion.wod_format
    if fmt == "for_time":
        return sesion.wod_time_seconds
    if fmt == "amrap":
        if sesion.wod_rounds is None and sesion.wod_extra_reps is None:
            return None
        # Reps "sueltas" como fracción de ronda: permite comparar en un solo número ordenable
        # sin saber cuántas reps tiene una ronda completa de este WOD en particular.
        return (sesion.wod_rounds or 0) + (sesion.wod_extra_reps or 0) / 10_000
    if fmt == "amrap_reps":
        return sesion.wod_extra_reps
    if fmt == "tabata":
        return sesion.wod_extra_reps
    if fmt == "emom":
        if sesion.wod_emom_completed is None:
            return None
        return 1.0 if sesion.wod_emom_completed else 0.0
    if fmt == "1rm":
        pesos = [s.actual_weight for s in sesion.sets if s.actual_weight]
        return max(pesos) if pesos else None
    if fmt == "calories":
        return sesion.wod_calories
    if fmt == "distance":
        return sesion.wod_distance_meters
    if fmt == "watts":
        return sesion.wod_watts
    return None


def rank_wod_sessions(sesiones: "list[models.Session]") -> "list[models.Session]":
    """Ordena sesiones COMPLETADAS del mismo WOD por su resultado (mejor primero). Las que no
    reportaron un valor numérico (formato sin datos suficientes) quedan al final, en el orden
    en que llegaron."""
    con_score = [(s, wod_score_value(s)) for s in sesiones]
    ascendente = sesiones[0].wod_format in _WOD_LOWER_IS_BETTER if sesiones else False
    con_resultado = [(s, v) for s, v in con_score if v is not None]
    sin_resultado = [s for s, v in con_score if v is None]
    con_resultado.sort(key=lambda x: x[1], reverse=not ascendente)
    return [s for s, _ in con_resultado] + sin_resultado
