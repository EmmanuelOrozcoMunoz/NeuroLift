from datetime import date, timedelta
from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile, status
from sqlalchemy.orm import Session, joinedload

from backend import avatars, models, schemas, storage
from backend.core.security import _ip_and_user_key, get_current_user, limiter, require_coach
from backend.database import get_db
from backend.routers.exercise_helpers import get_or_create_exercise
from backend.routers.pr_helpers import get_athlete_prs, resolve_weight_from_percentage

router = APIRouter(prefix="/plans", tags=["plans"])

# Un plan es un Mesocycle con is_template=True y user_id=None. Sus sesiones guardan el "día N"
# relativo (day_offset) más una fecha sintética (PLAN_EPOCH + day_offset) para no romper el
# ordenamiento ni las vistas que asumen que scheduled_date existe. Al adquirirlo, se clona a un
# mesociclo normal con las fechas reales del atleta y las cargas resueltas desde sus propias marcas.
PLAN_EPOCH = date(2000, 1, 1)


def _get_owned_plan(db: Session, plan_id: UUID, current_user: models.User) -> models.Mesocycle:
    plan = db.query(models.Mesocycle).filter(
        models.Mesocycle.id == plan_id, models.Mesocycle.is_template == True
    ).first()
    if not plan:
        raise HTTPException(status_code=404, detail="Plan no encontrado")
    if current_user.role != "admin" and plan.created_by_coach_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Este plan no te pertenece")
    return plan


