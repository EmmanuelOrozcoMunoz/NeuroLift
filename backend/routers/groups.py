from datetime import date
from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile
from sqlalchemy import and_, func
from sqlalchemy.orm import Session, joinedload

from backend import avatars, models, schemas, storage
from backend.core.security import _ip_and_user_key, get_current_user, limiter, require_coach
from backend.database import get_db
from backend.services.group_access import claim_athletes_for_group, ensure_athletes_addable, get_owned_group
from backend.services.groups import (
    actualizar_ejercicio,
    agregar_ejercicio,
    eliminar_ejercicio,
    sesiones_por_mesociclo,
    sumar_miembros,
)
from backend.wod_scoring import format_wod_summary, rank_wod_sessions, wod_score_value

router = APIRouter(prefix="/groups", tags=["groups"])

@router.post("/", response_model=schemas.GroupResponse)
def create_group(
    req: schemas.GroupCreate, db: Session = Depends(get_db), current_user: models.User = Depends(require_coach)
):
    nuevo_grupo = models.Group(coach_id=current_user.id, box_id=current_user.box_id, name=req.name)
    if req.athlete_ids:
        atletas = db.query(models.User).filter(
            models.User.id.in_(req.athlete_ids), models.User.role == "athlete"
        ).all()
        ensure_athletes_addable(atletas, current_user)
        claim_athletes_for_group(atletas, current_user)
        nuevo_grupo.members = atletas
    db.add(nuevo_grupo)
    db.commit()
    db.refresh(nuevo_grupo)
    return nuevo_grupo


@router.get("/", response_model=List[schemas.GroupSummaryResponse])
def list_my_groups(db: Session = Depends(get_db), current_user: models.User = Depends(require_coach)):
    """Panel del coach: todos sus grupos con el número de atletas en cada uno. El dueño del box
    ve todos los grupos de su box; el admin de plataforma, todos los de todos los boxes."""
    query = db.query(models.Group).options(joinedload(models.Group.coach))
    if current_user.role == "owner":
        query = query.filter(models.Group.box_id == current_user.box_id)
    elif current_user.role != "admin":
        query = query.filter(models.Group.coach_id == current_user.id)
    grupos = query.all()
    return [
        schemas.GroupSummaryResponse(
            id=g.id, name=g.name, created_at=g.created_at, member_count=len(g.members),
            coach_name=g.coach.full_name, has_cover_image=g.has_cover_image,
        )
        for g in grupos
    ]


@router.get("/{group_id}", response_model=schemas.GroupResponse)
def get_group_detail(
    group_id: UUID, db: Session = Depends(get_db), current_user: models.User = Depends(require_coach)
):
    return get_owned_group(db, group_id, current_user)


@router.post("/{group_id}/cover", response_model=schemas.GroupResponse)
@limiter.limit("10/hour", key_func=_ip_and_user_key)
async def upload_group_cover(
    request: Request,
    group_id: UUID,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_coach),
):
    """Sube (o reemplaza) la foto de portada del grupo — mismo pipeline de saneo que el avatar
    de usuario (magic-number, re-render sin metadatos, nombre aleatorio)."""
    grupo = get_owned_group(db, group_id, current_user)
    raw = await avatars.read_and_validate_upload(file)
    clean_bytes, extension = avatars.rerender_and_strip_metadata(raw)

    nombre_anterior = grupo.cover_image_filename
    nuevo_nombre = storage.upload_object(
        storage.GROUP_COVER_BUCKET, clean_bytes, extension, avatars.AVATAR_CONTENT_TYPES[extension]
    )
    grupo.cover_image_filename = nuevo_nombre
    db.commit()
    db.refresh(grupo)
    storage.delete_object(storage.GROUP_COVER_BUCKET, nombre_anterior)
    return grupo


