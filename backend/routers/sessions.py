from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session, joinedload

from backend import ai_agent, models, schemas
from backend.core.security import ensure_owner_or_coach, get_current_user, limiter, require_coach
from backend.database import get_db
from backend.routers.exercise_helpers import clean_ai_block, get_or_create_exercise

router = APIRouter(prefix="/sessions", tags=["sessions"])


@router.post("/", response_model=schemas.SessionResponse)
def create_session(
    session: schemas.SessionCreate, db: Session = Depends(get_db), current_user: models.User = Depends(require_coach)
):
    db_meso = db.query(models.Mesocycle).filter(models.Mesocycle.id == session.mesocycle_id).first()
    if not db_meso:
        raise HTTPException(status_code=404, detail="Mesociclo no encontrado")
    ensure_owner_or_coach(db, db_meso.user_id, current_user)

    new_session = models.Session(
        mesocycle_id=session.mesocycle_id,
        scheduled_date=session.scheduled_date,
    )
    db.add(new_session)
    db.commit()
    db.refresh(new_session)
    return new_session


@router.put("/{session_id}/wod-format", response_model=schemas.MessageResponse)
def set_session_wod_format(
    session_id: UUID,
    req: schemas.WodFormatUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_coach),
):
    """El coach marca (o quita) qué formato de WOD tiene esta sesión — así el atleta sabe qué
    reportar al completarla (tiempo, rondas+reps, o si cumplió el EMOM)."""
    sesion = (
        db.query(models.Session)
        .options(joinedload(models.Session.mesocycle))
        .filter(models.Session.id == session_id)
        .first()
    )
    if not sesion:
        raise HTTPException(status_code=404, detail="Sesión no encontrada")
    ensure_owner_or_coach(db, sesion.mesocycle.user_id, current_user)

    sesion.wod_format = req.wod_format
    sesion.wod_time_cap_seconds = req.time_cap_seconds if req.wod_format else None
    db.commit()
    return {"message": "Formato de WOD actualizado" if req.wod_format else "Formato de WOD quitado"}


@router.put("/{session_id}/meta", response_model=schemas.SessionResponse)
def update_session_meta(
    session_id: UUID,
    req: schemas.SessionMetaUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_coach),
):
    """El coach ajusta el orden de los bloques y/o las pautas de calentamiento de esta sesión —
    aparte de sus series, que se editan por su cuenta (ver routers/sets.py)."""
    sesion = (
        db.query(models.Session)
        .options(joinedload(models.Session.mesocycle), joinedload(models.Session.sets).joinedload(models.Set.exercise))
        .filter(models.Session.id == session_id)
        .first()
    )
    if not sesion:
        raise HTTPException(status_code=404, detail="Sesión no encontrada")
    ensure_owner_or_coach(db, sesion.mesocycle.user_id, current_user)

    if req.block_order is not None:
        sesion.block_order = req.block_order or None
    if req.warmup_notes is not None:
        sesion.warmup_notes = req.warmup_notes or None
    db.commit()
    db.refresh(sesion)
    return sesion


