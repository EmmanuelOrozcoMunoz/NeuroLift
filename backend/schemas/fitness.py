from typing import Literal

from pydantic import BaseModel, Field

from backend.schemas.common import SanitizedModel


# --- ESQUEMAS PARA EL CALCULADOR DE "FIT LEVEL" (halterofilia / gimnasia / metcon) ---
class FitnessBenchmarkUpdate(SanitizedModel):
    """Todos los campos son opcionales: el atleta llena solo las marcas que ya tiene."""
    body_weight: float | None = Field(None, ge=20, le=300)
    sex: Literal["male", "female"] | None = None
    age: int | None = Field(None, ge=10, le=100)
    # Halterofilia (1RM en kg)
    snatch_kg: float | None = Field(None, ge=0, le=400)
    clean_jerk_kg: float | None = Field(None, ge=0, le=400)
    back_squat_kg: float | None = Field(None, ge=0, le=500)
    deadlift_kg: float | None = Field(None, ge=0, le=500)
    # Gimnasia (repeticiones máximas)
    pull_ups_max: int | None = Field(None, ge=0, le=200)
    push_ups_max: int | None = Field(None, ge=0, le=500)
    muscle_ups_max: int | None = Field(None, ge=0, le=100)
    hspu_max: int | None = Field(None, ge=0, le=200)
    # Metcon (tiempo en segundos, salvo Cindy que es AMRAP de repeticiones)
    fran_seconds: int | None = Field(None, ge=30, le=3600)
    grace_seconds: int | None = Field(None, ge=30, le=3600)
    cindy_total_reps: int | None = Field(None, ge=0, le=2000)
    row_2k_seconds: int | None = Field(None, ge=300, le=3600)


class FitnessLevelResponse(BaseModel):
    body_weight: float | None = None
    sex: str | None = None
    age: int | None = None
    values: dict[str, float] = {}
    category_scores: dict[str, float] = {}
    category_levels: dict[str, str] = {}
    overall_score: float | None = None
    overall_level: str | None = None