@router.delete("/{group_id}/cover", response_model=schemas.MessageResponse)
def delete_group_cover(
    group_id: UUID, db: Session = Depends(get_db), current_user: models.User = Depends(require_coach)
):
    grupo = get_owned_group(db, group_id, current_user)
    if not grupo.cover_image_filename:
        raise HTTPException(status_code=404, detail="Este grupo no tiene foto de portada.")
    storage.delete_object(storage.GROUP_COVER_BUCKET, grupo.cover_image_filename)
    grupo.cover_image_filename = None
    db.commit()
    return {"message": "Foto de portada eliminada."}


@router.get("/{group_id}/cover")
def get_group_cover(
    group_id: UUID, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)
):
    grupo = get_owned_group(db, group_id, current_user)
    return storage.redirect_to_image(storage.GROUP_COVER_BUCKET, grupo.cover_image_filename)


@router.post("/{group_id}/members", response_model=schemas.GroupResponse)
def add_group_members(
    group_id: UUID,
    req: schemas.GroupMemberAdd,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_coach),
):
    """Añade atletas al grupo y, a cada uno que sea realmente nuevo, le clona el/los
    mesociclo(s) activo(s) del grupo (mismos ejercicios/reps/RPE/peso ya programados),
    para que aparezca de inmediato en su propia pestaña de edición."""
    grupo = get_owned_group(db, group_id, current_user)
    existentes = {m.id for m in grupo.members}
    nuevos = db.query(models.User).filter(
        models.User.id.in_(req.athlete_ids), models.User.role == "athlete"
    ).all()
    ensure_athletes_addable(nuevos, current_user)
    claim_athletes_for_group(nuevos, current_user)
    atletas_nuevos = [a for a in nuevos if a.id not in existentes]

    sumar_miembros(db, grupo, atletas_nuevos)
    db.commit()
    db.refresh(grupo)
    return grupo


@router.delete("/{group_id}/members/{user_id}", response_model=schemas.GroupResponse)
def remove_group_member(
    group_id: UUID,
    user_id: UUID,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_coach),
):
    grupo = get_owned_group(db, group_id, current_user)
    grupo.members = [m for m in grupo.members if m.id != user_id]
    db.commit()
    db.refresh(grupo)
    return grupo


@router.delete("/{group_id}")
def delete_group(
    group_id: UUID, db: Session = Depends(get_db), current_user: models.User = Depends(require_coach)
):
    grupo = get_owned_group(db, group_id, current_user)
    db.delete(grupo)
    db.commit()
    return {"message": "Grupo eliminado correctamente"}


@router.get("/{group_id}/mesocycles", response_model=List[schemas.GroupMesocycleProgram])
def list_group_mesocycles(
    group_id: UUID, db: Session = Depends(get_db), current_user: models.User = Depends(require_coach)
):
    """Mesociclos programados para este grupo, agrupados por programa (mismo nombre + fecha de inicio),
    cada uno con la instancia por-atleta correspondiente (una fila real de Mesocycle por atleta)."""
    get_owned_group(db, group_id, current_user)  # valida existencia + pertenencia

    mesos = (
        db.query(models.Mesocycle)
        .options(joinedload(models.Mesocycle.user))
        .filter(models.Mesocycle.group_id == group_id)
        .order_by(models.Mesocycle.created_at.desc())
        .all()
    )

    programas: dict[tuple, schemas.GroupMesocycleProgram] = {}
    for meso in mesos:
        clave = (meso.name, meso.start_date)
        if clave not in programas:
            # Calendario compartido: cualquier atleta del programa sirve de referencia,
            # todos entrenan las mismas fechas (misma construcción del grupo).
            fechas = (
                db.query(models.Session.scheduled_date)
                .filter(models.Session.mesocycle_id == meso.id)
                .order_by(models.Session.scheduled_date)
                .all()
            )
            programas[clave] = schemas.GroupMesocycleProgram(
                name=meso.name,
                discipline=meso.discipline,
                start_date=meso.start_date,
                end_date=meso.end_date,
                created_at=meso.created_at,
                athletes=[],
                session_dates=[f[0] for f in fechas],
            )
        programas[clave].athletes.append(
            schemas.GroupMesocycleAthlete(
                user_id=meso.user_id,
                full_name=meso.user.full_name,
                mesocycle_id=meso.id,
                is_active=meso.is_active,
            )
        )

    return list(programas.values())


