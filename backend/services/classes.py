"""Reglas de las clases del box que no dependen de HTTP: armar el horario y copiar una clase al
registro personal de un atleta. Los routers validan permisos y traducen a respuestas; aquí solo
se trabaja con la base de datos (sin commit: lo hace quien llama)."""
from dataclasses import dataclass, field
from datetime import date, timedelta
from uuid import UUID

from sqlalchemy.orm import Session, joinedload

from backend import models, schemas
from backend.core.security import can_program_class
from backend.routers.pr_helpers import get_athlete_prs, resolve_weight_from_percentage
from backend.services.sets import clonar_set

CLASS_LOG_NAME = "Clases del box"


def hhmm(value) -> str:
    return value.strftime("%H:%M")


@dataclass
class ResultadoRegistro:
    mesocycle_id: UUID
    session_id: UUID
    missing_prs: list[str] = field(default_factory=list)


def registrar_clase(db: Session, atleta: models.User, clase_sesion: models.Session) -> ResultadoRegistro:
    """Copia la sesión de una clase al mesociclo personal "Clases del box" del atleta, con las
    cargas en % resueltas con SUS marcas. Idempotente: si ya la había registrado, devuelve la
    misma copia. Ya validado por el router: el atleta es del box y la fecha ya llegó."""
    registro = db.query(models.Mesocycle).filter(
        models.Mesocycle.user_id == atleta.id, models.Mesocycle.is_class_log == True  # noqa: E712
    ).first()
    if not registro:
        registro = models.Mesocycle(
            user_id=atleta.id,
            box_id=atleta.box_id,
            name=CLASS_LOG_NAME,
            discipline="Clase",
            start_date=clase_sesion.scheduled_date,
            is_active=True,
            is_class_log=True,
        )
        db.add(registro)
        db.flush()

    copia = db.query(models.Session).filter(
        models.Session.mesocycle_id == registro.id, models.Session.class_session_id == clase_sesion.id
    ).first()
    if copia:
        return ResultadoRegistro(mesocycle_id=registro.id, session_id=copia.id)

    registro.start_date = min(registro.start_date, clase_sesion.scheduled_date)
    registro.end_date = max(registro.end_date or clase_sesion.scheduled_date, clase_sesion.scheduled_date)

    copia = models.Session(
        mesocycle_id=registro.id,
        class_session_id=clase_sesion.id,
        scheduled_date=clase_sesion.scheduled_date,
        status="pending",
        # El nombre de la clase queda visible en la copia (en su historial se lee "CrossFit 6 am")
        athlete_notes=clase_sesion.athlete_notes or clase_sesion.mesocycle.box_class.name,
        block_order=clase_sesion.block_order,
        warmup_notes=clase_sesion.warmup_notes,
        wod_notes=clase_sesion.wod_notes,
        wod_format=clase_sesion.wod_format,
        wod_time_cap_seconds=clase_sesion.wod_time_cap_seconds,
        duration_minutes=clase_sesion.mesocycle.box_class.duration_minutes,
    )
    db.add(copia)
    db.flush()

    prs = get_athlete_prs(db, atleta.id)
    sin_marca: set[str] = set()
    for serie in sorted(clase_sesion.sets, key=lambda x: x.set_order):
        referencia = serie.reference_exercise or (serie.exercise.name if serie.exercise else "")
        peso = resolve_weight_from_percentage(serie.prescribed_percentage, serie.prescribed_weight, referencia, prs)
        if serie.prescribed_percentage is not None and peso is None and referencia:
            sin_marca.add(referencia)
        db.add(clonar_set(serie, copia.id, prescribed_weight=peso))
    return ResultadoRegistro(mesocycle_id=registro.id, session_id=copia.id, missing_prs=sorted(sin_marca))


def armar_horario(db: Session, usuario: models.User, box_id: UUID, start: date, days: int) -> list[schemas.ClassOccurrence]:
    """Clases del box día por día entre `start` y `start + days`, con profesor, contenido
    programado y, si quien pregunta es atleta, si ya la registró."""
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

    mis_registros: dict[UUID, models.Session] = {}
    if usuario.role == "athlete" and sesiones:
        for copia in (
            db.query(models.Session)
            .join(models.Mesocycle, models.Session.mesocycle_id == models.Mesocycle.id)
            .filter(
                models.Mesocycle.user_id == usuario.id,
                models.Mesocycle.is_class_log == True,  # noqa: E712
                models.Session.class_session_id.in_([s.id for s in sesiones]),
            )
            .all()
        ):
            mis_registros[copia.class_session_id] = copia

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
            mio = mis_registros.get(sesion.id) if sesion else None
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
                my_session_id=mio.id if mio else None,
                my_mesocycle_id=mio.mesocycle_id if mio else None,
                my_status=mio.status if mio else None,
            ))
    resultado.sort(key=lambda o: (o.date, o.start_time, o.class_name))
    return resultado
