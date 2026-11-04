"""Los entrenos de un coach, todos juntos: lo que programó para sus grupos y para cada atleta personalizado.

Alimenta la pantalla "Entrenos" del coach (lista y calendario). Un día programado para un GRUPO es un solo
entreno (aunque cada miembro tenga su propia sesión), y uno personalizado es el de ese atleta.
"""
from collections import defaultdict
from datetime import date

from sqlalchemy.orm import Session

from backend import models
from backend.core.security import _coach_athlete_ids
from backend.services.block_notes import TODOS_LOS_BLOQUES

MAX_DIAS_DEL_RANGO = 400


def _bloques_de_la_sesion(sesion: models.Session, bloques_de_series: set[str]) -> list[str]:
    """Los bloques que tiene el día (con ejercicios o escritos como texto), en el orden del día."""
    presentes = set(bloques_de_series)
    if sesion.warmup_notes:
        presentes.add("warmup")
    if sesion.wod_notes or sesion.wod_format:
        presentes.add("metcon")
    presentes.update(clave for clave, texto in (sesion.block_notes or {}).items() if texto)
    personalizado = [b for b in (sesion.block_order or "").split(",") if b]
    orden = personalizado + [b for b in TODOS_LOS_BLOQUES if b not in personalizado]
    return [b for b in orden if b in presentes] + sorted(b for b in presentes if b not in orden)


def entrenos_del_coach(db: Session, coach: models.User, desde: date, hasta: date) -> list[dict]:
    """Los entrenos programados entre `desde` y `hasta` (ambos incluidos) para los atletas del coach.

    Un admin ve los de todos. No incluye lo que no es programación del coach: plantillas de planes, clases
    del box, el registro propio de un atleta ni las versiones "adaptadas al tiempo" de una sesión."""
    consulta = (
        db.query(models.Session, models.Mesocycle, models.User)
        .join(models.Mesocycle, models.Session.mesocycle_id == models.Mesocycle.id)
        .join(models.User, models.Mesocycle.user_id == models.User.id)
        .filter(
            models.Session.scheduled_date >= desde,
            models.Session.scheduled_date <= hasta,
            models.Session.parent_session_id.is_(None),
            models.Mesocycle.is_template == False,  # noqa: E712
            models.Mesocycle.is_self_managed == False,  # noqa: E712
            models.Mesocycle.is_class_log == False,  # noqa: E712
            models.Mesocycle.class_id.is_(None),
        )
    )
    if coach.role != "admin":
        ids = _coach_athlete_ids(db, coach)
        if not ids:
            return []
        consulta = consulta.filter(models.Mesocycle.user_id.in_(ids))
    filas = consulta.order_by(models.Session.scheduled_date, models.User.full_name).all()
    if not filas:
        return []

    # Bloques y ejercicios de las series de cada sesión, en UNA consulta (no una por sesión)
    sesion_ids = [sesion.id for sesion, _, _ in filas]
    bloques_de: dict = defaultdict(set)
    ejercicios_de: dict = defaultdict(set)
    for sesion_id, bloque, ejercicio_id in (
        db.query(models.Set.session_id, models.Set.block, models.Set.exercise_id)
        .filter(models.Set.session_id.in_(sesion_ids))
        .distinct()
        .all()
    ):
        if bloque:
            bloques_de[sesion_id].add(bloque)
        if ejercicio_id:
            ejercicios_de[sesion_id].add(ejercicio_id)

    ids_de_grupo = {meso.group_id for _, meso, _ in filas if meso.group_id is not None}
    nombres_de_grupo = (
        {g.id: g.name for g in db.query(models.Group).filter(models.Group.id.in_(ids_de_grupo))} if ids_de_grupo else {}
    )

    entrenos: dict[tuple, dict] = {}
    for sesion, meso, atleta in filas:
        if meso.group_id is not None and meso.group_id in nombres_de_grupo:
            # Un día de grupo es UN entreno: la misma fecha del mismo programa de ese grupo
            clave = ("group", meso.group_id, meso.name, meso.start_date, sesion.scheduled_date)
        else:
            clave = ("athlete", atleta.id, meso.id, sesion.scheduled_date)
        item = entrenos.get(clave)
        if item is None:
            es_grupo = clave[0] == "group"
            bloques = _bloques_de_la_sesion(sesion, bloques_de.get(sesion.id, set()))
            item = entrenos[clave] = {
                "date": sesion.scheduled_date,
                "kind": clave[0],
                "group_id": meso.group_id if es_grupo else None,
                "group_name": nombres_de_grupo.get(meso.group_id) if es_grupo else None,
                "athlete_id": None if es_grupo else atleta.id,
                "athlete_name": None if es_grupo else atleta.full_name,
                "program_name": meso.name,
                "program_start_date": meso.start_date,
                "mesocycle_id": meso.id,
                "session_id": sesion.id,
                "blocks": bloques,
                "exercise_count": len(ejercicios_de.get(sesion.id, set())),
                "is_empty": not bloques,
                "is_draft": bool(meso.is_draft),
                "athletes_total": 0,
                "athletes_completed": 0,
            }
        item["athletes_total"] += 1
        if sesion.status == "completed":
            item["athletes_completed"] += 1
        if meso.is_draft:
            item["is_draft"] = True
    return sorted(
        entrenos.values(),
        key=lambda e: (e["date"], e["group_name"] or e["athlete_name"] or "", e["program_name"] or ""),
    )
