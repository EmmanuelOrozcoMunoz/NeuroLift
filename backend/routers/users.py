from datetime import date, timedelta
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile
from sqlalchemy import case, func
from sqlalchemy.orm import Session, joinedload
from typing import List

from backend import avatars, models, schemas, storage
from backend.core.logging import security_logger
from backend.core.security import (
    _client_ip,
    _coach_athlete_ids,
    _ip_and_user_key,
    ensure_owner_or_coach,
    get_current_user,
    limiter,
    require_admin,
    require_coach,
)
from backend.database import get_db
from backend.routers.shared import AVATAR_CONTENT_TYPES, PR_NAME_TO_FIT_LEVEL_LIFT
from backend.wod_scoring import format_wod_summary

# Mezcla rutas /users/* y /coach/* (el leaderboard general es "del coach", no "de un usuario"),
# así que este router no fija un prefix común — cada ruta lleva su path completo.
router = APIRouter(tags=["users"])


@router.get("/users/", response_model=List[schemas.UserResponse])
def get_users(db: Session = Depends(get_db), current_user: models.User = Depends(require_admin)):
    """Listado global de usuarios (todos los roles): solo un admin lo necesita — un coach ya
    tiene su propio listado acotado en GET /users/athletes."""
    return db.query(models.User).all()


@router.get("/users/athletes", response_model=List[schemas.UserResponse])
def get_athletes(db: Session = Depends(get_db), current_user: models.User = Depends(require_coach)):
    """Los atletas del coach autenticado (los que él registró + los de sus grupos) para su menú
    desplegable. Un admin sigue viendo a todos."""
    if current_user.role == "admin":
        return db.query(models.User).filter(models.User.role == "athlete").all()
    ids = _coach_athlete_ids(db, current_user.id)
    if not ids:
        return []
    return db.query(models.User).filter(models.User.id.in_(ids)).all()


@router.get("/coach/leaderboard", response_model=List[schemas.AthleteActivityResponse])
def get_athlete_leaderboard(db: Session = Depends(get_db), current_user: models.User = Depends(require_coach)):
    """Tabla de posiciones: cuántos entrenamientos completó cada uno de TUS atletas (los que el
    propio atleta marcó como hechos, con sus reps/pesos reales) — antes el coach no tenía forma
    de ver esto sin entrar mesociclo por mesociclo. Ordenado por actividad de esta semana."""
    if current_user.role == "admin":
        ids = {u.id for u in db.query(models.User.id).filter(models.User.role == "athlete").all()}
    else:
        ids = _coach_athlete_ids(db, current_user.id)
    if not ids:
        return []

    atletas = db.query(models.User).filter(models.User.id.in_(ids)).all()

    hoy = date.today()
    inicio_semana = hoy - timedelta(days=hoy.weekday())  # lunes de esta semana

    filas = (
        db.query(
            models.Mesocycle.user_id.label("user_id"),
            func.count(models.Session.id).label("total"),
            func.sum(case((models.Session.completed_date >= inicio_semana, 1), else_=0)).label("esta_semana"),
            func.max(models.Session.completed_date).label("ultima"),
        )
        .join(models.Session, models.Session.mesocycle_id == models.Mesocycle.id)
        .filter(models.Mesocycle.user_id.in_(ids), models.Session.status == "completed")
        .group_by(models.Mesocycle.user_id)
        .all()
    )
    stats_por_atleta = {f.user_id: f for f in filas}

    # Último WOD con resultado registrado, uno por atleta (el más reciente primero en la
    # consulta, así que el primero que aparece por atleta ya es el que queremos).
    sesiones_wod = (
        db.query(models.Session)
        .join(models.Mesocycle, models.Session.mesocycle_id == models.Mesocycle.id)
        .options(joinedload(models.Session.mesocycle), joinedload(models.Session.sets))
        .filter(
            models.Mesocycle.user_id.in_(ids),
            models.Session.status == "completed",
            models.Session.wod_format.isnot(None),
        )
        .order_by(models.Session.completed_date.desc())
        .all()
    )
    ultimo_wod_por_atleta: dict = {}
    for s in sesiones_wod:
        ultimo_wod_por_atleta.setdefault(s.mesocycle.user_id, s)

    resultados = [
        schemas.AthleteActivityResponse(
            user_id=atleta.id,
            full_name=atleta.full_name,
            has_avatar=atleta.has_avatar,
            completed_total=(stats_por_atleta[atleta.id].total if atleta.id in stats_por_atleta else 0),
            completed_this_week=(
                int(stats_por_atleta[atleta.id].esta_semana) if atleta.id in stats_por_atleta else 0
            ),
            last_completed_at=(stats_por_atleta[atleta.id].ultima if atleta.id in stats_por_atleta else None),
            last_wod_summary=format_wod_summary(ultimo_wod_por_atleta.get(atleta.id)),
        )
        for atleta in atletas
    ]
    resultados.sort(key=lambda r: (r.completed_this_week, r.completed_total), reverse=True)
    return resultados