def _get_group_program_mesocycles(
    db: Session, group_id: UUID, program_name: str, program_start_date, current_user: models.User
) -> List[models.Mesocycle]:
    get_owned_group(db, group_id, current_user)
    mesos = (
        db.query(models.Mesocycle)
        .options(joinedload(models.Mesocycle.user))
        .filter(
            models.Mesocycle.group_id == group_id,
            models.Mesocycle.name == program_name,
            models.Mesocycle.start_date == program_start_date,
        )
        .all()
    )
    if not mesos:
        raise HTTPException(status_code=404, detail="No se encontró ese programa para el grupo")
    return mesos


@router.delete("/{group_id}/mesocycles")
def delete_group_program(
    group_id: UUID,
    req: schemas.GroupProgramDelete,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_coach),
):
    """Elimina el programa completo: el mesociclo (y en cascada sus sesiones/series) de CADA
    atleta del grupo que lo tenga asignado."""
    mesos = _get_group_program_mesocycles(db, group_id, req.program_name, req.program_start_date, current_user)
    total = len(mesos)
    for meso in mesos:
        db.delete(meso)
    db.commit()
    return {"message": f"Programa '{req.program_name}' eliminado para {total} atleta(s)."}


@router.post("/{group_id}/sessions/bulk-add-exercise")
def add_exercise_to_group_session(
    group_id: UUID,
    req: schemas.GroupSessionExerciseAdd,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_coach),
):
    """Añade el mismo ejercicio (mismas series/reps/RPE/peso) a la sesión de una fecha dada,
    para TODOS los atletas del programa a la vez. Útil para ajustes que aplican a todo el equipo."""
    mesos = _get_group_program_mesocycles(db, group_id, req.program_name, req.program_start_date, current_user)
    resultados = agregar_ejercicio(db, mesos, req)

    db.commit()
    exitosos = sum(1 for r in resultados if r["status"] == "añadido")
    return {
        "message": f"'{req.exercise_name}' añadido a {exitosos}/{len(resultados)} atleta(s) del grupo para el {req.scheduled_date}",
        "results": resultados,
    }


@router.put("/{group_id}/sessions/bulk-update-exercise")
def update_exercise_in_group_session(
    group_id: UUID,
    req: schemas.GroupSessionExerciseUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_coach),
):
    """Edita (nombre/series/reps/RPE/peso) un ejercicio ya existente en la sesión de una fecha dada,
    para TODOS los atletas del programa. Cada atleta conserva su propio peso salvo que el coach
    lo cambie explícitamente aquí (en cuyo caso se aplica el mismo peso a todos)."""
    mesos = _get_group_program_mesocycles(db, group_id, req.program_name, req.program_start_date, current_user)
    resultados = actualizar_ejercicio(db, mesos, req)

    db.commit()
    exitosos = sum(1 for r in resultados if r["status"] == "actualizado")
    return {
        "message": f"'{req.exercise_name}' actualizado en {exitosos}/{len(resultados)} atleta(s) del grupo",
        "results": resultados,
    }


@router.post("/{group_id}/sessions/bulk-delete-exercise")
def delete_exercise_from_group_session(
    group_id: UUID,
    req: schemas.GroupSessionExerciseDelete,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_coach),
):
    """Elimina por completo un ejercicio (todas sus series) de la sesión de una fecha dada,
    para TODOS los atletas del programa."""
    mesos = _get_group_program_mesocycles(db, group_id, req.program_name, req.program_start_date, current_user)
    resultados = eliminar_ejercicio(db, mesos, req)

    db.commit()
    exitosos = sum(1 for r in resultados if r["status"] == "eliminado")
    return {
        "message": f"'{req.exercise_name}' eliminado de {exitosos}/{len(resultados)} atleta(s) del grupo",
        "results": resultados,
    }


