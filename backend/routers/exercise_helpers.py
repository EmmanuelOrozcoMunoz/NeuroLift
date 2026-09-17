"""Helpers para resolver/normalizar ejercicios y su bloque — cualquier flujo que reciba un
nombre de ejercicio o un bloque en texto libre (de un formulario o de la IA) y necesite la
fila real o un valor validado."""
from sqlalchemy.orm import Session

from backend import models

_BLOQUES_VALIDOS = {"warmup", "strength", "weightlifting", "skills", "metcon", "accessory", "main"}


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


def clean_ai_block(value) -> str | None:
    """Normaliza el bloque que devuelve la IA: minúsculas, recortado, y descartado si no es uno
    de los valores válidos (ver schemas.Bloque) — mejor guardar None que un string inventado.
    Usado por sessions.py (adaptar sesión) y ai.py (generación)."""
    if not isinstance(value, str):
        return None
    limpio = value.strip().lower()
    return limpio if limpio in _BLOQUES_VALIDOS else None