@router.get("/users/{user_id}/recent-activity", response_model=List[schemas.RecentSessionSummary])
def get_recent_activity(
    user_id: UUID, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)
):
    """Últimas 10 sesiones COMPLETADAS de este atleta, con lo que REALMENTE hizo (reps/pesos
    reales por ejercicio, resultado del WOD si tenía uno prescrito) — antes el coach no tenía
    forma de ver esto sin entrar mesociclo por mesociclo."""
    ensure_owner_or_coach(db, user_id, current_user)

    sesiones = (
        db.query(models.Session)
        .join(models.Mesocycle, models.Session.mesocycle_id == models.Mesocycle.id)
        .options(
            joinedload(models.Session.mesocycle),
            joinedload(models.Session.sets).joinedload(models.Set.exercise),
        )
        .filter(models.Mesocycle.user_id == user_id, models.Session.status == "completed")
        .order_by(models.Session.completed_date.desc())
        .limit(10)
        .all()
    )

    resultados = []
    for sesion in sesiones:
        # Agrupa series CONSECUTIVAS del mismo ejercicio+bloque (igual que groupSets en el
        # frontend) — así "Back Squat" con 4 series seguidas se lee como un solo renglón.
        ejercicios: list[schemas.RecentSessionExercise] = []
        for s in sorted(sesion.sets, key=lambda x: x.set_order):
            nombre = s.exercise.name if s.exercise else "Ejercicio"
            anterior = ejercicios[-1] if ejercicios else None
            if anterior and anterior.exercise_name == nombre and anterior.block == s.block:
                fila = anterior
            else:
                fila = schemas.RecentSessionExercise(exercise_name=nombre, block=s.block)
                ejercicios.append(fila)
            if s.actual_reps is not None:
                fila.actual_reps.append(s.actual_reps)
                fila.sets_logged += 1
            if s.actual_weight is not None:
                fila.actual_weight.append(s.actual_weight)

        resultados.append(schemas.RecentSessionSummary(
            session_id=sesion.id,
            scheduled_date=sesion.scheduled_date,
            completed_date=sesion.completed_date,
            mesocycle_name=sesion.mesocycle.name,
            discipline=sesion.mesocycle.discipline,
            wod_format=sesion.wod_format,
            wod_time_cap_seconds=sesion.wod_time_cap_seconds,
            wod_time_seconds=sesion.wod_time_seconds,
            wod_rounds=sesion.wod_rounds,
            wod_extra_reps=sesion.wod_extra_reps,
            wod_emom_completed=sesion.wod_emom_completed,
            wod_calories=sesion.wod_calories,
            wod_distance_meters=sesion.wod_distance_meters,
            wod_watts=sesion.wod_watts,
            exercises=ejercicios,
        ))
    return resultados


@router.get("/users/search", response_model=schemas.UserResponse)
@limiter.limit("30/hour", key_func=_ip_and_user_key)
def search_athlete_by_email(
    request: Request, email: str, db: Session = Depends(get_db), current_user: models.User = Depends(require_coach)
):
    """Busca UN atleta por correo EXACTO (case-insensitive) — para que un coach pueda encontrar
    a un atleta que se auto-registró por su cuenta y agregarlo a un grupo, sin exponerle el
    listado completo de usuarios de la plataforma (eso rompería el aislamiento por coach).
    Limitado por hora para que no se use como herramienta de enumeración masiva de correos."""
    usuario = db.query(models.User).filter(
        models.User.role == "athlete", models.User.email.ilike(email.strip())
    ).first()
    if not usuario:
        raise HTTPException(status_code=404, detail="No hay ningún atleta registrado con ese correo.")
    return usuario


