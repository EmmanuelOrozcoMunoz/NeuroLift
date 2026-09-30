"""Ranking del box entre atletas: marcas (1RM) de los levantamientos principales y WODs.

Las marcas se limitan a los dos levantamientos olímpicos principales (Snatch y Clean & Jerk).
Solo cuentan los atletas de esa cuenta que quieren aparecer (`show_in_ranking`). En los WODs solo
entran las sesiones que el propio atleta anota a mano (`is_self_managed`): el nombre de un WOD
programado por un coach suele traer su contenido, y las clases y los mesociclos del coach son
confidenciales. Sin HTTP ni commit.
"""
from collections import defaultdict
from uuid import UUID

from sqlalchemy.orm import Session, joinedload

from backend import models
from backend.services.prs import normalize_exercise_name
from backend.wod_scoring import format_wod_summary, rank_wod_sessions, wod_score_value


# Los únicos levantamientos que tienen ranking de marcas, en el orden en que se muestran. Se
# comparan por su forma normalizada, así "snatch", "Arranque" o "clean and jerk" cuentan igual.
LEVANTAMIENTOS_PRINCIPALES = ("Snatch", "Clean & Jerk")
_PRINCIPALES = {normalize_exercise_name(n): n for n in LEVANTAMIENTOS_PRINCIPALES}


def nombre_mas_comun(nombres: list[str]) -> str:
    """Cómo mostrar un ejercicio o WOD que varios escribieron distinto ("Fran" / "fran"): la
    escritura más frecuente y, en empate, la primera por orden alfabético (así no depende del
    orden en que la base devuelve las filas)."""
    cuenta: dict[str, int] = {}
    for n in nombres:
        cuenta[n] = cuenta.get(n, 0) + 1
    return sorted(cuenta, key=lambda n: (-cuenta[n], n))[0]


def atletas_del_ranking(db: Session, box_id: UUID, sexo: str | None = None) -> dict[UUID, models.User]:
    """Atletas de la cuenta que aparecen en el ranking, por id."""
    consulta = db.query(models.User).filter(
        models.User.box_id == box_id, models.User.role == "athlete", models.User.show_in_ranking == True  # noqa: E712
    )
    if sexo:
        consulta = consulta.filter(models.User.sex == sexo)
    return {u.id: u for u in consulta.all()}


def asignar_posiciones(valores: list[float], mayor_es_mejor: bool = True) -> list[int]:
    """Posición de cada valor (ya ordenados de mejor a peor). Empates comparten posición: 1, 1, 3."""
    posiciones: list[int] = []
    for i, v in enumerate(valores):
        if i > 0 and v == valores[i - 1]:
            posiciones.append(posiciones[-1])
        else:
            posiciones.append(i + 1)
    return posiciones


# ------------------------------------------------------------------ marcas (1RM)

def _mejores_marcas(db: Session, atletas: dict[UUID, models.User]) -> dict[str, dict[UUID, models.PersonalRecord]]:
    """clave normalizada del ejercicio -> atleta -> su mejor marca (los nombres se unifican:
    "Clean & Jerk" y "clean and jerk" son el mismo levantamiento)."""
    if not atletas:
        return {}
    marcas = db.query(models.PersonalRecord).filter(models.PersonalRecord.user_id.in_(list(atletas))).all()
    por_clave: dict[str, dict[UUID, models.PersonalRecord]] = defaultdict(dict)
    for m in marcas:
        if not m.max_weight_kg or m.max_weight_kg <= 0:
            continue
        clave = normalize_exercise_name(m.exercise_name)
        if clave not in _PRINCIPALES:
            continue
        actual = por_clave[clave].get(m.user_id)
        if actual is None or m.max_weight_kg > actual.max_weight_kg:
            por_clave[clave][m.user_id] = m
    return por_clave


def levantamientos(db: Session, box_id: UUID, sexo: str | None = None) -> list[dict]:
    """Los levantamientos principales, siempre en el mismo orden, con cuántos atletas del ranking
    tienen marca en cada uno (puede ser 0)."""
    por_clave = _mejores_marcas(db, atletas_del_ranking(db, box_id, sexo))
    return [
        {"key": clave, "name": nombre, "athletes_count": len(por_clave.get(clave, {}))}
        for clave, nombre in _PRINCIPALES.items()
    ]


