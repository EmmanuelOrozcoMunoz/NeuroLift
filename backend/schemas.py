from typing import Annotated, List, Literal, Optional
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, model_validator
from datetime import datetime, date

from backend.sanitize import clean_text

Dia = Annotated[int, Field(ge=0, le=6)]  # 0 = Lunes ... 6 = Domingo

# Parte de la sesión a la que pertenece un ejercicio. "warmup"/"strength"/"accessory" sirven
# para cualquier disciplina; "weightlifting"/"skills"/"metcon" son específicos de CrossFit;
# "main" es un cajón genérico para disciplinas que no necesitan más desglose que
# calentamiento + entrenamiento principal. None = sin bloque asignado.
Bloque = Literal["warmup", "strength", "weightlifting", "skills", "metcon", "accessory", "main"]


class SanitizedModel(BaseModel):
    """Base para esquemas de ENTRADA: sanea todo campo string (quita HTML/scripts, colapsa
    espacios, recorta) antes de que Pydantic valide los demás constraints. La contraseña se
    deja intacta (recortarla o limpiarla cambiaría lo que el usuario realmente escribió)."""

    @model_validator(mode="before")
    @classmethod
    def _sanitize_strings(cls, data):
        if isinstance(data, dict):
            return {
                key: (clean_text(value) if isinstance(value, str) and key != "password" else value)
                for key, value in data.items()
            }
        return data


class MessageResponse(BaseModel):
    message: str


# --- ESQUEMAS DE AUTENTICACIÓN ---
class UserRegister(SanitizedModel):
    email: EmailStr
    full_name: str = Field(..., min_length=1, max_length=100)
    password: str = Field(..., min_length=8, max_length=128)
    role: Literal["athlete", "coach"] = "athlete"
    body_weight: float | None = Field(None, ge=0, le=500)

class UserLogin(SanitizedModel):
    email: EmailStr
    password: str = Field(..., min_length=1, max_length=128)

# Actualizamos UserResponse para que también devuelva el rol al frontend
class UserResponse(BaseModel):
    id: UUID
    full_name: str
    email: str
    body_weight: float | None = None
    role: str # ¡Agregamos el rol aquí!
    has_avatar: bool = False  # true -> el cliente puede pedir GET /users/{id}/avatar
    created_at: datetime | None = None  # para mostrar "Miembro desde..." en el perfil

    class Config:
        from_attributes = True


# --- ESQUEMAS PARA MESOCICLOS ---
class MesocycleCreate(SanitizedModel):
    user_id: UUID
    name: str = Field(..., min_length=1, max_length=100)
    discipline: str = Field(..., min_length=1, max_length=50)
    start_date: date

class MesocycleResponse(BaseModel):
    id: UUID
    user_id: UUID
    name: str
    discipline: str
    start_date: date
    end_date: Optional[date] = None
    is_active: bool

    class Config:
        from_attributes = True


class MesocycleSummaryResponse(BaseModel):
    """GET /users/{id}/mesocycles/ — exactamente los campos que ya consume el frontend
    (ver web/src/lib/types.ts:MesocycleSummary). Antes este endpoint devolvía el modelo ORM
    crudo sin response_model; con esto queda con la misma lista blanca que el resto de la API."""
    id: UUID
    user_id: Optional[UUID] = None
    group_id: Optional[UUID] = None
    name: str | None = None
    discipline: str
    start_date: date
    end_date: Optional[date] = None
    is_active: bool
    created_at: Optional[datetime] = None
    description: Optional[str] = None
    level: Optional[str] = None

    class Config:
        from_attributes = True

# --- ESQUEMAS PARA SESIONES Y SERIES (CORREGIDOS) ---
class SessionCreate(SanitizedModel):
    mesocycle_id: UUID
    scheduled_date: date

class AIGenerateRequest(SanitizedModel):
    mesocycle_id: UUID
    context: str = Field(..., min_length=1, max_length=2000)
    weeks_count: int = Field(..., ge=1, le=52)
    sessions_per_week: int = Field(..., ge=1, le=7)

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
    prescribed_weight: float | None = None # <-- ¡ESTO FALTABA!
    prescribed_percentage: Optional[float] = None  # carga en % de 1RM (planes)
    reference_exercise: Optional[str] = None       # de qué 1RM se calcula ese %
    actual_reps: Optional[int] = None
    actual_weight: Optional[float] = None
    technique_feedback: Optional[str] = None
    exercise: ExerciseResponse

    class Config:
        from_attributes = True