@router.post("/users/me/avatar", response_model=schemas.UserResponse)
@limiter.limit("10/hour", key_func=_ip_and_user_key)
async def upload_my_avatar(
    request: Request,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Sube (o reemplaza) la foto de perfil del usuario autenticado. Solo uno mismo puede
    subir su propia foto — no hay ruta equivalente para que un coach suba la de un atleta."""
    raw = await avatars.read_and_validate_upload(file)
    clean_bytes, extension = avatars.rerender_and_strip_metadata(raw)

    nombre_anterior = current_user.avatar_filename
    nuevo_nombre = storage.upload_object(
        storage.AVATAR_BUCKET, clean_bytes, extension, AVATAR_CONTENT_TYPES[extension]
    )

    current_user.avatar_filename = nuevo_nombre
    db.commit()
    db.refresh(current_user)

    # Se borra la anterior DESPUÉS de confirmar la nueva en la BD (si algo falla antes, la
    # foto anterior sigue siendo válida en vez de quedar el usuario sin ninguna).
    storage.delete_object(storage.AVATAR_BUCKET, nombre_anterior)

    security_logger.info("Foto de perfil actualizada: %s desde %s", current_user.email, _client_ip(request))
    return current_user


@router.delete("/users/me/avatar", response_model=schemas.MessageResponse)
def delete_my_avatar(
    db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)
):
    if not current_user.avatar_filename:
        raise HTTPException(status_code=404, detail="No tienes foto de perfil.")
    storage.delete_object(storage.AVATAR_BUCKET, current_user.avatar_filename)
    current_user.avatar_filename = None
    db.commit()
    return {"message": "Foto de perfil eliminada."}


@router.get("/users/{user_id}/avatar")
def get_user_avatar(
    user_id: UUID, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)
):
    """Cualquier usuario autenticado puede ver la foto de perfil de otro (no es información
    sensible más allá del nombre, que ya es visible en toda la app)."""
    usuario = db.query(models.User).filter(models.User.id == user_id).first()
    if not usuario or not usuario.avatar_filename:
        raise HTTPException(status_code=404, detail="Este usuario no tiene foto de perfil.")
    return storage.redirect_to_image(storage.AVATAR_BUCKET, usuario.avatar_filename)


@router.get("/users/{user_id}/mesocycles/", response_model=List[schemas.MesocycleSummaryResponse])
def obtener_mesociclos_usuario(
    user_id: UUID, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)
):
    ensure_owner_or_coach(db, user_id, current_user)
    return db.query(models.Mesocycle).filter(models.Mesocycle.user_id == user_id).all()


@router.post("/users/{user_id}/records/")
def upsert_personal_record(
    user_id: UUID,
    record: schemas.PRCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Añade una nueva marca o la actualiza si el ejercicio ya existe."""
    ensure_owner_or_coach(db, user_id, current_user)
    pr_existente = db.query(models.PersonalRecord).filter(
        models.PersonalRecord.user_id == user_id,
        models.PersonalRecord.exercise_name == record.exercise_name,
    ).first()

    if pr_existente:
        pr_existente.max_weight_kg = record.max_weight_kg
        mensaje = f"RM de {record.exercise_name} actualizado a {record.max_weight_kg}kg"
    else:
        db.add(models.PersonalRecord(
            user_id=user_id, exercise_name=record.exercise_name, max_weight_kg=record.max_weight_kg,
        ))
        mensaje = f"Nuevo RM de {record.exercise_name} registrado."

    # Si el nombre coincide con uno de los 4 levantamientos del Fit Level, esta marca también
    # actualiza esa métrica — así no hay que volver a escribirla en la otra pantalla.
    metric_key = PR_NAME_TO_FIT_LEVEL_LIFT.get(record.exercise_name.strip().lower())
    if metric_key:
        fila = db.query(models.FitnessBenchmark).filter(
            models.FitnessBenchmark.user_id == user_id, models.FitnessBenchmark.metric_key == metric_key,
        ).first()
        if fila:
            fila.value = record.max_weight_kg
        else:
            db.add(models.FitnessBenchmark(user_id=user_id, metric_key=metric_key, value=record.max_weight_kg))

    db.commit()
    return {"message": mensaje}


@router.get("/users/{user_id}/records/", response_model=List[schemas.PRResponse])
def obtener_marcas_atleta(
    user_id: UUID, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)
):
    ensure_owner_or_coach(db, user_id, current_user)
    return db.query(models.PersonalRecord).filter(models.PersonalRecord.user_id == user_id).all()