def tabla_de_marcas(db: Session, box_id: UUID, clave: str, yo: UUID, sexo: str | None = None) -> list[dict]:
    atletas = atletas_del_ranking(db, box_id, sexo)
    por_atleta = _mejores_marcas(db, atletas).get(normalize_exercise_name(clave), {})  # otros levantamientos: vacío
    ordenadas = sorted(por_atleta.values(), key=lambda m: (-m.max_weight_kg, atletas[m.user_id].full_name.lower()))
    posiciones = asignar_posiciones([m.max_weight_kg for m in ordenadas])
    return [
        {
            "rank": pos,
            "user_id": m.user_id,
            "full_name": atletas[m.user_id].full_name,
            "has_avatar": atletas[m.user_id].has_avatar,
            "weight_kg": m.max_weight_kg,
            "category": atletas[m.user_id].category,
            "is_me": m.user_id == yo,
        }
        for m, pos in zip(ordenadas, posiciones)
    ]


# ------------------------------------------------------------------ WODs

def _nombre_del_wod(sesion: models.Session) -> str | None:
    """El nombre de un WOD es el de su ejercicio del bloque metabólico (lo escribe el atleta)."""
    series = sorted((s for s in sesion.sets if s.block == "metcon" and s.exercise), key=lambda s: s.set_order)
    return series[0].exercise.name.strip() if series else None


def _mejores_sesiones_de_wod(db: Session, atletas: dict[UUID, models.User]) -> dict[tuple[str, str], dict]:
    """(clave del WOD, formato) -> {"name", "por_atleta": {user_id: su mejor sesión}} con las
    sesiones completadas, anotadas a mano por el atleta y con un resultado numérico."""
    if not atletas:
        return {}
    sesiones = (
        db.query(models.Session)
        .join(models.Mesocycle, models.Session.mesocycle_id == models.Mesocycle.id)
        .options(joinedload(models.Session.mesocycle), joinedload(models.Session.sets).joinedload(models.Set.exercise))
        .filter(
            models.Mesocycle.user_id.in_(list(atletas)),
            models.Mesocycle.is_self_managed == True,  # noqa: E712
            models.Mesocycle.is_class_log == False,  # noqa: E712
            models.Session.status == "completed",
            models.Session.wod_format.isnot(None),
        )
        .all()
    )
    intentos: dict[tuple[str, str], dict[UUID, list[models.Session]]] = defaultdict(lambda: defaultdict(list))
    nombres: dict[tuple[str, str], list[str]] = defaultdict(list)
    for sesion in sesiones:
        nombre = _nombre_del_wod(sesion)
        if not nombre or wod_score_value(sesion) is None:
            continue
        clave = (normalize_exercise_name(nombre), sesion.wod_format)
        nombres[clave].append(nombre)
        intentos[clave][sesion.mesocycle.user_id].append(sesion)
    resultado = {}
    for clave, por_atleta in intentos.items():
        mejores = {uid: rank_wod_sessions(lista)[0] for uid, lista in por_atleta.items()}
        resultado[clave] = {"name": nombre_mas_comun(nombres[clave]), "por_atleta": mejores}
    return resultado


def wods(db: Session, box_id: UUID, sexo: str | None = None) -> list[dict]:
    """WODs con resultados de atletas del ranking, los más hechos (y más recientes) primero."""
    atletas = atletas_del_ranking(db, box_id, sexo)
    lista = []
    for (clave, formato), datos in _mejores_sesiones_de_wod(db, atletas).items():
        fechas = [s.scheduled_date for s in datos["por_atleta"].values()]
        lista.append({"key": clave, "name": datos["name"], "wod_format": formato,
                      "athletes_count": len(datos["por_atleta"]), "last_date": max(fechas)})
    lista.sort(key=lambda x: (-x["athletes_count"], -x["last_date"].toordinal(), x["name"].lower()))
    return lista


def tabla_de_wod(db: Session, box_id: UUID, clave: str, formato: str, yo: UUID, sexo: str | None = None) -> list[dict]:
    atletas = atletas_del_ranking(db, box_id, sexo)
    datos = _mejores_sesiones_de_wod(db, atletas).get((normalize_exercise_name(clave), formato))
    if not datos:
        return []
    sesiones = rank_wod_sessions(list(datos["por_atleta"].values()))
    posiciones = asignar_posiciones([wod_score_value(s) for s in sesiones])
    filas = []
    for sesion, pos in zip(sesiones, posiciones):
        usuario = atletas[sesion.mesocycle.user_id]
        filas.append({
            "rank": pos,
            "user_id": usuario.id,
            "full_name": usuario.full_name,
            "has_avatar": usuario.has_avatar,
            "score_label": format_wod_summary(sesion),
            "date": sesion.scheduled_date,
            "category": usuario.category,
            "is_me": usuario.id == yo,
        })
    return filas
