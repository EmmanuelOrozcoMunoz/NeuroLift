"""Helpers alrededor de las marcas (1RM) de un atleta: sincronía con Fit Level, y resolución
de carga prescrita como % de 1RM a kg reales."""
import re
import unicodedata
from uuid import UUID

from sqlalchemy.orm import Session

from backend import models

# Los 4 levantamientos de halterofilia del calculador de Fit Level son, ni más ni menos, un
# 1RM — lo mismo que ya representa una fila de PersonalRecord. Estos mapeos mantienen ambas
# tablas en sincronía sin importar por cuál pantalla se haya registrado (ver users.py y
# fitness.py, ambos los usan en direcciones opuestas).
FIT_LEVEL_LIFT_TO_PR_NAME = {
    "snatch_kg": "Snatch",
    "clean_jerk_kg": "Clean & Jerk",
    "back_squat_kg": "Back Squat",
    "deadlift_kg": "Deadlift",
}

# Nombres que la gente escribe distinto para el MISMO levantamiento (en español, abreviados...).
# La llave y el valor ya van normalizados (ver normalize_exercise_name). Solo sinónimos
# inequívocos: "press" a secas NO se mapea, porque puede ser strict, push o bench.
_ALIASES = {
    "c and j": "clean and jerk",
    "cj": "clean and jerk",
    "cyj": "clean and jerk",
    "dos tiempos": "clean and jerk",
    "cargada y envion": "clean and jerk",
    "arranque": "snatch",
    "sentadilla": "back squat",
    "sentadilla trasera": "back squat",
    "sentadilla atras": "back squat",
    "back squats": "back squat",
    "sentadilla frontal": "front squat",
    "sentadilla adelante": "front squat",
    "sentadilla overhead": "overhead squat",
    "peso muerto": "deadlift",
    "peso muerto convencional": "deadlift",
    "press militar": "strict press",
    "press estricto": "strict press",
    "shoulder press": "strict press",
    "press de banca": "bench press",
    "press banca": "bench press",
    "banca": "bench press",
    "cargada": "clean",
    "cargada de potencia": "power clean",
    "arranque de potencia": "power snatch",
    "jerk dividido": "split jerk",
}


def normalize_exercise_name(name: str | None) -> str:
    """Forma canónica de un nombre de ejercicio para COMPARAR (nunca para mostrar): sin tildes,
    minúsculas, "&"/"y" como "and", sin signos, espacios colapsados y sinónimos unificados. Así
    "Clean and jerk", "Clean & Jerk", "clean & jerk " y "Dos tiempos" son el mismo levantamiento.
    La usan todas las búsquedas de marcas (1RM) por nombre."""
    if not name:
        return ""
    sin_tildes = "".join(c for c in unicodedata.normalize("NFKD", name) if not unicodedata.combining(c))
    texto = sin_tildes.lower().replace("&", " and ")
    texto = re.sub(r"[^a-z0-9]+", " ", texto)
    texto = " ".join("and" if palabra == "y" else palabra for palabra in texto.split())  # "Clean y Jerk"
    texto = re.sub(r"\s+", " ", texto).strip()
    return _ALIASES.get(texto, texto)


PR_NAME_TO_FIT_LEVEL_LIFT = {normalize_exercise_name(name): key for key, name in FIT_LEVEL_LIFT_TO_PR_NAME.items()}


def fit_level_lift_for(exercise_name: str) -> str | None:
    """Métrica del Fit Level que corresponde a esta marca (si es uno de sus 4 levantamientos)."""
    return PR_NAME_TO_FIT_LEVEL_LIFT.get(normalize_exercise_name(exercise_name))


def find_personal_record(db: Session, user_id: UUID, exercise_name: str) -> models.PersonalRecord | None:
    """La marca de este atleta para ese levantamiento, aunque esté escrita distinto."""
    buscado = normalize_exercise_name(exercise_name)
    for pr in db.query(models.PersonalRecord).filter(models.PersonalRecord.user_id == user_id).all():
        if normalize_exercise_name(pr.exercise_name) == buscado:
            return pr
    return None


def upsert_personal_record_by_name(db: Session, user_id: UUID, exercise_name: str, max_weight_kg: float) -> None:
    """Como el endpoint POST /users/{id}/records/ (users.py), pero para uso interno (sync con
    Fit Level, en fitness.py): busca por nombre normalizado, para no crear un duplicado si el
    ejercicio ya existía escrito distinto (p. ej. "back squat", "Clean and jerk" vs "Clean & Jerk")."""
    existente = find_personal_record(db, user_id, exercise_name)
    if existente:
        existente.max_weight_kg = max_weight_kg
    else:
        db.add(models.PersonalRecord(user_id=user_id, exercise_name=exercise_name, max_weight_kg=max_weight_kg))


def get_athlete_prs(db: Session, user_id: UUID) -> dict[str, float]:
    """Marcas (1RM) de un atleta, con la llave normalizada (ver normalize_exercise_name) para
    encontrarlas aunque el nombre esté escrito distinto — ver resolve_weight_from_percentage.
    Usado por sets.py, groups.py, plans.py, classes.py y ai.py: cualquier flujo que prescriba
    carga en % de 1RM. Si hay dos marcas del mismo levantamiento escritas distinto, gana la mayor."""
    prs: dict[str, float] = {}
    for pr in db.query(models.PersonalRecord).filter(models.PersonalRecord.user_id == user_id).all():
        llave = normalize_exercise_name(pr.exercise_name)
        prs[llave] = max(prs.get(llave, 0), pr.max_weight_kg or 0)
    return prs


def resolve_weight_from_percentage(
    porcentaje: float | None, peso_fijo: float | None, referencia: str, prs: dict[str, float]
) -> float | None:
    """Convierte un % de 1RM a kg usando las marcas del atleta (ver get_athlete_prs), redondeando
    a múltiplos de 2.5kg. Si no viene porcentaje, se respeta el peso fijo tal cual; si viene
    porcentaje pero no hay marca de referencia, queda sin peso (el atleta o su coach lo ajusta a
    mano) — quien llama es responsable de avisar que esa carga quedó pendiente."""
    if porcentaje is None:
        return peso_fijo
    pr = prs.get(normalize_exercise_name(referencia))
    if not pr:
        return None
    return round((pr * porcentaje / 100) / 2.5) * 2.5


def actualizar_cargas_por_porcentaje(series, prs: dict[str, float]) -> bool:
    """Recalcula en kg las series prescritas por % de 1RM con las marcas VIGENTES y deja el valor
    en la serie (el llamador hace commit). Las series ya anotadas no se tocan (lo que se levantó
    contra esa prescripción no debe moverse) y, si no hay marca de referencia, se conserva el kg
    que tenía. Devuelve si cambió alguna."""
    cambio = False
    for serie in series:
        if serie.prescribed_percentage is None or serie.actual_reps is not None:
            continue
        # "1RM de referencia" vacío significa "el mismo ejercicio" (como al crear/editar la serie)
        referencia = serie.reference_exercise or (serie.exercise.name if serie.exercise else None)
        if not referencia:
            continue
        nuevo = resolve_weight_from_percentage(serie.prescribed_percentage, serie.prescribed_weight, referencia, prs)
        if nuevo is not None and nuevo != serie.prescribed_weight:
            serie.prescribed_weight = nuevo
            cambio = True
    return cambio
