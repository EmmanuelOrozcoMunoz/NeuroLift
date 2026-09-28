"""Planes: copiar un plan publicado a un mesociclo propio del atleta. Sin HTTP ni commit: los
routers validan permisos y hacen commit."""
from dataclasses import dataclass, field
from datetime import date, timedelta
from uuid import UUID

from sqlalchemy.orm import Session

from backend import models
from backend.services.prs import get_athlete_prs, resolve_weight_from_percentage
from backend.services.sets import clonar_set

# Los planes guardan sus días como offset relativo (day_offset) más una fecha sintética
# (PLAN_EPOCH + day_offset) para no romper las columnas de fecha obligatorias.
PLAN_EPOCH = date(2000, 1, 1)


@dataclass
class ResultadoAdquisicion:
    mesocycle_id: UUID
    missing_prs: list[str] = field(default_factory=list)


def adquirir_plan(db: Session, plan: models.Mesocycle, atleta: models.User, start_date: date) -> ResultadoAdquisicion:
    """Clona el plan (ya validado como publicado y visible) a un mesociclo propio del atleta con
    las fechas reales a partir de `start_date` y las cargas en % resueltas con SUS marcas de 1RM."""
    prs = get_athlete_prs(db, atleta.id)

    nuevo_meso = models.Mesocycle(
        user_id=atleta.id,
        is_template=False,
        source_plan_id=plan.id,
        name=plan.name,
        discipline=plan.discipline,
        start_date=start_date,
        ai_prompt_context=plan.description,
    )
    db.add(nuevo_meso)
    db.flush()

    max_offset = 0
    sin_marca = set()

    for sesion_plan in sorted(plan.sessions, key=lambda s: (s.day_offset if s.day_offset is not None else 0)):
        offset = sesion_plan.day_offset
        if offset is None:
            offset = (sesion_plan.scheduled_date - PLAN_EPOCH).days
        max_offset = max(max_offset, offset)

        nueva_sesion = models.Session(
            mesocycle_id=nuevo_meso.id,
            scheduled_date=start_date + timedelta(days=offset),
            athlete_notes=sesion_plan.athlete_notes,
            status="pending",
            duration_minutes=sesion_plan.duration_minutes,
            warmup_notes=sesion_plan.warmup_notes,
            wod_notes=sesion_plan.wod_notes,
            wod_format=sesion_plan.wod_format,
            wod_time_cap_seconds=sesion_plan.wod_time_cap_seconds,
        )
        db.add(nueva_sesion)
        db.flush()

        for set_plan in sorted(sesion_plan.sets, key=lambda x: x.set_order):
            referencia = set_plan.reference_exercise or (set_plan.exercise.name if set_plan.exercise else "")
            peso = resolve_weight_from_percentage(set_plan.prescribed_percentage, set_plan.prescribed_weight, referencia, prs)
            if set_plan.prescribed_percentage and peso is None and referencia:
                sin_marca.add(referencia)

            db.add(clonar_set(set_plan, nueva_sesion.id, prescribed_weight=peso))

    nuevo_meso.end_date = start_date + timedelta(days=max_offset)
    return ResultadoAdquisicion(mesocycle_id=nuevo_meso.id, missing_prs=sorted(sin_marca))