class SessionResponse(BaseModel):
    id: UUID
    mesocycle_id: UUID
    scheduled_date: date
    completed_date: Optional[datetime] = None
    athlete_notes: Optional[str] = None
    status: str
    parent_session_id: Optional[UUID] = None  # si no es None, es una versión adaptada de otra sesión
    duration_minutes: Optional[int] = None
    day_offset: Optional[int] = None  # "día N" del plan (solo en plantillas)
    # --- resultado del WOD/metcon, ver models.py:Session ---
    wod_format: Optional[str] = None
    wod_time_cap_seconds: Optional[int] = None
    wod_time_seconds: Optional[int] = None
    wod_rounds: Optional[int] = None
    wod_extra_reps: Optional[int] = None
    wod_emom_completed: Optional[bool] = None
    wod_calories: Optional[float] = None
    wod_distance_meters: Optional[float] = None
    wod_watts: Optional[float] = None
    sets: List[SetResponse] = [] # ¡Aquí anidamos los sets!

    class Config:
        from_attributes = True


# Formatos estándar de WOD de CrossFit que el coach puede prescribir para una sesión.
FormatoWod = Literal["for_time", "amrap", "amrap_reps", "emom", "tabata", "1rm", "calories", "distance", "watts"]


class WodFormatUpdate(SanitizedModel):
    """El coach marca (o quita, mandando null) qué formato de WOD tiene esta sesión, y
    opcionalmente el timer: cap duro para "for_time", duración de la ventana para
    amrap/amrap_reps/calories/distance/watts. No aplica a emom/1rm."""
    wod_format: FormatoWod | None = None
    time_cap_seconds: int | None = Field(None, ge=1, le=36_000)


class SessionCompleteRequest(SanitizedModel):
    """Lo que el atleta reporta al terminar una sesión, si tenía un formato de WOD prescrito.
    Todo opcional: una sesión sin wod_format (o sin metcon) se completa sin mandar nada de esto."""
    wod_time_seconds: int | None = Field(None, ge=1, le=36_000)
    wod_rounds: int | None = Field(None, ge=0, le=500)
    wod_extra_reps: int | None = Field(None, ge=0, le=2000)
    wod_emom_completed: bool | None = None
    wod_calories: float | None = Field(None, ge=0, le=5000)
    wod_distance_meters: float | None = Field(None, ge=0, le=200_000)
    wod_watts: float | None = Field(None, ge=0, le=3000)


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

class MesocycleFullResponse(BaseModel):
    id: UUID
    user_id: Optional[UUID] = None  # None en las plantillas de planes (no tienen dueño)
    name: str | None = None # <-- Agregamos el nombre aquí también
    discipline: str
    start_date: date
    end_date: Optional[date] = None
    description: Optional[str] = None
    level: Optional[str] = None
    price: Optional[float] = None  # solo relevante en planes (is_template) — None en mesociclos normales
    is_template: bool = False
    has_cover_image: bool = False  # true -> el cliente puede pedir GET /plans/{id}/cover
    is_preview: bool = False  # ver PlanPreviewResponse: esta es SIEMPRE la versión completa
    sessions: List[SessionResponse] = [] # ¡Aquí anidamos las sesiones!

    class Config:
        from_attributes = True


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


class MesocycleManualCreate(SanitizedModel):
    user_id: UUID
    name: str = Field(..., min_length=1, max_length=100)
    discipline: str = Field(..., min_length=1, max_length=50)
    start_date: date
    weeks_count: int = Field(..., ge=1, le=52)
    training_days: List[Dia]  # 0 = Lunes, 1 = Martes ... 6 = Domingo

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


# --- ESQUEMAS PARA GRUPOS DE ATLETAS ---
class GroupCreate(SanitizedModel):
    name: str = Field(..., min_length=1, max_length=100)
    athlete_ids: List[UUID] = []

class GroupMemberAdd(SanitizedModel):
    athlete_ids: List[UUID]

class GroupMemberResponse(BaseModel):
    id: UUID
    full_name: str
    email: str

    class Config:
        from_attributes = True

class GroupResponse(BaseModel):
    id: UUID
    name: str
    created_at: datetime
    has_cover_image: bool = False  # true -> el cliente puede pedir GET /groups/{id}/cover
    members: List[GroupMemberResponse] = []

    class Config:
        from_attributes = True

class GroupSummaryResponse(BaseModel):
    id: UUID
    name: str
    created_at: datetime
    member_count: int
    coach_name: str | None = None  # solo relevante cuando lo consulta un admin
    has_cover_image: bool = False


# --- ESQUEMAS PARA PROGRAMAR MESOCICLOS A UN GRUPO COMPLETO ---
class MesocycleManualGroupCreate(SanitizedModel):
    group_id: UUID
    name: str = Field(..., min_length=1, max_length=100)
    discipline: str = Field(..., min_length=1, max_length=50)
    start_date: date
    weeks_count: int = Field(..., ge=1, le=52)
    training_days: List[Dia]

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


class GroupMesocycleAthlete(BaseModel):
    user_id: UUID
    full_name: str
    mesocycle_id: UUID
    is_active: bool

class GroupMesocycleProgram(BaseModel):
    """Un mesociclo programado para el grupo: mismo nombre/fechas, una instancia por atleta."""
    name: str
    discipline: str
    start_date: date
    end_date: Optional[date] = None
    created_at: datetime
    athletes: List[GroupMesocycleAthlete] = []
    session_dates: List[date] = []  # calendario compartido (todos los atletas entrenan los mismos días)


