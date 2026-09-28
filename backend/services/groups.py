"""Programas de grupo: clonar lo programado a un miembro nuevo y aplicar a TODOS los atletas de
un programa un cambio de ejercicio (añadir, actualizar, eliminar). Sin HTTP ni commit: los routers
validan que el coach sea dueño del grupo, llaman aquí, hacen commit y arman el mensaje."""
from datetime import date
from typing import List
from uuid import UUID

from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from backend import models
from backend.routers.exercise_helpers import clean_coach_note, get_or_create_exercise
from backend.routers.pr_helpers import get_athlete_prs, resolve_weight_from_percentage
from backend.services.sets import clonar_set


def clonar_programa_para_atleta(db: Session, referencia: models.Mesocycle, user_id: UUID) -> models.Mesocycle:
    """Clona la estructura completa (sesiones + series + ejercicios) de un mesociclo de grupo
    para un atleta que se acaba de unir. No copia pesos/RMs específicos de nadie más:
    copia exactamente lo que el coach ya programó (mismos ejercicios/reps/RPE/peso prescrito),
    y el coach puede ajustarlo después desde la pestaña individual del atleta."""
    nuevo_meso = models.Mesocycle(
        user_id=user_id,
        group_id=referencia.group_id,
        name=referencia.name,
        discipline=referencia.discipline,
        start_date=referencia.start_date,
        end_date=referencia.end_date,
        is_active=referencia.is_active,
    )
    db.add(nuevo_meso)
    db.flush()

    sesiones_ref = (
        db.query(models.Session)
        .options(joinedload(models.Session.sets))
        .filter(models.Session.mesocycle_id == referencia.id)
        .all()
    )
    for sesion_ref in sesiones_ref:
        nueva_sesion = models.Session(
            mesocycle_id=nuevo_meso.id,
            scheduled_date=sesion_ref.scheduled_date,
            status=sesion_ref.status,
            athlete_notes=sesion_ref.athlete_notes,
        )
        db.add(nueva_sesion)
        db.flush()
        for set_ref in sesion_ref.sets:
            db.add(clonar_set(set_ref, nueva_sesion.id))

    return nuevo_meso


def resolver_peso_de_grupo(db: Session, req, athlete: models.User, nombre_ejercicio: str) -> float | None:
    """Resuelve el peso de ESTE atleta en particular, en orden:
    1. Pesos por categoría/género (bloque metcon) — si el coach llenó alguna de las 4 variantes,
       usa la que corresponde a la categoría (rx/scaled, default "rx") y sexo (default "male")
       de este atleta.
    2. % de 1RM (bloques de fuerza/weightlifting) — si viene `prescribed_percentage`, se calcula
       con las marcas YA registradas de este atleta (ver resolve_weight_from_percentage).
    3. `prescribed_weight` fijo, igual que siempre, si no vino ninguna de las anteriores."""
    variantes = {
        ("rx", "male"): req.prescribed_weight_rx_male,
        ("rx", "female"): req.prescribed_weight_rx_female,
        ("scaled", "male"): req.prescribed_weight_scaled_male,
        ("scaled", "female"): req.prescribed_weight_scaled_female,
    }
    if any(v is not None for v in variantes.values()):
        clave = (athlete.category or "rx", athlete.sex or "male")
        peso = variantes.get(clave)
        return peso if peso is not None else req.prescribed_weight

    if req.prescribed_percentage is not None:
        prs = get_athlete_prs(db, athlete.id)
        referencia = req.reference_exercise or nombre_ejercicio
        return resolve_weight_from_percentage(req.prescribed_percentage, req.prescribed_weight, referencia, prs)

    return req.prescribed_weight


