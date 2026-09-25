# Antes un solo archivo de 600+ líneas con los DTOs de los 9 dominios de la API mezclados.
# Se dividió por dominio (uno por endpoint agrupado en backend/routers/), pero el resto del
# código sigue haciendo `schemas.NombreDeClase` sin cambios: este __init__ reexporta todo para
# que ese acceso plano siga funcionando igual que cuando era un módulo único.
from backend.schemas.common import Bloque, Dia, FormatoWod, MessageResponse, SanitizedModel
from backend.schemas.auth import UserLogin, UserRegister
from backend.schemas.boxes import (
    AdminBoxPlanUpdate,
    AdminBoxRow,
    AdminBoxStatusUpdate,
    AdminPaymentCreate,
    AthleteCoachAssign,
    BoxDetail,
    BoxMember,
    BoxPublicInfo,
    BoxRegister,
    BoxSummary,
    BoxUpdate,
    CoachAccountRegister,
    CoachCreate,
    PricingPlan,
    PricingResponse,
)
from backend.schemas.users import (
    AthleteActivityResponse,
    AthleteLookupResponse,
    PRCreate,
    PRResponse,
    RecentSessionExercise,
    RecentSessionSummary,
    UserPreferencesUpdate,
    UserResponse,
)
from backend.schemas.fitness import FitnessBenchmarkUpdate, FitnessLevelResponse
from backend.schemas.sets import ExerciseResponse, SetCreate, SetLogUpdate, SetResponse, SetUpdate
from backend.schemas.sessions import (
    PersonalSessionCreate,
    SessionAdaptRequest,
    SessionCompleteRequest,
    SessionCreate,
    SessionMetaUpdate,
    SessionResponse,
    WodFormatUpdate,
)
from backend.schemas.mesocycles import (
    MesocycleCreate,
    MesocycleFullResponse,
    MesocycleManualCreate,
    MesocycleManualGroupCreate,
    MesocycleResponse,
    MesocycleSummaryResponse,
)
from backend.schemas.groups import (
    GroupCreate,
    GroupMemberAdd,
    GroupMemberResponse,
    GroupMesocycleAthlete,
    GroupMesocycleProgram,
    GroupProgramDelete,
    GroupResponse,
    GroupSessionExerciseAdd,
    GroupSessionExerciseDelete,
    GroupSessionExerciseUpdate,
    GroupSessionWodFormatUpdate,
    GroupSessionWodNotesUpdate,
    GroupSummaryResponse,
    WodDaySummary,
    WodLeaderboardRow,
)
from backend.schemas.ai import AIGenerateRequest, AIGenerateSmart, AIGenerateSmartGroup
from backend.schemas.admin import AdminOverview, AuditLogResponse, UserRoleUpdate
from backend.schemas.plans import (
    NivelPlan,
    PlanAcquireRequest,
    PlanCreate,
    PlanPreviewResponse,
    PlanPublishUpdate,
    PlanSessionPreview,
    PlanSetCreate,
    PlanSummaryResponse,
    PlanUpdate,
)

__all__ = [
    "Bloque", "Dia", "FormatoWod", "MessageResponse", "SanitizedModel",
    "UserLogin", "UserRegister",
    "AthleteActivityResponse", "PRCreate", "PRResponse", "RecentSessionExercise",
    "RecentSessionSummary", "UserPreferencesUpdate", "UserResponse", "AthleteLookupResponse",
    "FitnessBenchmarkUpdate", "FitnessLevelResponse",
    "ExerciseResponse", "SetCreate", "SetLogUpdate", "SetResponse", "SetUpdate",
    "PersonalSessionCreate",
    "SessionAdaptRequest", "SessionCompleteRequest", "SessionCreate", "SessionMetaUpdate", "SessionResponse", "WodFormatUpdate",
    "MesocycleCreate", "MesocycleFullResponse", "MesocycleManualCreate", "MesocycleManualGroupCreate",
    "MesocycleResponse", "MesocycleSummaryResponse",
    "GroupCreate", "GroupMemberAdd", "GroupMemberResponse", "GroupMesocycleAthlete", "GroupMesocycleProgram",
    "GroupProgramDelete",
    "GroupResponse", "GroupSessionExerciseAdd", "GroupSessionExerciseDelete", "GroupSessionExerciseUpdate",
    "GroupSessionWodFormatUpdate", "GroupSessionWodNotesUpdate", "GroupSummaryResponse", "WodDaySummary", "WodLeaderboardRow",
    "AIGenerateRequest", "AIGenerateSmart", "AIGenerateSmartGroup",
    "AdminOverview", "AuditLogResponse", "UserRoleUpdate",
    "NivelPlan", "PlanAcquireRequest", "PlanCreate", "PlanPreviewResponse", "PlanPublishUpdate",
    "PlanSessionPreview", "PlanSetCreate", "PlanSummaryResponse", "PlanUpdate",
]
