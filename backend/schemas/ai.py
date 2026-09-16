from datetime import date
from typing import Dict, List
from uuid import UUID

from pydantic import Field, field_validator

from backend.sanitize import clean_text
from backend.schemas.common import Dia, SanitizedModel

# Longitud máxima de la guía de un solo día — es una instrucción corta para la IA, no una nota
# larga (para eso ya está el campo "context" general del mesociclo).
_MAX_DAY_FOCUS_LENGTH = 300


def _clean_day_focus(value: Dict[int, str] | None) -> Dict[int, str] | None:
    """Sanea cada texto (SanitizedModel solo sanea los campos string de primer nivel, no los
    valores de un dict anidado) y descarta los días que quedaron vacíos tras limpiarlos."""
    if not value:
        return None
    limpio = {
        dia: texto_limpio
        for dia, texto in value.items()
        if (texto_limpio := clean_text(texto, max_length=_MAX_DAY_FOCUS_LENGTH))
    }
    return limpio or None


class AIGenerateRequest(SanitizedModel):
    mesocycle_id: UUID
    context: str = Field(..., min_length=1, max_length=2000)
    weeks_count: int = Field(..., ge=1, le=52)
    sessions_per_week: int = Field(..., ge=1, le=7)


class AIGenerateSmart(SanitizedModel):
    user_id: UUID
    name: str = Field(..., min_length=1, max_length=100)
    discipline: str = Field(..., min_length=1, max_length=50)
    start_date: date
    # Tope más bajo que en creación manual: cada 2 semanas dispara una llamada a Gemini,
    # así que 52 semanas serían ~26 llamadas encadenadas en un solo request.
    weeks_count: int = Field(..., ge=1, le=16)
    training_days: List[Dia]
    context: str = Field("", max_length=2000)
    session_duration_minutes: int | None = Field(None, ge=15, le=180)
    # Guía opcional por día de la semana (0=Lunes..6=Domingo) de lo que se quiere que la IA
    # prescriba ESE día en particular (ej. {0: "Sentadilla y accesorios de pierna"}) — se aplica
    # a TODAS las fechas de ese día del mesociclo, no solo la primera semana.
    day_focus: Dict[Dia, str] | None = None

    @field_validator("day_focus")
    @classmethod
    def _sanear_day_focus(cls, value: Dict[int, str] | None) -> Dict[int, str] | None:
        return _clean_day_focus(value)


class AIGenerateSmartGroup(SanitizedModel):
    group_id: UUID
    name: str = Field(..., min_length=1, max_length=100)
    discipline: str = Field(..., min_length=1, max_length=50)
    start_date: date
    # Mismo tope que la versión individual, y aquí se multiplica por cada atleta del grupo.
    weeks_count: int = Field(..., ge=1, le=16)
    training_days: List[Dia]
    context: str = Field("", max_length=2000)
    session_duration_minutes: int | None = Field(None, ge=15, le=180)
    day_focus: Dict[Dia, str] | None = None

    @field_validator("day_focus")
    @classmethod
    def _sanear_day_focus(cls, value: Dict[int, str] | None) -> Dict[int, str] | None:
        return _clean_day_focus(value)