def sesiones_por_mesociclo(
    db: Session, meso_ids: List[UUID], scheduled_date: date
) -> dict[UUID, models.Session]:
    """Una sola consulta para la sesión de esa fecha de CADA mesociclo del programa, en vez de
    una consulta por atleta dentro de un loop -- con un grupo de 30 atletas eso eran 30
    round-trips a la base de datos solo para ubicar la sesión de cada uno."""
    if not meso_ids:
        return {}
    sesiones = db.query(models.Session).filter(
        models.Session.mesocycle_id.in_(meso_ids),
        models.Session.scheduled_date == scheduled_date,
    ).all()
    return {s.mesocycle_id: s for s in sesiones}


def series_por_sesion_del_ejercicio(
    db: Session, session_ids: List[UUID], exercise_name: str
) -> dict[UUID, List[models.Set]]:
    """Igual que sesiones_por_mesociclo pero para las series de un ejercicio dado -- una sola
    consulta con session_id.in_(...) en vez de un JOIN por atleta dentro del loop."""
    if not session_ids:
        return {}
    todas = (
        db.query(models.Set)
        .join(models.Exercise, models.Set.exercise_id == models.Exercise.id)
        .filter(models.Set.session_id.in_(session_ids), models.Exercise.name == exercise_name)
        .order_by(models.Set.set_order)
        .all()
    )
    agrupadas: dict[UUID, List[models.Set]] = {}
    for s in todas:
        agrupadas.setdefault(s.session_id, []).append(s)
    return agrupadas


def sumar_miembros(db: Session, grupo: models.Group, atletas_nuevos: List[models.User]):
    """Agrega los atletas al grupo y les clona cada programa activo del grupo que aún no tengan."""
    for atleta in atletas_nuevos:
        grupo.members.append(atleta)
    db.flush()
    group_id = grupo.id

    # Un mesociclo de referencia por cada programa activo del grupo (mismo name + start_date)
    mesos_grupo = db.query(models.Mesocycle).filter(
        models.Mesocycle.group_id == group_id, models.Mesocycle.is_active == True
    ).all()
    programas_ref: dict[tuple, models.Mesocycle] = {}
    for m in mesos_grupo:
        clave = (m.name, m.start_date)
        programas_ref.setdefault(clave, m)

    for atleta in atletas_nuevos:
        programas_que_ya_tiene = {
            (m.name, m.start_date)
            for m in db.query(models.Mesocycle).filter(
                models.Mesocycle.user_id == atleta.id, models.Mesocycle.group_id == group_id
            ).all()
        }
        for clave, referencia in programas_ref.items():
            if clave not in programas_que_ya_tiene:
                clonar_programa_para_atleta(db, referencia, atleta.id)


def agregar_ejercicio(db: Session, mesos: List[models.Mesocycle], req):
    """Añade el ejercicio a la sesión de esa fecha de CADA mesociclo del programa. Devuelve un resultado por atleta."""
    ejercicio = get_or_create_exercise(db, req.exercise_name)

    sesiones_por_meso = sesiones_por_mesociclo(db, [m.id for m in mesos], req.scheduled_date)
    session_ids = [s.id for s in sesiones_por_meso.values()]
    conteos_por_sesion = dict(
        db.query(models.Set.session_id, func.count(models.Set.id))
        .filter(models.Set.session_id.in_(session_ids))
        .group_by(models.Set.session_id)
        .all()
    ) if session_ids else {}

    resultados = []
    for meso in mesos:
        sesion = sesiones_por_meso.get(meso.id)

        if not sesion:
            resultados.append({"full_name": meso.user.full_name, "status": "sin sesión en esa fecha"})
            continue

        series_actuales = conteos_por_sesion.get(sesion.id, 0)
        peso = resolver_peso_de_grupo(db, req, meso.user, req.exercise_name)
        for i in range(req.prescribed_sets):
            db.add(models.Set(
                session_id=sesion.id,
                exercise_id=ejercicio.id,
                set_order=series_actuales + i + 1,
                prescribed_reps=req.prescribed_reps,
                rpe=req.rpe,
                prescribed_weight=peso,
                prescribed_percentage=req.prescribed_percentage,
                reference_exercise=req.reference_exercise,
                block=req.block,
                coach_note=clean_coach_note(req.coach_note),
            ))
        resultados.append({"full_name": meso.user.full_name, "status": "añadido"})

    return resultados