@router.post("/{session_id}/complete")
def complete_session(
    session_id: UUID,
    req: schemas.SessionCompleteRequest | None = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """El ATLETA (dueño) o su coach marcan una sesión como completada. Si la sesión tenía un
    formato de WOD prescrito (wod_format), `req` trae el resultado real que reportó el atleta
    (tiempo, rondas+reps, o si cumplió el EMOM) — queda guardado junto con la sesión."""
    sesion = (
        db.query(models.Session)
        .options(joinedload(models.Session.mesocycle))
        .filter(models.Session.id == session_id)
        .first()
    )
    if not sesion:
        raise HTTPException(status_code=404, detail="Sesión no encontrada")

    ensure_owner_or_coach(db, sesion.mesocycle.user_id, current_user)

    sesion.status = "completed"
    sesion.completed_date = datetime.utcnow()
    if req is not None:
        if req.wod_time_seconds is not None:
            sesion.wod_time_seconds = req.wod_time_seconds
        if req.wod_rounds is not None:
            sesion.wod_rounds = req.wod_rounds
        if req.wod_extra_reps is not None:
            sesion.wod_extra_reps = req.wod_extra_reps
        if req.wod_emom_completed is not None:
            sesion.wod_emom_completed = req.wod_emom_completed
        if req.wod_calories is not None:
            sesion.wod_calories = req.wod_calories
        if req.wod_distance_meters is not None:
            sesion.wod_distance_meters = req.wod_distance_meters
        if req.wod_watts is not None:
            sesion.wod_watts = req.wod_watts
    db.commit()
    return {"message": "Sesión marcada como completada"}


@router.post("/{session_id}/uncomplete")
def uncomplete_session(
    session_id: UUID,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Deshace un "Terminar entrenamiento" hecho sin querer -- vuelve la sesión a "pendiente" y
    borra el resultado del WOD que se hubiera reportado (no solo el estado), para que si se
    vuelve a completar no quede un resultado viejo mezclado con uno nuevo. NO toca las series
    individuales (actual_reps/actual_weight de cada Set): eso se deshace por separado, serie por
    serie, con PUT /sets/{id}/log mandando null."""
    sesion = (
        db.query(models.Session)
        .options(joinedload(models.Session.mesocycle))
        .filter(models.Session.id == session_id)
        .first()
    )
    if not sesion:
        raise HTTPException(status_code=404, detail="Sesión no encontrada")

    ensure_owner_or_coach(db, sesion.mesocycle.user_id, current_user)

    sesion.status = "pending"
    sesion.completed_date = None
    sesion.wod_time_seconds = None
    sesion.wod_rounds = None
    sesion.wod_extra_reps = None
    sesion.wod_emom_completed = None
    sesion.wod_calories = None
    sesion.wod_distance_meters = None
    sesion.wod_watts = None
    db.commit()
    return {"message": "Se deshizo la sesión completada"}


@router.post("/{session_id}/adapt", response_model=schemas.SessionResponse)
@limiter.limit("10/hour")
def adapt_session_to_available_time(
    request: Request,
    session_id: UUID,
    req: schemas.SessionAdaptRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """El ATLETA (dueño) o su coach piden una versión adaptada de una sesión ya prescrita para
    caber en `available_minutes` (p. ej. "hoy solo tengo 60 min"). La sesión ORIGINAL nunca se
    toca: esto crea (o actualiza, si ya se había pedido antes) una segunda sesión "hija" para
    el mismo día, que el atleta puede ver junto a la original y elegir cuál seguir."""
    original = (
        db.query(models.Session)
        .options(
            joinedload(models.Session.mesocycle).joinedload(models.Mesocycle.user),
            joinedload(models.Session.sets).joinedload(models.Set.exercise),
        )
        .filter(models.Session.id == session_id)
        .first()
    )
    if not original:
        raise HTTPException(status_code=404, detail="Sesión no encontrada")

    ensure_owner_or_coach(db, original.mesocycle.user_id, current_user)

    if original.parent_session_id is not None:
        raise HTTPException(
            status_code=400,
            detail="Esta ya es una versión adaptada; pide la adaptación desde la sesión original.",
        )

    if not original.sets:
        raise HTTPException(status_code=400, detail="Esta sesión todavía no tiene ejercicios para adaptar.")

    atleta = original.mesocycle.user
    marcas = db.query(models.PersonalRecord).filter(models.PersonalRecord.user_id == atleta.id).all()
    texto_marcas = ", ".join(f"{pr.exercise_name}: {pr.max_weight_kg}kg" for pr in marcas) or "Sin marcas registradas."
    peso_corporal = f"{atleta.body_weight}kg" if atleta.body_weight else "No registrado"
    contexto = f"Peso corporal: {peso_corporal}. Marcas (1RM): {texto_marcas}."

    ejercicios_originales = [
        {
            "exercise_name": s.exercise.name,
            "prescribed_sets": 1,  # cada fila ya es una serie individual
            "prescribed_reps": s.prescribed_reps,
            "rpe": s.rpe,
            "prescribed_weight": s.prescribed_weight,
            "block": s.block,
        }
        for s in original.sets
    ]

    rutina_ai = ai_agent.adapt_session_to_time(
        athlete_name=atleta.full_name,
        discipline=original.mesocycle.discipline,
        experience_notes=contexto,
        original_exercises=ejercicios_originales,
        available_minutes=req.available_minutes,
    )
    if "error" in rutina_ai:
        raise HTTPException(status_code=500, detail=f"Error generando la sesión adaptada: {rutina_ai['error']}")

    # ¿Ya existía una versión adaptada de esta sesión? La reemplazamos en vez de duplicar.
    adaptada = db.query(models.Session).filter(models.Session.parent_session_id == original.id).first()
    if adaptada:
        db.query(models.Set).filter(models.Set.session_id == adaptada.id).delete()
    else:
        adaptada = models.Session(
            mesocycle_id=original.mesocycle_id,
            scheduled_date=original.scheduled_date,
            parent_session_id=original.id,
            status="pending",
        )
        db.add(adaptada)
        db.flush()

    adaptada.duration_minutes = req.available_minutes
    adaptada.athlete_notes = rutina_ai.get(
        "athlete_notes", f"Versión adaptada a {req.available_minutes} minutos."
    )

    orden = 1
    for ej_data in rutina_ai.get("exercises", []):
        ejercicio = get_or_create_exercise(db, ej_data.get("exercise_name", "Ejercicio Desconocido"))
        db.add(models.Set(
            session_id=adaptada.id,
            exercise_id=ejercicio.id,
            set_order=orden,
            prescribed_reps=ej_data.get("prescribed_reps", 1),
            rpe=ej_data.get("rpe_target"),
            prescribed_weight=ej_data.get("prescribed_weight"),
            block=clean_ai_block(ej_data.get("block")),
        ))
        orden += 1

    db.commit()
    db.refresh(adaptada)
    return adaptada
