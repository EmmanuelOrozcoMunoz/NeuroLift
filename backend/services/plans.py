"""Planes: copiar un plan publicado a un mesociclo propio del atleta. Sin HTTP ni commit: los
routers validan permisos y hacen commit."""
from dataclasses import dataclass, field
from datetime import date, timedelta
from uuid import UUID

from sqlalchemy.orm import Session, joinedload

from backend import models
from backend.core.errors import NoEncontrado, Prohibido, SolicitudInvalida
from backend.services.exercises import clean_coach_note, get_or_create_exercise
from backend.services.prs import get_athlete_prs, resolve_weight_from_percentage
from backend.services.sets import clonar_set, filas_de, reservar_orden

# Los planes guardan sus días como offset relativo (day_offset) más una fecha sintética
# (PLAN_EPOCH + day_offset) para no romper las columnas de fecha obligatorias.
PLAN_EPOCH = date(2000, 1, 1)


@dataclass
class ResultadoAdquisicion:
    mesocycle_id: UUID
    missing_prs: list[str] = field(default_factory=list)


def adquirir_plan(
    db: Session, plan: models.Mesocycle, atleta: models.User, start_date: date, group_id: UUID | None = None
) -> ResultadoAdquisicion:
    """Clona el plan (ya validado como publicado y visible) a un mesociclo propio del atleta con
    las fechas reales a partir de `start_date` y las cargas en % resueltas con SUS marcas de 1RM.
    Con `group_id`, el mesociclo queda como parte del programa de ese grupo."""
    prs = get_athlete_prs(db, atleta.id)

    nuevo_meso = models.Mesocycle(
        user_id=atleta.id,
        group_id=group_id,
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
            block_order=sesion_plan.block_order,
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


def obtener_plan_propio(db: Session, plan_id: UUID, coach: models.User) -> models.Mesocycle:
    """Un plan (plantilla) del propio coach, con sus sesiones y series cargadas. El admin puede
    usar cualquiera. Publicado o en borrador da igual: una plantilla sirve para asignar."""
    plan = (
        db.query(models.Mesocycle)
        .options(joinedload(models.Mesocycle.sessions).joinedload(models.Session.sets).joinedload(models.Set.exercise))
        .filter(models.Mesocycle.id == plan_id, models.Mesocycle.is_template == True)  # noqa: E712
        .first()
    )
    if not plan:
        raise NoEncontrado("Plan no encontrado")
    if coach.role != "admin" and plan.created_by_coach_id != coach.id:
        raise Prohibido("Este plan no te pertenece")
    return plan


def asignar_plan_a_grupo(
    db: Session, plan: models.Mesocycle, grupo: models.Group, start_date: date
) -> list[dict]:
    """Copia el plan a cada miembro del grupo: fechas reales desde `start_date` y las cargas en %
    resueltas con las marcas de CADA atleta. Sin commit. Quien ya recibió este mismo plan en esa
    misma fecha se omite, así volver a asignarlo solo alcanza a los miembros nuevos."""
    if not plan.sessions:
        raise SolicitudInvalida("Este plan no tiene días de entrenamiento.")
    if not any(sesion.sets for sesion in plan.sessions):
        raise SolicitudInvalida("Este plan todavía no tiene ejercicios: agrégalos antes de asignarlo.")

    miembros = list(grupo.members)
    ya_asignados = {
        fila[0]
        for fila in db.query(models.Mesocycle.user_id).filter(
            models.Mesocycle.group_id == grupo.id,
            models.Mesocycle.source_plan_id == plan.id,
            models.Mesocycle.start_date == start_date,
        )
    }

    resultados = []
    for atleta in sorted(miembros, key=lambda a: a.full_name.lower()):
        if atleta.id in ya_asignados:
            resultados.append({"user_id": atleta.id, "full_name": atleta.full_name, "status": "skipped",
                               "mesocycle_id": None, "missing_prs": []})
            continue
        resultado = adquirir_plan(db, plan, atleta, start_date, group_id=grupo.id)
        resultados.append({"user_id": atleta.id, "full_name": atleta.full_name, "status": "assigned",
                           "mesocycle_id": resultado.mesocycle_id, "missing_prs": resultado.missing_prs})
    return resultados


def actualizar_ejercicio_del_plan(db: Session, sesion: models.Session, req) -> int:
    """Reemplaza lo prescrito de un ejercicio de un día del plan (sin commit). Devuelve cuántas
    series quedaron.

    Las series se emparejan por posición: la 1.ª existente recibe la 1.ª fila, etc. Si sobran filas
    se crean series nuevas junto a las del ejercicio; si sobran series, se borran las últimas. Un
    plan no tiene dueño, así que no hay marcas con las que resolver un % a kg: la carga se guarda
    como se pidió y el kg se calcula cuando un atleta adquiere el plan."""
    existentes = (
        db.query(models.Set)
        .filter(models.Set.session_id == sesion.id, models.Set.id.in_(req.set_ids))
        .order_by(models.Set.set_order)
        .all()
    )
    if len(existentes) != len(set(req.set_ids)):
        raise NoEncontrado("Ese ejercicio no está en este día del plan")

    ejercicio = get_or_create_exercise(db, req.exercise_name)
    filas = filas_de(req)
    nota_enviada = "coach_note" in req.model_fields_set

    for serie, fila in zip(existentes, filas):
        serie.exercise_id = ejercicio.id
        serie.prescribed_reps = fila.reps
        serie.rpe = req.rpe
        serie.prescribed_weight = fila.weight
        serie.prescribed_percentage = fila.percentage
        serie.reference_exercise = req.reference_exercise
        if req.block is not None:
            serie.block = req.block
        if nota_enviada:
            serie.coach_note = clean_coach_note(req.coach_note)

    if len(filas) < len(existentes):
        for sobrante in existentes[len(filas):]:
            db.delete(sobrante)
    elif len(filas) > len(existentes):
        bloque_nuevas = req.block if req.block is not None else existentes[0].block
        nota_nuevas = clean_coach_note(req.coach_note) if nota_enviada else existentes[0].coach_note
        del_dia = db.query(models.Set).filter(models.Set.session_id == sesion.id).all()
        orden = reservar_orden(del_dia, ejercicio.id, len(filas) - len(existentes))
        for i in range(len(existentes), len(filas)):
            db.add(models.Set(
                session_id=sesion.id,
                exercise_id=ejercicio.id,
                set_order=orden + (i - len(existentes)),
                prescribed_reps=filas[i].reps,
                rpe=req.rpe,
                prescribed_weight=filas[i].weight,
                prescribed_percentage=filas[i].percentage,
                reference_exercise=req.reference_exercise,
                block=bloque_nuevas,
                coach_note=nota_nuevas,
            ))
    return len(filas)
