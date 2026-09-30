"""Reglas de las clases del box que no dependen de HTTP: armar el horario que ven los
entrenadores. Los routers validan permisos y traducen a respuestas; aquí solo se trabaja con la
base de datos."""
from datetime import date, timedelta
from uuid import UUID

from sqlalchemy.orm import Session, joinedload

from backend import models, schemas
from backend.core.security import can_program_class


def hhmm(value) -> str:
    return value.strftime("%H:%M")


def armar_horario(db: Session, usuario: models.User, box_id: UUID, start: date, days: int) -> list[schemas.ClassOccurrence]:
    """Clases del box día por día entre `start` y `start + days`, con profesor y contenido
    programado. Solo para entrenadores del box: el contenido es confidencial."""
    fin = start + timedelta(days=days - 1)

    clases = (
        db.query(models.BoxClass)
        .options(joinedload(models.BoxClass.coach))
        .filter(models.BoxClass.box_id == box_id, models.BoxClass.is_active == True)  # noqa: E712
        .all()
    )
    if not clases:
        return []
    por_id = {c.id: c for c in clases}

    sesiones = (
        db.query(models.Session)
        .join(models.Mesocycle, models.Session.mesocycle_id == models.Mesocycle.id)
        .options(joinedload(models.Session.sets).joinedload(models.Set.exercise), joinedload(models.Session.mesocycle))
        .filter(
            models.Mesocycle.class_id.in_(list(por_id)),
            models.Session.scheduled_date >= start,
            models.Session.scheduled_date <= fin,
            models.Session.parent_session_id.is_(None),
        )
        .order_by(models.Session.created_at)
        .all()
    )
    contenido: dict[tuple, models.Session] = {}
    for s in sesiones:
        contenido.setdefault((s.mesocycle.class_id, s.scheduled_date), s)

    resultado: list[schemas.ClassOccurrence] = []
    for i in range(days):
        dia = start + timedelta(days=i)
        for clase in clases:
            sesion = contenido.get((clase.id, dia))
            # Días de la clase, más cualquier fecha que ya tenga contenido aunque el horario
            # haya cambiado después (lo programado no desaparece)
            if dia.weekday() not in clase.weekday_list and sesion is None:
                continue
            if sesion:
                sesion.sets.sort(key=lambda x: x.set_order)
            resultado.append(schemas.ClassOccurrence(
                class_id=clase.id,
                class_name=clase.name,
                description=clase.description,
                date=dia,
                start_time=hhmm(clase.start_time),
                duration_minutes=clase.duration_minutes,
                coach_id=clase.coach_id,
                coach_name=clase.coach.full_name if clase.coach else None,
                can_program=can_program_class(usuario, clase),
                session=schemas.SessionResponse.model_validate(sesion) if sesion else None,
                program_mesocycle_id=sesion.mesocycle_id if sesion else None,
                program_name=sesion.mesocycle.name if sesion else None,
            ))
    resultado.sort(key=lambda o: (o.date, o.start_time, o.class_name))
    return resultado