@router.post("/{group_id}/sessions/bulk-set-wod-format")
def set_group_session_wod_format(
    group_id: UUID,
    req: schemas.GroupSessionWodFormatUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_coach),
):
    """El coach fija (o quita) el formato de WOD y su timer/time cap UNA sola vez para la
    sesión de una fecha dada, aplicado a TODOS los atletas del programa — así no hay que
    repetir la misma acción atleta por atleta cuando todo el grupo hace el mismo WOD."""
    mesos = _get_group_program_mesocycles(db, group_id, req.program_name, req.program_start_date, current_user)
    sesiones_por_meso = sesiones_por_mesociclo(db, [m.id for m in mesos], req.scheduled_date)

    resultados = []
    for meso in mesos:
        sesion = sesiones_por_meso.get(meso.id)
        if not sesion:
            resultados.append({"full_name": meso.user.full_name, "status": "sin sesión en esa fecha"})
            continue
        sesion.wod_format = req.wod_format
        sesion.wod_time_cap_seconds = req.time_cap_seconds if req.wod_format else None
        resultados.append({"full_name": meso.user.full_name, "status": "actualizado"})

    db.commit()
    exitosos = sum(1 for r in resultados if r["status"] == "actualizado")
    return {
        "message": f"Formato de WOD actualizado para {exitosos}/{len(resultados)} atleta(s) del grupo",
        "results": resultados,
    }


@router.post("/{group_id}/sessions/bulk-set-wod-notes")
def set_group_session_wod_notes(
    group_id: UUID,
    req: schemas.GroupSessionWodNotesUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_coach),
):
    """El coach escribe la descripción libre del WOD UNA sola vez para la sesión de una fecha
    dada, aplicado a TODOS los atletas del programa — mismo motivo que bulk-set-wod-format, para
    el bloque Metabólico/WOD (ver WodBlockCard/BulkWodBlockCard en el frontend)."""
    mesos = _get_group_program_mesocycles(db, group_id, req.program_name, req.program_start_date, current_user)
    sesiones_por_meso = sesiones_por_mesociclo(db, [m.id for m in mesos], req.scheduled_date)

    resultados = []
    for meso in mesos:
        sesion = sesiones_por_meso.get(meso.id)
        if not sesion:
            resultados.append({"full_name": meso.user.full_name, "status": "sin sesión en esa fecha"})
            continue
        sesion.wod_notes = req.wod_notes or None
        resultados.append({"full_name": meso.user.full_name, "status": "actualizado"})

    db.commit()
    exitosos = sum(1 for r in resultados if r["status"] == "actualizado")
    return {
        "message": f"Descripción del WOD actualizada para {exitosos}/{len(resultados)} atleta(s) del grupo",
        "results": resultados,
    }


