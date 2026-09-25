from datetime import date, datetime
from typing import List, Literal, Optional
from uuid import UUID

from pydantic import BaseModel, Field

from backend.schemas.common import Bloque, Dia, SanitizedModel

NivelPlan = Literal["Principiante", "Intermedio", "Avanzado"]


# --- ESQUEMAS PARA PLANES (plantillas vendibles, sin dueño) ---
class PlanCreate(SanitizedModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: str = Field("", max_length=2000)
    discipline: str = Field(..., min_length=1, max_length=50)
    level: NivelPlan = "Intermedio"
    price: float | None = Field(None, ge=0, le=100_000_000)  # amplio a propósito: sirve para COP, USD, etc.
    weeks_count: int = Field(..., ge=1, le=52)
    training_days: List[Dia]


class PlanPublishUpdate(SanitizedModel):
    is_published: bool
    # Quién lo ve en el catálogo: solo atletas del box del autor, o toda la plataforma. None =
    # conservar la visibilidad que ya tenía.
    visibility: Literal["box", "public"] | None = None


class PlanUpdate(SanitizedModel):
    """Edita los datos generales de un plan (nombre/descripción/disciplina/nivel/precio) — NO
    el calendario (weeks_count/training_days), que ya define los días que existen y cambiarlo
    requeriría recalcular sesiones ya creadas. Funciona igual esté publicado o en borrador:
    subir/bajar el precio de un plan ya publicado es una operación normal, no algo que deba
    bloquearse."""
    name: str = Field(..., min_length=1, max_length=100)
    description: str = Field("", max_length=2000)
    discipline: str = Field(..., min_length=1, max_length=50)
    level: NivelPlan = "Intermedio"
    price: float | None = Field(None, ge=0, le=100_000_000)


class PlanSetCreate(SanitizedModel):
    """Al armar un plan, la carga se define en kg fijos O en % de 1RM (no ambos)."""
    exercise_name: str = Field(..., min_length=1, max_length=100)
    prescribed_sets: int = Field(3, ge=1, le=20)
    prescribed_reps: int = Field(..., ge=1, le=100)
    rpe: float | None = Field(None, ge=0, le=10)
    prescribed_weight: float | None = Field(None, ge=0, le=1000)
    prescribed_percentage: float | None = Field(None, ge=1, le=150)
    reference_exercise: str | None = Field(None, min_length=1, max_length=100)
    block: Bloque | None = None


class PlanAcquireRequest(SanitizedModel):
    start_date: date


class PlanSummaryResponse(BaseModel):
    id: UUID
    name: str
    description: str | None = None
    discipline: str
    level: str | None = None
    price: float | None = None
    weeks_count: int
    sessions_count: int
    sessions_per_week: int
    coach_name: str | None = None
    is_published: bool
    has_cover_image: bool = False  # true -> el cliente puede pedir GET /plans/{id}/cover
    created_at: datetime
    visibility: Literal["box", "public"] = "box"
    # Box del autor — el catálogo lo muestra en planes públicos que vienen de OTRO box.
    box_name: str | None = None


class PlanSessionPreview(BaseModel):
    """Un día de un plan, SIN revelar sus ejercicios/series/pesos — solo la estructura (qué
    bloques trae y cuántos ejercicios). Ver PlanPreviewResponse."""
    id: UUID
    day_offset: Optional[int] = None
    blocks: List[str] = []
    exercise_count: int = 0


class PlanPreviewResponse(BaseModel):
    """Lo que ve de un plan cualquiera que NO sea su autor/admin (típicamente un atleta
    navegando el catálogo antes de comprarlo): mismos datos generales que MesocycleFullResponse,
    pero el contenido día por día se reduce a PlanSessionPreview — mostrar la programación
    completa (ejercicios, series, pesos) antes de pagar no tendría sentido comercial."""
    id: UUID
    name: str | None = None
    discipline: str
    start_date: date
    end_date: Optional[date] = None
    description: Optional[str] = None
    level: Optional[str] = None
    is_template: bool = True
    has_cover_image: bool = False
    is_preview: bool = True
    sessions: List[PlanSessionPreview] = []
