"""Planes de suscripción. La unidad que paga es la CUENTA (tabla boxes): un box, o el espacio
personal de un coach independiente — ambos con la misma tabla de precios, según cuántos atletas
tienen. El cobro por ahora es manual: el admin de plataforma registra cada pago desde su panel
(POST /admin/boxes/{id}/payment), que extiende `paid_until`.

Cambiar precios o límites es cambiar este diccionario; el frontend los lee de GET /boxes/pricing.
"""
from datetime import datetime, timedelta

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from backend import models

CURRENCY = "COP"
TRIAL_DAYS = 14
# Un "mes" de pago. 30 días fijos: simple de explicar y de calcular a mano.
PAYMENT_PERIOD_DAYS = 30

# Orden = de menor a mayor. max_athletes None = sin límite.
PLANS: dict[str, dict] = {
    "basic": {"name": "Básico", "max_athletes": 10, "monthly_price": 79_000},
    "pro": {"name": "Pro", "max_athletes": 30, "monthly_price": 149_000},
    "unlimited": {"name": "Ilimitado", "max_athletes": None, "monthly_price": 299_000},
}
DEFAULT_PLAN = "basic"


def trial_end_from(now: datetime | None = None) -> datetime:
    return (now or datetime.utcnow()) + timedelta(days=TRIAL_DAYS)


def subscription_status(box: models.Box, now: datetime | None = None) -> str:
    """"active" (pagado y vigente) | "trial" (en periodo de prueba) | "expired". Un pago vigente
    manda sobre la prueba."""
    now = now or datetime.utcnow()
    if box.paid_until is not None and box.paid_until >= now:
        return "active"
    if box.trial_ends_at is not None and box.trial_ends_at >= now:
        return "trial"
    return "expired"


def athletes_count(db: Session, box_id) -> int:
    return db.query(models.User).filter(models.User.box_id == box_id, models.User.role == "athlete").count()


def max_athletes(box: models.Box) -> int | None:
    return PLANS.get(box.plan, PLANS[DEFAULT_PLAN])["max_athletes"]


def ensure_can_add_athlete(db: Session, box: models.Box) -> None:
    """Se llama en TODO camino por el que un atleta nuevo entra a una cuenta (autoregistro con
    código o alta hecha por un coach). Los atletas que ya están nunca se bloquean: el límite solo
    frena a los nuevos."""
    es_coach = box.kind == "coach"
    if subscription_status(box) == "expired":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                "La suscripción de tu coach venció: no se pueden agregar atletas nuevos por ahora."
                if es_coach
                else "La suscripción de este box venció: no se pueden agregar atletas nuevos por ahora."
            ),
        )
    limite = max_athletes(box)
    if limite is not None and athletes_count(db, box.id) >= limite:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                f"Se alcanzó el límite de {limite} atletas del plan actual. Hay que subir de plan para agregar más."
            ),
        )
