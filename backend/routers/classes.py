"""Clases del box: horarios recurrentes con profesor (los crea el dueño), su programación (la
hace el profesor, como un bloque de varias semanas o día por día) y el registro de cada atleta.

Cómo se guarda el contenido: la programación de una clase es un Mesocycle con class_id y sin
atleta (user_id=None); cada sesión es lo que se hace en la clase ese día, con el mismo modelo de
series/WOD que cualquier entrenamiento, así que el profesor la edita con el editor de sesiones
de siempre. Cuando un atleta registra la clase, se le copia esa sesión a su mesociclo personal
"Clases del box" (is_class_log) y ahí anota lo que hizo, como en cualquier sesión suya.
"""
from datetime import date, timedelta
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload

from backend import models, schemas
from backend.core.security import can_program_class, ensure_can_program_class, get_current_user, require_owner
from backend.database import get_db
from backend.routers.pr_helpers import get_athlete_prs, resolve_weight_from_percentage
from backend.services.sets import clonar_set

router = APIRouter(prefix="/classes", tags=["classes"])

DAILY_PROGRAM_NAME = "Programación diaria"
CLASS_LOG_NAME = "Clases del box"
MAX_SCHEDULE_DAYS = 31


# ---------------------------------------------------------------- helpers

def _hhmm(value) -> str:
    return value.strftime("%H:%M")


def _ensure_box_member(user: models.User) -> models.Box:
    """Las clases son de un box activo (no de un coach independiente ni de la cuenta personal
    de un atleta solo); el admin de plataforma no pertenece a ninguno."""
    if user.box is None or not user.box.is_active or user.box.kind != "box":
        raise HTTPException(status_code=403, detail="Las clases son de un box activo")
    return user.box


def _get_class(db: Session, class_id: UUID, user: models.User) -> models.BoxClass:
    clase = (
        db.query(models.BoxClass)
        .options(joinedload(models.BoxClass.coach))
        .filter(models.BoxClass.id == class_id)
        .first()
    )
    # Una clase de otro box responde igual que una que no existe
    if not clase or (user.role != "admin" and clase.box_id != user.box_id):
        raise HTTPException(status_code=404, detail="Clase no encontrada")
    return clase


def _validate_coach(db: Session, box_id: UUID, coach_id: Optional[UUID]) -> Optional[models.User]:
    if coach_id is None:
        return None
    coach = db.query(models.User).filter(
        models.User.id == coach_id,
        models.User.box_id == box_id,
        models.User.role.in_(models.COACHING_ROLES),
    ).first()
    if not coach:
        raise HTTPException(status_code=400, detail="El profesor debe ser un coach de tu box")
    return coach


def _class_response(clase: models.BoxClass, user: models.User) -> schemas.ClassResponse:
    return schemas.ClassResponse(
        id=clase.id,
        name=clase.name,
        description=clase.description,
        coach_id=clase.coach_id,
        coach_name=clase.coach.full_name if clase.coach else None,
        weekdays=clase.weekday_list,
        start_time=_hhmm(clase.start_time),
        duration_minutes=clase.duration_minutes,
        is_active=clase.is_active,
        can_program=can_program_class(user, clase),
    )


def _programmed_dates(db: Session, class_id: UUID) -> set[date]:
    return {
        row[0]
        for row in db.query(models.Session.scheduled_date)
        .join(models.Mesocycle, models.Session.mesocycle_id == models.Mesocycle.id)
        .filter(models.Mesocycle.class_id == class_id)
        .all()
    }


# ------------------------------------------------------------ las clases

