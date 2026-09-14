from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload

from backend import models, schemas
from backend.core.security import ensure_owner_or_coach, get_current_user, require_coach
from backend.database import get_db
from backend.routers.shared import get_athlete_prs, resolve_weight_from_percentage

router = APIRouter(tags=["sets"])


@router.put("/sets/{set_id}", response_model=schemas.SetResponse)
def update_set(
    set_id: UUID,
    set_update: schemas.SetUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_coach),
):
    db_set = (
        db.query(models.Set)
        .options(joinedload(models.Set.session).joinedload(models.Session.mesocycle))
        .filter(models.Set.id == set_id)
        .first()
    )
    if not db_set:
        raise HTTPException(status_code=404, detail="Serie (Set) no encontrada")
    ensure_owner_or_coach(db, db_set.session.mesocycle.user_id, current_user)

    # Nombre de referencia para resolver el % de 1RM: el que se está escribiendo ahora, o si no
    # cambia, el que ya tenía el ejercicio (se calcula ANTES de tocar exercise_id).
    nombre_para_referencia = set_update.exercise_name or (db_set.exercise.name if db_set.exercise else "")

    db_set.prescribed_reps = set_update.prescribed_reps
    db_set.rpe = set_update.rpe
    db_set.prescribed_percentage = set_update.prescribed_percentage
    db_set.reference_exercise = set_update.reference_exercise
    if set_update.prescribed_percentage is not None:
        prs = get_athlete_prs(db, db_set.session.mesocycle.user_id)
        referencia = set_update.reference_exercise or nombre_para_referencia
        db_set.prescribed_weight = resolve_weight_from_percentage(
            set_update.prescribed_percentage, set_update.prescribed_weight, referencia, prs
        )
    else:
        db_set.prescribed_weight = set_update.prescribed_weight
    if set_update.block is not None:
        db_set.block = set_update.block

    if set_update.exercise_name:
        ejercicio = db.query(models.Exercise).filter(models.Exercise.name == set_update.exercise_name).first()
        if not ejercicio:
            ejercicio = models.Exercise(name=set_update.exercise_name, category="General")
            db.add(ejercicio)
            db.flush()
        db_set.exercise_id = ejercicio.id

    db.commit()
    db.refresh(db_set)
    return db_set


@router.post("/sessions/{session_id}/sets/")
def agregar_serie(
    session_id: UUID,
    req: schemas.SetCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_coach),
):
    sesion = (
        db.query(models.Session)
        .options(joinedload(models.Session.mesocycle))
        .filter(models.Session.id == session_id)
        .first()
    )
    if not sesion:
        raise HTTPException(status_code=404, detail="Sesión no encontrada")
    ensure_owner_or_coach(db, sesion.mesocycle.user_id, current_user)

    ejercicio = db.query(models.Exercise).filter(models.Exercise.name == req.exercise_name).first()
    if not ejercicio:
        ejercicio = models.Exercise(name=req.exercise_name, category="Custom")
        db.add(ejercicio)
        db.flush()

    series_actuales = db.query(models.Set).filter(models.Set.session_id == session_id).all()
    siguiente_orden = len(series_actuales) + 1

    if req.prescribed_percentage is not None:
        prs = get_athlete_prs(db, sesion.mesocycle.user_id)
        referencia = req.reference_exercise or req.exercise_name
        peso = resolve_weight_from_percentage(req.prescribed_percentage, req.prescribed_weight, referencia, prs)
    else:
        peso = req.prescribed_weight

    nuevo_set = models.Set(
        session_id=session_id,
        exercise_id=ejercicio.id,
        set_order=siguiente_orden,
        prescribed_reps=req.prescribed_reps,
        rpe=req.rpe,
        prescribed_weight=peso,
        prescribed_percentage=req.prescribed_percentage,
        reference_exercise=req.reference_exercise,
        block=req.block,
    )
    db.add(nuevo_set)
    db.commit()
    return {"message": "Nueva serie agregada al final de la sesión"}


@router.delete("/sets/{set_id}")
def delete_set(set_id: UUID, db: Session = Depends(get_db), current_user: models.User = Depends(require_coach)):
    db_set = (
        db.query(models.Set)
        .options(joinedload(models.Set.session).joinedload(models.Session.mesocycle))
        .filter(models.Set.id == set_id)
        .first()
    )
    if not db_set:
        raise HTTPException(status_code=404, detail="Serie no encontrada")
    ensure_owner_or_coach(db, db_set.session.mesocycle.user_id, current_user)

    db.delete(db_set)
    db.commit()
    return {"message": "Serie eliminada correctamente"}


@router.put("/sets/{set_id}/log", response_model=schemas.SetResponse)
def log_set_performance(
    set_id: UUID,
    log: schemas.SetLogUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """El ATLETA (dueño) o su coach registran lo que realmente se hizo en una serie
    (reps/peso reales, feedback de técnica) — a diferencia de PUT /sets/{id}, que edita
    lo PRESCRITO y es solo para coaches."""
    db_set = (
        db.query(models.Set)
        .options(joinedload(models.Set.session).joinedload(models.Session.mesocycle))
        .filter(models.Set.id == set_id)
        .first()
    )
    if not db_set:
        raise HTTPException(status_code=404, detail="Serie no encontrada")

    ensure_owner_or_coach(db, db_set.session.mesocycle.user_id, current_user)

    db_set.actual_reps = log.actual_reps
    db_set.actual_weight = log.actual_weight
    if log.technique_feedback is not None:
        db_set.technique_feedback = log.technique_feedback

    db.commit()
    db.refresh(db_set)
    return db_set