def actualizar_ejercicio(db: Session, mesos: List[models.Mesocycle], req):
    """Edita el ejercicio en la sesión de esa fecha de CADA mesociclo del programa. Devuelve un resultado por atleta."""
    nuevo_ejercicio = get_or_create_exercise(db, req.new_exercise_name)

    sesiones_por_meso = sesiones_por_mesociclo(db, [m.id for m in mesos], req.scheduled_date)
    sets_por_sesion = series_por_sesion_del_ejercicio(
        db, [s.id for s in sesiones_por_meso.values()], req.exercise_name
    )

    resultados = []
    for meso in mesos:
        sesion = sesiones_por_meso.get(meso.id)
        if not sesion:
            resultados.append({"full_name": meso.user.full_name, "status": "sin sesión en esa fecha"})
            continue

        sets_existentes = sets_por_sesion.get(sesion.id, [])
        if not sets_existentes:
            resultados.append({"full_name": meso.user.full_name, "status": "no tenía ese ejercicio en esa fecha"})
            continue

        peso = resolver_peso_de_grupo(db, req, meso.user, req.new_exercise_name)
        num_original = len(sets_existentes)
        limite = min(num_original, req.prescribed_sets)
        for i in range(limite):
            sets_existentes[i].exercise_id = nuevo_ejercicio.id
            sets_existentes[i].prescribed_reps = req.prescribed_reps
            sets_existentes[i].rpe = req.rpe
            sets_existentes[i].prescribed_weight = peso
            sets_existentes[i].prescribed_percentage = req.prescribed_percentage
            sets_existentes[i].reference_exercise = req.reference_exercise
            if req.block is not None:
                sets_existentes[i].block = req.block
            if "coach_note" in req.model_fields_set:
                sets_existentes[i].coach_note = clean_coach_note(req.coach_note)

        if req.prescribed_sets < num_original:
            for extra in sets_existentes[req.prescribed_sets:]:
                db.delete(extra)
        elif req.prescribed_sets > num_original:
            bloque_nuevas = req.block if req.block is not None else sets_existentes[0].block
            for i in range(num_original, req.prescribed_sets):
                db.add(models.Set(
                    session_id=sesion.id,
                    exercise_id=nuevo_ejercicio.id,
                    set_order=i + 1,
                    prescribed_reps=req.prescribed_reps,
                    rpe=req.rpe,
                    prescribed_weight=peso,
                    prescribed_percentage=req.prescribed_percentage,
                    reference_exercise=req.reference_exercise,
                    block=bloque_nuevas,
                    coach_note=(
                        clean_coach_note(req.coach_note)
                        if "coach_note" in req.model_fields_set
                        else sets_existentes[0].coach_note
                    ),
                ))

        resultados.append({"full_name": meso.user.full_name, "status": "actualizado"})

    return resultados


def eliminar_ejercicio(db: Session, mesos: List[models.Mesocycle], req):
    """Quita el ejercicio (todas sus series) de la sesión de esa fecha de CADA mesociclo del programa."""
    sesiones_por_meso = sesiones_por_mesociclo(db, [m.id for m in mesos], req.scheduled_date)
    sets_por_sesion = series_por_sesion_del_ejercicio(
        db, [s.id for s in sesiones_por_meso.values()], req.exercise_name
    )

    resultados = []
    for meso in mesos:
        sesion = sesiones_por_meso.get(meso.id)
        if not sesion:
            resultados.append({"full_name": meso.user.full_name, "status": "sin sesión en esa fecha"})
            continue

        sets_existentes = sets_por_sesion.get(sesion.id, [])
        for s in sets_existentes:
            db.delete(s)
        resultados.append({"full_name": meso.user.full_name, "status": "eliminado" if sets_existentes else "no tenía ese ejercicio"})

    return resultados