def _plan_summary(db: Session, plan: models.Mesocycle) -> schemas.PlanSummaryResponse:
    sesiones = db.query(models.Session).filter(models.Session.mesocycle_id == plan.id).all()
    dias_distintos = {s.day_offset for s in sesiones if s.day_offset is not None}
    semanas = max(1, ((max(dias_distintos) // 7) + 1) if dias_distintos else 1)
    return schemas.PlanSummaryResponse(
        id=plan.id,
        name=plan.name,
        description=plan.description,
        discipline=plan.discipline,
        level=plan.level,
        price=plan.price,
        weeks_count=semanas,
        sessions_count=len(sesiones),
        sessions_per_week=round(len(sesiones) / semanas) if semanas else len(sesiones),
        coach_name=plan.created_by_coach.full_name if plan.created_by_coach else None,
        is_published=plan.is_published,
        has_cover_image=plan.has_cover_image,
        created_at=plan.created_at,
    )


@router.post("/", response_model=schemas.PlanSummaryResponse)
def create_plan(
    req: schemas.PlanCreate, db: Session = Depends(get_db), current_user: models.User = Depends(require_coach)
):
    """Crea el esqueleto de un plan: la plantilla y sus días vacíos, listos para que el coach
    les agregue ejercicios. No pertenece a ningún atleta y nace despublicado (borrador)."""
    plan = models.Mesocycle(
        user_id=None,
        is_template=True,
        is_published=False,
        created_by_coach_id=current_user.id,
        name=req.name,
        description=req.description,
        discipline=req.discipline,
        level=req.level,
        price=req.price,
        start_date=PLAN_EPOCH,
    )
    db.add(plan)
    db.flush()

    # Los offsets se normalizan para que el PRIMER día de entrenamiento sea el día 0. Así, al
    # adquirir el plan, la primera sesión cae exactamente en la fecha que eligió el atleta y el
    # patrón semanal del coach (ej. lun/mié/vie -> +0/+2/+4) se conserva tal cual, sin importar
    # en qué día de la semana empiece cada comprador.
    offsets_crudos = [
        i for i in range(req.weeks_count * 7)
        if (PLAN_EPOCH + timedelta(days=i)).weekday() in req.training_days
    ]
    base = offsets_crudos[0] if offsets_crudos else 0
    offsets = [i - base for i in offsets_crudos]

    for offset in offsets:
        db.add(models.Session(
            mesocycle_id=plan.id,
            day_offset=offset,
            scheduled_date=PLAN_EPOCH + timedelta(days=offset),
            athlete_notes="",
            status="pending",
        ))

    plan.end_date = PLAN_EPOCH + timedelta(days=max(offsets) if offsets else 0)
    db.commit()
    db.refresh(plan)
    return _plan_summary(db, plan)


@router.post("/{plan_id}/cover", response_model=schemas.PlanSummaryResponse)
@limiter.limit("10/hour", key_func=_ip_and_user_key)
async def upload_plan_cover(
    request: Request,
    plan_id: UUID,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_coach),
):
    """Sube (o reemplaza) la foto de portada del plan — mismo pipeline de saneo que el avatar
    de usuario (magic-number, re-render sin metadatos, nombre aleatorio)."""
    plan = _get_owned_plan(db, plan_id, current_user)
    raw = await avatars.read_and_validate_upload(file)
    clean_bytes, extension = avatars.rerender_and_strip_metadata(raw)

    nombre_anterior = plan.cover_image_filename
    nuevo_nombre = storage.upload_object(
        storage.PLAN_COVER_BUCKET, clean_bytes, extension, avatars.AVATAR_CONTENT_TYPES[extension]
    )
    plan.cover_image_filename = nuevo_nombre
    db.commit()
    db.refresh(plan)
    storage.delete_object(storage.PLAN_COVER_BUCKET, nombre_anterior)
    return _plan_summary(db, plan)


@router.delete("/{plan_id}/cover", response_model=schemas.MessageResponse)
def delete_plan_cover(
    plan_id: UUID, db: Session = Depends(get_db), current_user: models.User = Depends(require_coach)
):
    plan = _get_owned_plan(db, plan_id, current_user)
    if not plan.cover_image_filename:
        raise HTTPException(status_code=404, detail="Este plan no tiene foto de portada.")
    storage.delete_object(storage.PLAN_COVER_BUCKET, plan.cover_image_filename)
    plan.cover_image_filename = None
    db.commit()
    return {"message": "Foto de portada eliminada."}


@router.get("/{plan_id}/cover")
def get_plan_cover(
    plan_id: UUID, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)
):
    """Mismo criterio de visibilidad que GET /plans/{id}: el autor/admin ve la portada de
    borradores, cualquiera autenticado ve la de planes ya publicados."""
    plan = db.query(models.Mesocycle).filter(
        models.Mesocycle.id == plan_id, models.Mesocycle.is_template == True
    ).first()
    if not plan:
        raise HTTPException(status_code=404, detail="Plan no encontrado")
    es_autor = plan.created_by_coach_id == current_user.id or current_user.role == "admin"
    if not plan.is_published and not es_autor:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Este plan todavía no está publicado")
    return storage.redirect_to_image(storage.PLAN_COVER_BUCKET, plan.cover_image_filename)


@router.get("/mine", response_model=List[schemas.PlanSummaryResponse])
def list_my_plans(db: Session = Depends(get_db), current_user: models.User = Depends(require_coach)):
    """Planes creados por este coach (publicados y borradores). El admin ve todos."""
    query = db.query(models.Mesocycle).options(
        joinedload(models.Mesocycle.created_by_coach)
    ).filter(models.Mesocycle.is_template == True)
    if current_user.role != "admin":
        query = query.filter(models.Mesocycle.created_by_coach_id == current_user.id)
    return [_plan_summary(db, p) for p in query.order_by(models.Mesocycle.created_at.desc()).all()]


@router.get("/catalog", response_model=List[schemas.PlanSummaryResponse])
def list_plan_catalog(db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    """Catálogo público (para cualquier usuario autenticado): solo planes publicados."""
    planes = (
        db.query(models.Mesocycle)
        .options(joinedload(models.Mesocycle.created_by_coach))
        .filter(models.Mesocycle.is_template == True, models.Mesocycle.is_published == True)
        .order_by(models.Mesocycle.created_at.desc())
        .all()
    )
    return [_plan_summary(db, p) for p in planes]


@router.get("/{plan_id}")
def get_plan_detail(
    plan_id: UUID, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)
):
    """El autor/admin ve el contenido COMPLETO (lo necesita para editarlo). Cualquier otro
    usuario autenticado — típicamente un atleta viendo el catálogo antes de comprarlo — recibe
    una VISTA PREVIA (schemas.PlanPreviewResponse): se ven los bloques y cuántos ejercicios trae
    cada día, pero no los ejercicios/series/pesos exactos. Mostrar la programación completa
    antes de pagar no tendría sentido comercial."""
    plan = db.query(models.Mesocycle).options(
        joinedload(models.Mesocycle.sessions).joinedload(models.Session.sets).joinedload(models.Set.exercise)
    ).filter(models.Mesocycle.id == plan_id, models.Mesocycle.is_template == True).first()
    if not plan:
        raise HTTPException(status_code=404, detail="Plan no encontrado")

    es_autor = plan.created_by_coach_id == current_user.id or current_user.role == "admin"
    if not plan.is_published and not es_autor:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Este plan todavía no está publicado")

    plan.sessions.sort(key=lambda s: (s.day_offset if s.day_offset is not None else 0))
    for sesion in plan.sessions:
        sesion.sets.sort(key=lambda x: x.set_order)

    if es_autor:
        return schemas.MesocycleFullResponse.model_validate(plan)

    sesiones_preview = []
    for sesion in plan.sessions:
        bloques_del_dia: list[str] = []
        ejercicios_del_dia: set = set()
        for s in sesion.sets:
            if s.block and s.block not in bloques_del_dia:
                bloques_del_dia.append(s.block)
            if s.exercise_id:
                ejercicios_del_dia.add(s.exercise_id)
        sesiones_preview.append(schemas.PlanSessionPreview(
            id=sesion.id,
            day_offset=sesion.day_offset,
            blocks=bloques_del_dia,
            exercise_count=len(ejercicios_del_dia),
        ))

    return schemas.PlanPreviewResponse(
        id=plan.id,
        name=plan.name,
        discipline=plan.discipline,
        start_date=plan.start_date,
        end_date=plan.end_date,
        description=plan.description,
        level=plan.level,
        has_cover_image=plan.has_cover_image,
        sessions=sesiones_preview,
    )


@router.put("/{plan_id}", response_model=schemas.PlanSummaryResponse)
def update_plan(
    plan_id: UUID,
    req: schemas.PlanUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_coach),
):
    """Edita nombre/descripción/disciplina/nivel/precio de un plan — funciona igual esté
    publicado o en borrador (cambiar el precio de un plan ya publicado es normal)."""
    plan = _get_owned_plan(db, plan_id, current_user)
    plan.name = req.name
    plan.description = req.description
    plan.discipline = req.discipline
    plan.level = req.level
    plan.price = req.price
    db.commit()
    db.refresh(plan)
    return _plan_summary(db, plan)


