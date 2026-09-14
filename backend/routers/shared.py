"""Helpers usados por más de un router — si algo aquí solo lo necesitara un dominio, viviría
en ese router en vez de aquí."""
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from backend import models

# Extensiones de imagen aceptadas para avatares/portadas (usuario, grupo, plan) — mismo
# saneo en los tres (magic-number, re-render sin metadatos, ver backend/avatars.py).
AVATAR_CONTENT_TYPES = {".jpg": "image/jpeg", ".png": "image/png", ".webp": "image/webp"}


def get_owned_group(db: Session, group_id: UUID, current_user: models.User) -> models.Group:
    """Usado por groups.py, y también por mesocycles.py/ai.py al programar un mesociclo para
    un grupo completo (necesitan validar la misma pertenencia antes de tocarlo)."""
    grupo = db.query(models.Group).filter(models.Group.id == group_id).first()
    if not grupo:
        raise HTTPException(status_code=404, detail="Grupo no encontrado")
    if current_user.role != "admin" and grupo.coach_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Este grupo no te pertenece")
    return grupo


def get_or_create_exercise(db: Session, name: str) -> models.Exercise:
    """Usado por groups.py (bulk add/update de ejercicios), sessions.py (adaptar sesión),
    ai.py (generación) y plans.py (armar un plan) — cualquier flujo que reciba un nombre de
    ejercicio en texto libre y necesite su fila real."""
    ejercicio = db.query(models.Exercise).filter(models.Exercise.name == name).first()
    if not ejercicio:
        ejercicio = models.Exercise(name=name, category="Custom")
        db.add(ejercicio)
        db.flush()
    return ejercicio


_BLOQUES_VALIDOS = {"warmup", "strength", "weightlifting", "skills", "metcon", "accessory", "main"}


def clean_ai_block(value) -> str | None:
    """Normaliza el bloque que devuelve la IA: minúsculas, recortado, y descartado si no es uno
    de los valores válidos (ver schemas.Bloque) — mejor guardar None que un string inventado.
    Usado por sessions.py (adaptar sesión) y ai.py (generación)."""
    if not isinstance(value, str):
        return None
    limpio = value.strip().lower()
    return limpio if limpio in _BLOQUES_VALIDOS else None


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