@router.get("/", response_model=List[schemas.ClassResponse])
def list_classes(
    include_inactive: bool = False,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Clases del box, ordenadas por hora. Cualquier miembro del box las ve."""
    box = _ensure_box_member(current_user)
    query = db.query(models.BoxClass).options(joinedload(models.BoxClass.coach)).filter(models.BoxClass.box_id == box.id)
    if not (include_inactive and current_user.role == "owner"):
        query = query.filter(models.BoxClass.is_active == True)  # noqa: E712
    clases = query.order_by(models.BoxClass.start_time, models.BoxClass.name).all()
    return [_class_response(c, current_user) for c in clases]


@router.post("/", response_model=schemas.ClassResponse)
def create_class(
    req: schemas.ClassCreate, db: Session = Depends(get_db), current_user: models.User = Depends(require_owner)
):
    box = current_user.box
    if box.kind != "box" or not box.is_active:
        raise HTTPException(status_code=403, detail="Las clases son de un box activo")
    _validate_coach(db, box.id, req.coach_id)
    clase = models.BoxClass(
        box_id=box.id,
        name=req.name,
        description=req.description,
        coach_id=req.coach_id,
        weekdays=",".join(str(d) for d in req.weekdays),
        start_time=req.start_time,
        duration_minutes=req.duration_minutes,
    )
    db.add(clase)
    db.commit()
    return _class_response(_get_class(db, clase.id, current_user), current_user)


@router.put("/{class_id}", response_model=schemas.ClassResponse)
def update_class(
    class_id: UUID,
    req: schemas.ClassUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_owner),
):
    """Cambiar el horario NO borra lo ya programado: el contenido de fechas que dejan de caer en
    los días de la clase se conserva y sigue apareciendo en el horario de esa fecha."""
    clase = _get_class(db, class_id, current_user)
    if req.name is not None:
        clase.name = req.name
    if req.description is not None:
        clase.description = req.description or None
    if req.clear_coach:
        clase.coach_id = None
    elif req.coach_id is not None:
        _validate_coach(db, clase.box_id, req.coach_id)
        clase.coach_id = req.coach_id
    if req.weekdays is not None:
        clase.weekdays = ",".join(str(d) for d in req.weekdays)
    if req.start_time is not None:
        clase.start_time = req.start_time
    if req.duration_minutes is not None:
        clase.duration_minutes = req.duration_minutes
    db.commit()
    return _class_response(_get_class(db, clase.id, current_user), current_user)


@router.delete("/{class_id}", response_model=schemas.MessageResponse)
def deactivate_class(class_id: UUID, db: Session = Depends(get_db), current_user: models.User = Depends(require_owner)):
    """Borrado lógico: la clase sale del horario, pero su programación y los registros que los
    atletas ya hicieron se conservan."""
    clase = _get_class(db, class_id, current_user)
    clase.is_active = False
    db.commit()
    return {"message": f"La clase '{clase.name}' ya no aparece en el horario."}


# ------------------------------------------------------------- horario

@router.get("/schedule", response_model=List[schemas.ClassOccurrence])
def get_schedule(
    start: date,
    days: int = Query(7, ge=1, le=MAX_SCHEDULE_DAYS),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Clases del box día por día entre `start` y `start + days`, con el profesor, el contenido
    programado de cada una y, si quien pregunta es atleta, si ya la registró."""
    box = _ensure_box_member(current_user)
    fin = start + timedelta(days=days - 1)

    clases = (
        db.query(models.BoxClass)
        .options(joinedload(models.BoxClass.coach))
        .filter(models.BoxClass.box_id == box.id, models.BoxClass.is_active == True)  # noqa: E712
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
    if current_user.role == "athlete" and sesiones:
        for copia in (
            db.query(models.Session)
            .join(models.Mesocycle, models.Session.mesocycle_id == models.Mesocycle.id)
            .filter(
                models.Mesocycle.user_id == current_user.id,
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
                start_time=_hhmm(clase.start_time),
                duration_minutes=clase.duration_minutes,
                coach_id=clase.coach_id,
                coach_name=clase.coach.full_name if clase.coach else None,
                can_program=can_program_class(current_user, clase),
                session=schemas.SessionResponse.model_validate(sesion) if sesion else None,
                program_mesocycle_id=sesion.mesocycle_id if sesion else None,
                program_name=sesion.mesocycle.name if sesion else None,
                my_session_id=mio.id if mio else None,
                my_mesocycle_id=mio.mesocycle_id if mio else None,
                my_status=mio.status if mio else None,
            ))
    resultado.sort(key=lambda o: (o.date, o.start_time, o.class_name))
    return resultado


# --------------------------------------------------------- programación

@router.get("/{class_id}/programs", response_model=List[schemas.ClassProgramResponse])
def list_class_programs(class_id: UUID, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    clase = _get_class(db, class_id, current_user)
    ensure_can_program_class(current_user, clase)
    programas = (
        db.query(models.Mesocycle)
        .filter(models.Mesocycle.class_id == clase.id)
        .order_by(models.Mesocycle.start_date.desc())
        .all()
    )
    return [
        schemas.ClassProgramResponse(
            id=p.id,
            name=p.name,
            start_date=p.start_date,
            end_date=p.end_date,
            sessions_count=db.query(models.Session).filter(models.Session.mesocycle_id == p.id).count(),
        )
        for p in programas
    ]


@router.post("/{class_id}/programs", response_model=schemas.ClassProgramResponse)
def create_class_program(
    class_id: UUID,
    req: schemas.ClassProgramCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Programa la clase "como un mesociclo": crea una sesión vacía por cada día que se dicta la
    clase en las próximas `weeks_count` semanas, lista para que el profesor le cargue ejercicios.
    Las fechas que ya tenían contenido se saltan (nunca se pisa lo ya programado)."""
    clase = _get_class(db, class_id, current_user)
    ensure_can_program_class(current_user, clase)
    if not clase.is_active:
        raise HTTPException(status_code=400, detail="Esta clase ya no está en el horario")

    ocupadas = _programmed_dates(db, clase.id)
    fechas: list[date] = []
    saltadas: list[date] = []
    for i in range(req.weeks_count * 7):
        dia = req.start_date + timedelta(days=i)
        if dia.weekday() not in clase.weekday_list:
            continue
        (saltadas if dia in ocupadas else fechas).append(dia)
    if not fechas:
        raise HTTPException(status_code=400, detail="Todas esas fechas ya tienen contenido programado")

    programa = models.Mesocycle(
        user_id=None,
        class_id=clase.id,
        box_id=clase.box_id,
        name=req.name,
        discipline="Clase",
        start_date=fechas[0],
        end_date=fechas[-1],
        is_active=True,
    )
    db.add(programa)
    db.flush()
    for dia in fechas:
        db.add(models.Session(mesocycle_id=programa.id, scheduled_date=dia, status="pending", athlete_notes=""))
    db.commit()
    return schemas.ClassProgramResponse(
        id=programa.id,
        name=programa.name,
        start_date=programa.start_date,
        end_date=programa.end_date,
        sessions_count=len(fechas),
        skipped_dates=saltadas,
    )


@router.post("/{class_id}/days", response_model=schemas.ClassDayResponse)
def create_class_day(
    class_id: UUID,
    req: schemas.ClassDayCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Programa la clase día por día. Si ese día ya tiene contenido, devuelve esa misma sesión
    (idempotente): así "Programar este día" siempre lleva al editor correcto."""
    clase = _get_class(db, class_id, current_user)
    ensure_can_program_class(current_user, clase)

    existente = (
        db.query(models.Session)
        .join(models.Mesocycle, models.Session.mesocycle_id == models.Mesocycle.id)
        .filter(models.Mesocycle.class_id == clase.id, models.Session.scheduled_date == req.date)
        .order_by(models.Session.created_at)
        .first()
    )
    if existente:
        return schemas.ClassDayResponse(mesocycle_id=existente.mesocycle_id, session_id=existente.id)

    diaria = db.query(models.Mesocycle).filter(
        models.Mesocycle.class_id == clase.id, models.Mesocycle.name == DAILY_PROGRAM_NAME
    ).first()
    if not diaria:
        diaria = models.Mesocycle(
            user_id=None,
            class_id=clase.id,
            box_id=clase.box_id,
            name=DAILY_PROGRAM_NAME,
            discipline="Clase",
            start_date=req.date,
            is_active=True,
        )
        db.add(diaria)
        db.flush()
    diaria.start_date = min(diaria.start_date, req.date)
    diaria.end_date = max(diaria.end_date or req.date, req.date)
    sesion = models.Session(mesocycle_id=diaria.id, scheduled_date=req.date, status="pending", athlete_notes="")
    db.add(sesion)
    db.commit()
    return schemas.ClassDayResponse(mesocycle_id=diaria.id, session_id=sesion.id)


# ------------------------------------------------ registro del atleta

@router.post("/sessions/{session_id}/join", response_model=schemas.ClassJoinResponse)
def join_class_session(session_id: UUID, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    """El atleta registra la clase de un día: se le copia el contenido a su mesociclo "Clases del
    box" (con las cargas en % resueltas con SUS marcas) y ahí anota lo que hizo con la pantalla
    de siempre. Idempotente: si ya la había registrado, devuelve la misma copia."""
    if current_user.role != "athlete":
        raise HTTPException(status_code=403, detail="Solo los atletas registran clases")
    _ensure_box_member(current_user)

    clase_sesion = (
        db.query(models.Session)
        .options(
            joinedload(models.Session.mesocycle).joinedload(models.Mesocycle.box_class),
            joinedload(models.Session.sets).joinedload(models.Set.exercise),
        )
        .filter(models.Session.id == session_id)
        .first()
    )
    if (
        not clase_sesion
        or clase_sesion.mesocycle.class_id is None
        or clase_sesion.mesocycle.box_class.box_id != current_user.box_id
    ):
        raise HTTPException(status_code=404, detail="Clase no encontrada")
    if clase_sesion.scheduled_date > date.today():
        raise HTTPException(status_code=400, detail="Podrás registrar esta clase el día que se dicte")

    registro = db.query(models.Mesocycle).filter(
        models.Mesocycle.user_id == current_user.id, models.Mesocycle.is_class_log == True  # noqa: E712
    ).first()
    if not registro:
        registro = models.Mesocycle(
            user_id=current_user.id,
            box_id=current_user.box_id,
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
        return schemas.ClassJoinResponse(mesocycle_id=registro.id, session_id=copia.id)

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

    prs = get_athlete_prs(db, current_user.id)
    sin_marca: set[str] = set()
    for serie in sorted(clase_sesion.sets, key=lambda x: x.set_order):
        referencia = serie.reference_exercise or (serie.exercise.name if serie.exercise else "")
        peso = resolve_weight_from_percentage(serie.prescribed_percentage, serie.prescribed_weight, referencia, prs)
        if serie.prescribed_percentage is not None and peso is None and referencia:
            sin_marca.add(referencia)
        db.add(clonar_set(serie, copia.id, prescribed_weight=peso))
    db.commit()
    return schemas.ClassJoinResponse(mesocycle_id=registro.id, session_id=copia.id, missing_prs=sorted(sin_marca))


@router.delete("/sessions/{session_id}/join", response_model=schemas.MessageResponse)
def leave_class_session(session_id: UUID, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    """El atleta quita el registro de una clase (p. ej. la registró por error): se borra SU
    copia, con lo que haya anotado. La clase del profesor no se toca, y puede volver a
    registrarla cuando quiera. Si ya la había marcado como hecha, deja de contar en su historial
    y en la actividad del box."""
    if current_user.role != "athlete":
        raise HTTPException(status_code=403, detail="Solo los atletas registran clases")
    copia = (
        db.query(models.Session)
        .join(models.Mesocycle, models.Session.mesocycle_id == models.Mesocycle.id)
        .filter(
            models.Session.class_session_id == session_id,
            models.Mesocycle.user_id == current_user.id,
            models.Mesocycle.is_class_log == True,  # noqa: E712
        )
        .first()
    )
    if not copia:
        raise HTTPException(status_code=404, detail="No tenías registrada esta clase")
    db.delete(copia)
    db.commit()
    return {"message": "Quitaste el registro de esta clase."}