@router.put("/{plan_id}/publish", response_model=schemas.PlanSummaryResponse)
def publish_plan(
    plan_id: UUID,
    req: schemas.PlanPublishUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_coach),
):
    plan = _get_owned_plan(db, plan_id, current_user)
    if req.is_published:
        tiene_ejercicios = (
            db.query(models.Set)
            .join(models.Session, models.Set.session_id == models.Session.id)
            .filter(models.Session.mesocycle_id == plan.id)
            .count()
        )
        if not tiene_ejercicios:
            raise HTTPException(
                status_code=400,
                detail="No puedes publicar un plan sin ejercicios. Agrégalos primero.",
            )
    plan.is_published = req.is_published
    db.commit()
    db.refresh(plan)
    return _plan_summary(db, plan)


@router.delete("/{plan_id}")
def delete_plan(plan_id: UUID, db: Session = Depends(get_db), current_user: models.User = Depends(require_coach)):
    plan = _get_owned_plan(db, plan_id, current_user)
    db.delete(plan)
    db.commit()
    return {"message": "Plan eliminado correctamente"}


@router.post("/{plan_id}/sessions/{session_id}/sets")
def add_set_to_plan_session(
    plan_id: UUID,
    session_id: UUID,
    req: schemas.PlanSetCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_coach),
):
    """Agrega un ejercicio a un día del plan. La carga puede ir en kg fijos o en % de 1RM
    (el % se resuelve a kg cuando un atleta adquiere el plan, usando SUS marcas)."""
    plan = _get_owned_plan(db, plan_id, current_user)

    sesion = db.query(models.Session).filter(
        models.Session.id == session_id, models.Session.mesocycle_id == plan.id
    ).first()
    if not sesion:
        raise HTTPException(status_code=404, detail="Ese día no pertenece a este plan")

    ejercicio = get_or_create_exercise(db, req.exercise_name)
    series_actuales = db.query(models.Set).filter(models.Set.session_id == sesion.id).count()

    for i in range(req.prescribed_sets):
        db.add(models.Set(
            session_id=sesion.id,
            exercise_id=ejercicio.id,
            set_order=series_actuales + i + 1,
            prescribed_reps=req.prescribed_reps,
            rpe=req.rpe,
            prescribed_weight=req.prescribed_weight,
            prescribed_percentage=req.prescribed_percentage,
            reference_exercise=req.reference_exercise,
            block=req.block,
        ))

    db.commit()
    return {"message": f"'{req.exercise_name}' agregado al plan ({req.prescribed_sets} series)"}


