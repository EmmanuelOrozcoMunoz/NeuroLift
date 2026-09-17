"""Helpers alrededor de las marcas (1RM) de un atleta: sincronía con Fit Level, y resolución
de carga prescrita como % de 1RM a kg reales."""
from uuid import UUID

from sqlalchemy import func
from sqlalchemy.orm import Session

from backend import models

# Los 4 levantamientos de halterofilia del calculador de Fit Level son, ni más ni menos, un
# 1RM — lo mismo que ya representa una fila de PersonalRecord. Estos mapeos mantienen ambas
# tablas en sincronía sin importar por cuál pantalla se haya registrado (ver users.py y
# fitness.py, ambos los usan en direcciones opuestas).
FIT_LEVEL_LIFT_TO_PR_NAME = {
    "snatch_kg": "Snatch",
    "clean_jerk_kg": "Clean & Jerk",
    "back_squat_kg": "Back Squat",
    "deadlift_kg": "Deadlift",
}
PR_NAME_TO_FIT_LEVEL_LIFT = {name.lower(): key for key, name in FIT_LEVEL_LIFT_TO_PR_NAME.items()}


def upsert_personal_record_by_name(db: Session, user_id: UUID, exercise_name: str, max_weight_kg: float) -> None:
    """Como el endpoint POST /users/{id}/records/ (users.py), pero para uso interno (sync con
    Fit Level, en fitness.py): busca SIN importar mayúsculas/minúsculas, para no crear un
    duplicado si el ejercicio ya existía escrito distinto (p. ej. "back squat" vs "Back Squat")."""
    existente = db.query(models.PersonalRecord).filter(
        models.PersonalRecord.user_id == user_id,
        func.lower(models.PersonalRecord.exercise_name) == exercise_name.lower(),
    ).first()
    if existente:
        existente.max_weight_kg = max_weight_kg
    else:
        db.add(models.PersonalRecord(user_id=user_id, exercise_name=exercise_name, max_weight_kg=max_weight_kg))


def get_athlete_prs(db: Session, user_id: UUID) -> dict[str, float]:
    """Marcas (1RM) de un atleta, con la llave normalizada (minúsculas, recortada) para poder
    buscarlas por nombre sin importar mayúsculas — ver resolve_weight_from_percentage. Usado por
    sets.py, groups.py y plans.py: cualquier flujo que prescriba carga en % de 1RM."""
    return {
        pr.exercise_name.strip().lower(): pr.max_weight_kg
        for pr in db.query(models.PersonalRecord).filter(models.PersonalRecord.user_id == user_id).all()
    }


def resolve_weight_from_percentage(
    porcentaje: float | None, peso_fijo: float | None, referencia: str, prs: dict[str, float]
) -> float | None:
    """Convierte un % de 1RM a kg usando las marcas del atleta (ver get_athlete_prs), redondeando
    a múltiplos de 2.5kg. Si no viene porcentaje, se respeta el peso fijo tal cual; si viene
    porcentaje pero no hay marca de referencia, queda sin peso (el atleta o su coach lo ajusta a
    mano) — quien llama es responsable de avisar que esa carga quedó pendiente."""
    if porcentaje is None:
        return peso_fijo
    pr = prs.get(referencia.strip().lower())
    if not pr:
        return None
    return round((pr * porcentaje / 100) / 2.5) * 2.5
