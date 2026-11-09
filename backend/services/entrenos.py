"""Los entrenos de un coach, todos juntos: lo que programó para sus grupos y para cada atleta personalizado.

Alimenta la pantalla "Entrenos" del coach (lista y calendario). Un día programado para un GRUPO es un solo
entreno (aunque cada miembro tenga su propia sesión), y uno personalizado es el de ese atleta.
"""
from collections import defaultdict
from datetime import date, datetime

from sqlalchemy.orm import Session, joinedload

from backend import models
from backend.core.errors import NoEncontrado
from backend.core.security import _coach_athlete_ids, ensure_owner_or_coach
from backend.wod_scoring import format_wod_summary, rank_wod_sessions, wod_score_value
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
                "completed_names": [],
            }
        item["athletes_total"] += 1
        if sesion.status == "completed":
            item["athletes_completed"] += 1
            item["completed_names"].append(atleta.full_name)
        if meso.is_draft:
            item["is_draft"] = True
    return sorted(
        entrenos.values(),
        key=lambda e: (e["date"], e["group_name"] or e["athlete_name"] or "", e["program_name"] or ""),
    )


def resultados_del_entreno(db: Session, coach: models.User, session_id, como_atleta: bool = False) -> dict:
    """Cómo quedó un entreno entre sus miembros: quién lo terminó, cuándo y, si tiene un WOD con formato, el
    ranking por su resultado (mejor primero). `session_id` es la sesión de referencia que trae cada entreno de
    `entrenos_del_coach`: si es de un grupo, se juntan las de todos sus miembros ese día; si es de un atleta
    personalizado, es solo la suya.

    El orden de las filas: los que tienen resultado de WOD (por posición), después los que lo terminaron sin
    resultado numérico (por hora), y al final los pendientes. Sin WOD no hay posiciones: nadie "gana" una
    sesión de fuerza por terminarla antes.

    `como_atleta`: lo pide un atleta para el entreno de SU grupo. Solo ve a quienes ya lo terminaron (no quién
    falta) y solo a quienes aceptan aparecer en el leaderboard (User.show_in_ranking, el interruptor del perfil);
    él mismo aparece siempre. Un entreno que no es suyo, o que no es de un grupo, es un 404."""
    referencia = (
        db.query(models.Session)
        .options(joinedload(models.Session.mesocycle).joinedload(models.Mesocycle.user))
        .filter(models.Session.id == session_id)
        .first()
    )
    meso = referencia.mesocycle if referencia else None
    if (
        referencia is None
        or meso.user_id is None
        or meso.is_template
        or meso.is_self_managed
        or meso.is_class_log
        or meso.class_id is not None
    ):
        raise NoEncontrado("Entreno no encontrado")
    if como_atleta:
        if meso.user_id != coach.id or meso.group_id is None:
            raise NoEncontrado("Entreno no encontrado")
    else:
        ensure_owner_or_coach(db, meso.user_id, coach)

    opciones = (
        joinedload(models.Session.mesocycle).joinedload(models.Mesocycle.user),
        joinedload(models.Session.sets).joinedload(models.Set.exercise),
    )
    if meso.group_id is not None:
        grupo = db.query(models.Group).filter(models.Group.id == meso.group_id).first()
        sesiones = (
            db.query(models.Session)
            .join(models.Mesocycle, models.Session.mesocycle_id == models.Mesocycle.id)
            .options(*opciones)
            .filter(
                models.Mesocycle.group_id == meso.group_id,
                models.Mesocycle.name == meso.name,
                models.Mesocycle.start_date == meso.start_date,
                models.Session.scheduled_date == referencia.scheduled_date,
                models.Session.parent_session_id.is_(None),
            )
            .all()
        )
        tipo, titulo = "group", (grupo.name if grupo else "Grupo")
    else:
        sesiones = db.query(models.Session).options(*opciones).filter(models.Session.id == referencia.id).all()
        tipo, titulo = "athlete", meso.user.full_name

    if como_atleta:
        sesiones = [s for s in sesiones if s.mesocycle.user_id == coach.id or s.mesocycle.user.show_in_ranking]
    completadas = [s for s in sesiones if s.status == "completed"]
    pendientes = [] if como_atleta else sorted((s for s in sesiones if s.status != "completed"), key=lambda s: s.mesocycle.user.full_name.lower())
    con_wod = bool(referencia.wod_format)

    ordenadas = rank_wod_sessions(completadas) if con_wod else []
    con_resultado = [s for s in ordenadas if wod_score_value(s) is not None]
    sin_resultado = sorted(
        (s for s in completadas if s not in con_resultado), key=lambda s: s.completed_date or datetime.min
    )

    def fila(sesion: models.Session, posicion: int | None) -> dict:
        marcadas = sum(1 for serie in sesion.sets if serie.actual_reps is not None)
        return {
            "user_id": sesion.mesocycle.user_id,
            "full_name": sesion.mesocycle.user.full_name,
            "has_avatar": bool(sesion.mesocycle.user.has_avatar),
            "completed": sesion.status == "completed",
            "completed_at": sesion.completed_date,
            "score_label": format_wod_summary(sesion) if con_wod and sesion.status == "completed" else None,
            "rank": posicion,
            "sets_logged": marcadas,
            "sets_total": len(sesion.sets),
        }

    filas = [fila(s, i) for i, s in enumerate(con_resultado, start=1)]
    filas += [fila(s, None) for s in sin_resultado]
    filas += [fila(s, None) for s in pendientes]

    nombre_del_wod = next(
        (serie.exercise.name for s in sesiones for serie in s.sets if serie.block == "metcon" and serie.exercise), None
    )
    return {
        "date": referencia.scheduled_date,
        "kind": tipo,
        "title": titulo,
        "wod_format": referencia.wod_format,
        "wod_name": nombre_del_wod if con_wod else None,
        "time_cap_seconds": referencia.wod_time_cap_seconds if con_wod else None,
        "total": len(completadas) if como_atleta else len(sesiones),
        "completed": len(completadas),
        "rows": filas,
    }
