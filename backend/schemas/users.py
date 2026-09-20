from datetime import date, datetime
from typing import List, Literal, Optional
from uuid import UUID

from pydantic import BaseModel, Field

from backend.schemas.common import SanitizedModel


# Actualizamos UserResponse para que también devuelva el rol al frontend
class UserResponse(BaseModel):
    id: UUID
    full_name: str
    email: str
    body_weight: float | None = None
    role: str  # ¡Agregamos el rol aquí!
    has_avatar: bool = False  # true -> el cliente puede pedir GET /users/{id}/avatar
    created_at: datetime | None = None  # para mostrar "Miembro desde..." en el perfil
    # "kg" | "lb" — en qué unidad este usuario prefiere ver/escribir cualquier peso en la app.
    weight_unit: str | None = None
    # "male" | "female" — para saber el peso de SU barra (20kg / 15kg) en la calculadora de discos.
    sex: str | None = None
    # Si su box tiene discos de 25kg — null se trata como True en el frontend.
    has_25kg_plates: bool | None = None

    class Config:
        from_attributes = True


class UserPreferencesUpdate(SanitizedModel):
    # Ambos opcionales: cada toggle (unidad de peso, disponibilidad de discos de 25kg) guarda
    # solo lo suyo, sin obligar a mandar el resto de las preferencias en la misma llamada.
    weight_unit: Literal["kg", "lb"] | None = None
    has_25kg_plates: bool | None = None


class PRResponse(BaseModel):
    id: UUID
    exercise_name: str
    max_weight_kg: float
    last_updated: datetime

    class Config:
        from_attributes = True


# Esquema rápido para recibir la marca
class PRCreate(SanitizedModel):
    exercise_name: str = Field(..., min_length=1, max_length=100)
    max_weight_kg: float = Field(..., ge=0, le=1000)


# --- TABLA DE POSICIONES DE ACTIVIDAD (panel del coach) ---
class AthleteActivityResponse(BaseModel):
    """Una fila de la 'tabla de posiciones': cuántos entrenamientos ha completado este atleta
    (los que él mismo marcó como hechos, con sus pesos/reps reales) — visibilidad que antes el
    coach no tenía sin entrar mesociclo por mesociclo."""
    user_id: UUID
    full_name: str
    has_avatar: bool = False
    completed_total: int = 0
    completed_this_week: int = 0
    last_completed_at: Optional[datetime] = None
    # Texto ya armado del lado del servidor (ej. "Fran: 12:34", "AMRAP: 5 rondas + 12 reps") del
    # último WOD con resultado registrado — el detalle completo (ejercicio por ejercicio, con
    # los pesos reales) vive en GET /users/{id}/recent-activity, no aquí, para no saturar la fila.
    last_wod_summary: Optional[str] = None


# GET /users/{id}/recent-activity — una sesión ya completada, con lo REALMENTE hecho.
class RecentSessionExercise(BaseModel):
    """Un ejercicio ya completado, con lo REALMENTE hecho (no lo prescrito) — para que el coach
    vea sin adivinar qué pesos está moviendo su atleta."""
    exercise_name: str
    block: Optional[str] = None
    sets_logged: int = 0
    actual_reps: List[int] = []
    actual_weight: List[float] = []


class RecentSessionSummary(BaseModel):
    session_id: UUID
    scheduled_date: date
    completed_date: Optional[datetime] = None
    mesocycle_name: str | None = None
    discipline: str
    wod_format: Optional[str] = None
    wod_time_cap_seconds: Optional[int] = None
    wod_time_seconds: Optional[int] = None
    wod_rounds: Optional[int] = None
    wod_extra_reps: Optional[int] = None
    wod_emom_completed: Optional[bool] = None
    wod_calories: Optional[float] = None
    wod_distance_meters: Optional[float] = None
    wod_watts: Optional[float] = None
    exercises: List[RecentSessionExercise] = []