@router.delete("/{plan_id}/sets/{set_id}")
def delete_set_from_plan(
    plan_id: UUID,
    set_id: UUID,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_coach),
):
    plan = _get_owned_plan(db, plan_id, current_user)
    db_set = (
        db.query(models.Set)
        .join(models.Session, models.Set.session_id == models.Session.id)
        .filter(models.Set.id == set_id, models.Session.mesocycle_id == plan.id)
        .first()
    )
    if not db_set:
        raise HTTPException(status_code=404, detail="Serie no encontrada en este plan")
    db.delete(db_set)
    db.commit()
    return {"message": "Serie eliminada del plan"}


@router.post("/{plan_id}/acquire")
def acquire_plan(
    plan_id: UUID,
    req: schemas.PlanAcquireRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """El atleta adquiere un plan publicado: se clona a un mesociclo propio con las fechas
    reales a partir de `start_date` y las cargas en % resueltas con SUS marcas de 1RM."""
    plan = db.query(models.Mesocycle).options(
        joinedload(models.Mesocycle.sessions).joinedload(models.Session.sets).joinedload(models.Set.exercise)
    ).filter(models.Mesocycle.id == plan_id, models.Mesocycle.is_template == True).first()
    if not plan:
        raise HTTPException(status_code=404, detail="Plan no encontrado")
    if not plan.is_published:
        raise HTTPException(status_code=400, detail="Este plan todavía no está disponible")

    prs = get_athlete_prs(db, current_user.id)

    nuevo_meso = models.Mesocycle(
        user_id=current_user.id,
        is_template=False,
        source_plan_id=plan.id,
        name=plan.name,
        discipline=plan.discipline,
        start_date=req.start_date,
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
            scheduled_date=req.start_date + timedelta(days=offset),
            athlete_notes=sesion_plan.athlete_notes,
            status="pending",
            duration_minutes=sesion_plan.duration_minutes,
        )
        db.add(nueva_sesion)
        db.flush()

        for set_plan in sorted(sesion_plan.sets, key=lambda x: x.set_order):
            referencia = set_plan.reference_exercise or (set_plan.exercise.name if set_plan.exercise else "")
            peso = resolve_weight_from_percentage(set_plan.prescribed_percentage, set_plan.prescribed_weight, referencia, prs)
            if set_plan.prescribed_percentage and peso is None and referencia:
                sin_marca.add(referencia)

            db.add(models.Set(
                session_id=nueva_sesion.id,
                exercise_id=set_plan.exercise_id,
                set_order=set_plan.set_order,
                block=set_plan.block,
                prescribed_reps=set_plan.prescribed_reps,
                rpe=set_plan.rpe,
                prescribed_weight=peso,
                prescribed_percentage=set_plan.prescribed_percentage,
                reference_exercise=set_plan.reference_exercise,
            ))

    nuevo_meso.end_date = req.start_date + timedelta(days=max_offset)
    db.commit()

    mensaje = f"¡Plan '{plan.name}' adquirido! Ya está en tus entrenamientos a partir del {req.start_date}."
    if sin_marca:
        mensaje += (
            " Ojo: no tienes marcas registradas de "
            + ", ".join(sorted(sin_marca))
            + ", así que esas cargas quedaron sin kg (registra tus 1RM y ajústalas)."
        )
    return {"message": mensaje, "mesocycle_id": str(nuevo_meso.id), "missing_prs": sorted(sin_marca)}