@router.get("/{group_id}/wod-days", response_model=List[schemas.WodDaySummary])
def get_group_wod_days(
    group_id: UUID, db: Session = Depends(get_db), current_user: models.User = Depends(require_coach)
):
    """Fechas del grupo con un WOD prescrito (wod_format) — para que el coach elija cuál quiere
    ver en la tabla de posiciones por WOD (GET /groups/{group_id}/wod-leaderboard)."""
    get_owned_group(db, group_id, current_user)

    # El "nombre" del WOD no se guarda aparte: ya vive como el nombre del ejercicio del bloque
    # metabólico (ej. "Helen (3 rondas de...)") — lo tomamos de ahí para no duplicar lo que el
    # coach ya escribió al armar la sesión (ver bloque "metcon" en backend/schemas/common.py:Bloque).
    filas = (
        db.query(
            models.Session.scheduled_date,
            models.Session.wod_format,
            func.max(models.Exercise.name).label("wod_name"),
            func.max(models.Session.wod_time_cap_seconds).label("time_cap_seconds"),
            func.count(func.distinct(models.Session.id)).label("participantes"),
        )
        .join(models.Mesocycle, models.Session.mesocycle_id == models.Mesocycle.id)
        .outerjoin(models.Set, and_(models.Set.session_id == models.Session.id, models.Set.block == "metcon"))
        .outerjoin(models.Exercise, models.Exercise.id == models.Set.exercise_id)
        .filter(models.Mesocycle.group_id == group_id, models.Session.wod_format.isnot(None))
        .group_by(models.Session.scheduled_date, models.Session.wod_format)
        .order_by(models.Session.scheduled_date.desc())
        .all()
    )
    return [
        schemas.WodDaySummary(
            scheduled_date=f.scheduled_date,
            wod_format=f.wod_format,
            wod_name=f.wod_name,
            time_cap_seconds=f.time_cap_seconds,
            participants_count=f.participantes,
        )
        for f in filas
    ]


@router.get("/{group_id}/wod-leaderboard", response_model=List[schemas.WodLeaderboardRow])
def get_group_wod_leaderboard(
    group_id: UUID,
    scheduled_date: date,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_coach),
):
    """Tabla de posiciones de UN WOD específico del grupo: todos los atletas que lo tenían
    prescrito ese día, ordenados por su resultado real según el formato (ver
    rank_wod_sessions). Los que aún no lo completan aparecen al final, sin rank."""
    get_owned_group(db, group_id, current_user)

    sesiones = (
        db.query(models.Session)
        .join(models.Mesocycle, models.Session.mesocycle_id == models.Mesocycle.id)
        .options(
            joinedload(models.Session.mesocycle).joinedload(models.Mesocycle.user),
            joinedload(models.Session.sets).joinedload(models.Set.exercise),
        )
        .filter(
            models.Mesocycle.group_id == group_id,
            models.Session.scheduled_date == scheduled_date,
            models.Session.wod_format.isnot(None),
        )
        .all()
    )
    if not sesiones:
        return []

    # El "nombre" del WOD ya vive como el nombre del ejercicio del bloque metabólico — se toma
    # de la primera sesión que tenga uno, es el mismo para todo el grupo ese día.
    wod_name = next(
        (s.exercise.name for sesion in sesiones for s in sesion.sets if s.block == "metcon" and s.exercise),
        None,
    )

    completadas = [s for s in sesiones if s.status == "completed"]
    ordenadas = rank_wod_sessions(completadas)

    filas: list[schemas.WodLeaderboardRow] = []
    rank = 1
    for sesion in ordenadas:
        tiene_score = wod_score_value(sesion) is not None
        filas.append(schemas.WodLeaderboardRow(
            user_id=sesion.mesocycle.user_id,
            full_name=sesion.mesocycle.user.full_name,
            has_avatar=sesion.mesocycle.user.has_avatar,
            wod_format=sesion.wod_format,
            wod_name=wod_name,
            score_label=format_wod_summary(sesion),
            rank=rank if tiene_score else None,
            completed=True,
        ))
        if tiene_score:
            rank += 1

    completados_ids = {s.mesocycle.user_id for s in completadas}
    pendientes = [s for s in sesiones if s.mesocycle.user_id not in completados_ids]
    for sesion in pendientes:
        filas.append(schemas.WodLeaderboardRow(
            user_id=sesion.mesocycle.user_id,
            full_name=sesion.mesocycle.user.full_name,
            has_avatar=sesion.mesocycle.user.has_avatar,
            wod_format=sesion.wod_format,
            wod_name=wod_name,
            score_label=None,
            rank=None,
            completed=False,
        ))
    return filas