class GroupSessionExerciseAdd(SanitizedModel):
    """Añade el mismo ejercicio a la sesión de una fecha dada, para TODOS los atletas del programa."""
    program_name: str = Field(..., min_length=1, max_length=100)
    program_start_date: date
    scheduled_date: date
    exercise_name: str = Field(..., min_length=1, max_length=100)
    prescribed_sets: int = Field(3, ge=1, le=20)
    prescribed_reps: int = Field(..., ge=1, le=100)
    rpe: float | None = Field(None, ge=0, le=10)
    prescribed_weight: float | None = Field(None, ge=0, le=1000)
    block: Bloque | None = None


class GroupSessionExerciseUpdate(SanitizedModel):
    """Actualiza (nombre/series/reps/RPE/peso) un ejercicio ya existente en la sesión de una fecha
    dada, para TODOS los atletas del programa. Se identifica el ejercicio por su nombre ACTUAL;
    si se reduce el número de series se borran las sobrantes, si se aumenta se crean nuevas."""
    program_name: str = Field(..., min_length=1, max_length=100)
    program_start_date: date
    scheduled_date: date
    exercise_name: str = Field(..., min_length=1, max_length=100)
    new_exercise_name: str = Field(..., min_length=1, max_length=100)
    prescribed_sets: int = Field(..., ge=1, le=20)
    prescribed_reps: int = Field(..., ge=1, le=100)
    rpe: float | None = Field(None, ge=0, le=10)
    prescribed_weight: float | None = Field(None, ge=0, le=1000)
    block: Bloque | None = None


class GroupSessionExerciseDelete(SanitizedModel):
    """Elimina por completo un ejercicio (todas sus series) de la sesión de una fecha dada,
    para TODOS los atletas del programa."""
    program_name: str = Field(..., min_length=1, max_length=100)
    program_start_date: date
    scheduled_date: date
    exercise_name: str = Field(..., min_length=1, max_length=100)


class GroupSessionWodFormatUpdate(SanitizedModel):
    """El coach fija el formato de WOD (y su timer/time cap) UNA sola vez para la sesión de una
    fecha dada, aplicado a TODOS los atletas del programa a la vez — evita repetir la misma
    acción atleta por atleta cuando todo el grupo hace el mismo WOD."""
    program_name: str = Field(..., min_length=1, max_length=100)
    program_start_date: date
    scheduled_date: date
    wod_format: FormatoWod | None = None
    time_cap_seconds: int | None = Field(None, ge=1, le=36_000)


# --- ESQUEMAS PARA EL PANEL DE ADMINISTRACIÓN ---
class UserRoleUpdate(SanitizedModel):
    """Solo un admin puede cambiar el rol de un usuario (incluyendo promover a otro admin)."""
    role: Literal["athlete", "coach", "admin"]


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


# --- TABLA DE POSICIONES POR WOD (panel del coach) ---
class WodDaySummary(BaseModel):
    """Una fecha del grupo en la que hay un WOD prescrito (wod_format) — para que el coach
    elija cuál quiere ver en la tabla de posiciones por WOD."""
    scheduled_date: date
    wod_format: str
    # No se guarda aparte: es el nombre del ejercicio del bloque metabólico (ver main.py:
    # get_group_wod_days) — mismo texto que el coach ya escribió al armar la sesión.
    wod_name: Optional[str] = None
    time_cap_seconds: Optional[int] = None
    participants_count: int = 0


class WodLeaderboardRow(BaseModel):
    """Una fila de la tabla de posiciones de UN WOD específico: todos los atletas del grupo que
    lo tenían prescrito ese día, ordenados por su resultado según el formato (menor tiempo,
    más rondas/reps, más peso/calorías/distancia/vatios — ver _rank_wod_sessions). Los que
    todavía no lo completan aparecen al final, sin rank."""
    user_id: UUID
    full_name: str
    has_avatar: bool = False
    wod_format: str
    wod_name: Optional[str] = None  # ver WodDaySummary.wod_name
    score_label: Optional[str] = None
    rank: Optional[int] = None
    completed: bool = False


class AdminOverview(BaseModel):
    total_users: int
    total_coaches: int
    total_athletes: int
    total_admins: int
    total_groups: int
    total_mesocycles: int
    total_sessions: int
    sessions_completed: int
    sessions_pending: int


class AuditLogResponse(BaseModel):
    id: UUID
    created_at: Optional[datetime]
    level: str
    message: str

    class Config:
        from_attributes = True


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


# --- ESQUEMA PARA ADAPTAR UNA SESIÓN AL TIEMPO DISPONIBLE ---
class SessionAdaptRequest(SanitizedModel):
    available_minutes: int = Field(..., ge=10, le=180)


# --- ESQUEMAS PARA PLANES (plantillas vendibles, sin dueño) ---
NivelPlan = Literal["Principiante", "Intermedio", "Avanzado"]


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
