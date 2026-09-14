from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field

from backend.schemas.common import Bloque, SanitizedModel


class ExerciseResponse(BaseModel):
    id: UUID
    name: str
    category: Optional[str] = None

    class Config:
        from_attributes = True


class SetUpdate(SanitizedModel):
    exercise_name: str | None = Field(None, min_length=1, max_length=100)
    prescribed_reps: int = Field(..., ge=1, le=100)
    rpe: float | None = Field(None, ge=0, le=10)
    prescribed_weight: float | None = Field(None, ge=0, le=1000)
    block: Bloque | None = None


class SetCreate(SanitizedModel):
    exercise_name: str = Field(..., min_length=1, max_length=100)
    prescribed_reps: int = Field(..., ge=1, le=100)
    rpe: float | None = Field(None, ge=0, le=10)
    prescribed_weight: float | None = Field(None, ge=0, le=1000)
    block: Bloque | None = None


class SetLogUpdate(SanitizedModel):
    """Lo que el ATLETA reporta tras entrenar: lo que hizo de verdad, no lo prescrito."""
    actual_reps: int | None = Field(None, ge=0, le=200)
    actual_weight: float | None = Field(None, ge=0, le=1000)
    technique_feedback: str | None = Field(None, max_length=500)


class SetResponse(BaseModel):
    id: UUID
    set_order: int
    block: Optional[str] = None
    prescribed_reps: int
    rpe: Optional[int] = None
    prescribed_weight: float | None = None
    prescribed_percentage: Optional[float] = None  # carga en % de 1RM (planes)
    reference_exercise: Optional[str] = None       # de qué 1RM se calcula ese %
    actual_reps: Optional[int] = None
    actual_weight: Optional[float] = None
    technique_feedback: Optional[str] = None
    exercise: ExerciseResponse

    class Config:
        from_attributes = True
