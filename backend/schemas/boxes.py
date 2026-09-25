from datetime import datetime
from typing import Literal, Optional
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, field_validator

from backend.schemas.common import SanitizedModel

HEX_COLOR = r"^#[0-9a-fA-F]{6}$"
BoxStatus = Literal["pending", "active", "rejected", "suspended"]
BoxKind = Literal["box", "coach"]
PlanCode = Literal["basic", "pro", "unlimited"]
SubscriptionStatus = Literal["trial", "active", "expired"]


def _luminance(hex_color: str) -> float:
    """Luminancia relativa WCAG 2.x — misma fórmula que web/src/lib/brand.ts."""
    canales = []
    for i in (1, 3, 5):
        c = int(hex_color[i : i + 2], 16) / 255
        canales.append(c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4)
    return 0.2126 * canales[0] + 0.7152 * canales[1] + 0.0722 * canales[2]


def validate_accent(value: Optional[str]) -> Optional[str]:
    """El acento también se usa como color de texto sobre el fondo carbón (#121212): se rechaza
    uno que no llegue a 3:1 de contraste, igual que hace el frontend al aplicarlo."""
    if value is None:
        return None
    value = value.lower()
    contraste = (_luminance(value) + 0.05) / (_luminance("#121212") + 0.05)
    if contraste < 3:
        raise ValueError("Ese color es demasiado oscuro: no se distinguiría sobre el fondo de la app.")
    return value


class BoxAddress(SanitizedModel):
    address: Optional[str] = Field(None, max_length=255)
    city: Optional[str] = Field(None, max_length=100)
    state: Optional[str] = Field(None, max_length=100)
    country: Optional[str] = Field(None, max_length=100)


class BoxRegister(BoxAddress):
    """Alta pública de un box: crea el box (pendiente de aprobación) y la cuenta de su dueño."""
    box_name: str = Field(..., min_length=2, max_length=100)
    city: str = Field(..., min_length=1, max_length=100)
    owner_name: str = Field(..., min_length=1, max_length=100)
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)


class CoachAccountRegister(SanitizedModel):
    """Alta pública de un coach independiente (sin box): queda activo con prueba gratis."""
    full_name: str = Field(..., min_length=1, max_length=100)
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)


class BoxUpdate(BoxAddress):
    name: Optional[str] = Field(None, min_length=2, max_length=100)
    # "" o null = volver al acento por defecto de la app
    accent_color: Optional[str] = Field(None, pattern=HEX_COLOR + "|^$")

    @field_validator("accent_color")
    @classmethod
    def _accent(cls, value: Optional[str]) -> Optional[str]:
        return validate_accent(value or None)


class BoxSummary(BaseModel):
    """Lo que cualquier miembro del box ve de él (va embebido en /auth/me)."""
    id: UUID
    name: str
    city: Optional[str] = None
    status: BoxStatus
    kind: BoxKind = "box"
    accent_color: Optional[str] = None
    has_logo: bool = False

    class Config:
        from_attributes = True


class BoxDetail(BoxSummary):
    """Perfil completo del box para su dueño y sus coaches."""
    address: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None
    invite_code: Optional[str] = None
    created_at: Optional[datetime] = None
    # Suscripción (solo la recibe el dueño de la cuenta; ver routers/boxes.py:_box_detail)
    plan: Optional[PlanCode] = None
    subscription_status: Optional[SubscriptionStatus] = None
    trial_ends_at: Optional[datetime] = None
    paid_until: Optional[datetime] = None
    athletes_count: Optional[int] = None
    max_athletes: Optional[int] = None


class PricingPlan(BaseModel):
    code: PlanCode
    name: str
    max_athletes: Optional[int] = None
    monthly_price: int
    currency: str


class PricingResponse(BaseModel):
    trial_days: int
    plans: list[PricingPlan]


class BoxPublicInfo(BaseModel):
    """GET /boxes/by-code/{code}: lo mínimo para que el formulario de registro confirme a qué
    box se va a unir el atleta — sin dirección, miembros ni nada más."""
    name: str
    city: Optional[str] = None
    kind: BoxKind = "box"

    class Config:
        from_attributes = True


class BoxMember(BaseModel):
    """Una fila del listado de miembros que ve el dueño del box."""
    id: UUID
    full_name: str
    email: str
    role: str
    has_avatar: bool = False
    coach_id: Optional[UUID] = None
    coach_name: Optional[str] = None
    created_at: Optional[datetime] = None


class CoachCreate(SanitizedModel):
    """El dueño da de alta a un coach de su box con una contraseña inicial que le comparte."""
    full_name: str = Field(..., min_length=1, max_length=100)
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)


class AthleteCoachAssign(SanitizedModel):
    """null = el atleta queda "del box" (sin coach): recibe los mesociclos generales."""
    coach_id: Optional[UUID] = None


class AdminBoxRow(BaseModel):
    id: UUID
    name: str
    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None
    status: BoxStatus
    kind: BoxKind = "box"
    plan: PlanCode = "basic"
    subscription_status: SubscriptionStatus = "expired"
    trial_ends_at: Optional[datetime] = None
    paid_until: Optional[datetime] = None
    max_athletes: Optional[int] = None
    has_logo: bool = False
    owner_name: Optional[str] = None
    owner_email: Optional[str] = None
    coaches_count: int = 0
    athletes_count: int = 0
    created_at: Optional[datetime] = None


class AdminBoxStatusUpdate(SanitizedModel):
    status: BoxStatus


class AdminBoxPlanUpdate(SanitizedModel):
    plan: PlanCode


class AdminPaymentCreate(SanitizedModel):
    """Registra un pago manual: extiende la suscripción `months` periodos de 30 días, contados
    desde el vencimiento actual si sigue vigente, o desde hoy si ya venció."""
    months: int = Field(1, ge=1, le=12)
