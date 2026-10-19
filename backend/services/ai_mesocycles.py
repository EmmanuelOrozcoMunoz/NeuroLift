"""Generación de entrenamientos con IA: arma lo que se le pide a Gemini y guarda lo que responde.

Separado en pasos pequeños (contexto, fechas, guía por día, llamadas en paralelo y guardado) para
poder probar cada uno sin pasar por HTTP. La limpieza de lo que devuelve la IA (tipos, rangos, WOD,
cargas, fechas) vive en backend/services/ai_salida.py; la llamada real a Gemini está en
backend/ai_agent.py y en las pruebas se sustituye.
"""
import logging
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timedelta
from typing import List
from uuid import UUID

from sqlalchemy import func
from sqlalchemy.orm import Session

from backend import models
from backend.database import SessionLocal
from backend.services.ai_salida import (  # noqa: F401 — se reexportan: las pruebas y otros módulos los importan de aquí
    EjercicioLimpio,
    FORMATOS_CON_TIEMPO,
    FORMATOS_DE_WOD,
    SesionLimpia,
    emparejar_fechas,
    fecha_de_texto,
    limpiar_ejercicio,
    limpiar_sesion,
    sesiones_de_respuesta,
    wod_limpio,
)
from backend.services.plans import PLAN_EPOCH
from backend.services.prs import get_athlete_prs

logger = logging.getLogger(__name__)

_NOMBRE_DIA_SEMANA = {0: "Lunes", 1: "Martes", 2: "Miércoles", 3: "Jueves", 4: "Viernes", 5: "Sábado", 6: "Domingo"}

# 3 semanas por chunk: un mesociclo corto (3-4 semanas, el caso más común) queda en UNA sola
# llamada a Gemini sin acercarse al límite de tokens de salida del modelo.
SEMANAS_POR_CHUNK = 3
# Veces que se pide una tanda: si la IA falla o se salta fechas se reintenta UNA vez antes de rendirse.
INTENTOS_POR_CHUNK = 2


def _ejercicio(db: Session, nombre: str, categoria: str) -> models.Exercise:
    """El ejercicio del catálogo con ese nombre (sin distinguir mayúsculas: "back squat" y "Back
    Squat" son el mismo) o uno nuevo."""
    ejercicio = db.query(models.Exercise).filter(func.lower(models.Exercise.name) == nombre.lower()).first()
    if not ejercicio:
        ejercicio = models.Exercise(name=nombre, category=categoria)
        db.add(ejercicio)
        db.flush()
    return ejercicio


# ------------------------------------------------------------ guardar una sesión ya limpia

def aplicar_wod(sesion: models.Session, wod) -> bool:
    """Configura en la sesión la plantilla de WOD (formato, tiempo límite, descripción) a partir de
    lo que devolvió la IA. Devuelve si había un WOD usable."""
    datos = wod_limpio(wod)
    if datos is None:
        return False
    sesion.wod_format = datos["format"]
    sesion.wod_time_cap_seconds = datos["time_cap_seconds"]
    sesion.wod_notes = datos["notes"]
    return True


def _crear_sesion(
    db: Session, meso: models.Mesocycle, limpia: SesionLimpia, duracion: int | None, categoria: str = "General"
) -> models.Session:
    """Crea la sesión y sus series en la base a partir de una sesión ya limpia (sin commit). Usa todo
    lo que tiene una sesión armada a mano: calentamiento en texto, orden de bloques, WOD, nota por
    ejercicio y series una por una (rampas)."""
    sesion = models.Session(
        mesocycle_id=meso.id,
        scheduled_date=limpia.fecha,
        athlete_notes=limpia.notas_atleta,
        status="pending",
        duration_minutes=duracion,
        warmup_notes=limpia.calentamiento,
        block_order=limpia.orden_de_bloques,
    )
    if limpia.wod:
        sesion.wod_format = limpia.wod["format"]
        sesion.wod_time_cap_seconds = limpia.wod["time_cap_seconds"]
        sesion.wod_notes = limpia.wod["notes"]
    db.add(sesion)
    db.flush()

    orden = 1
    for ej in limpia.ejercicios:
        ejercicio = _ejercicio(db, ej.nombre, categoria)
        for fila in ej.filas_a_guardar():
            db.add(models.Set(
                session_id=sesion.id,
                exercise_id=ejercicio.id,
                set_order=orden,
                prescribed_reps=fila.reps,
                rpe=ej.rpe,
                prescribed_weight=fila.peso,
                prescribed_percentage=fila.porcentaje,
                reference_exercise=ej.referencia if fila.porcentaje is not None else None,
                block=ej.bloque,
                coach_note=ej.nota,
            ))
            orden += 1
    return sesion


# ------------------------------------------------------------ una sesión suelta

def guardar_sesion_ia(db: Session, meso: models.Mesocycle, rutina_ai: dict) -> models.Session:
    """Guarda como sesión de hoy la rutina que devolvió la IA (sin hacer commit). Pasa por la misma
    limpieza que un mesociclo: antes un ejercicio sin nombre rompía la petición y se ignoraban las
    series de cada ejercicio."""
    # Sin atleta (la programación de una clase) no hay marcas: los % se conservan como están
    prs = get_athlete_prs(db, meso.user_id) if meso.user_id else None
    limpia = limpiar_sesion(rutina_ai if isinstance(rutina_ai, dict) else {}, date.today(), prs)
    if limpia.advertencias:
        logger.info("Sesión suelta con IA: %s", "; ".join(limpia.advertencias))
    return _crear_sesion(db, meso, limpia, None, "AI Generated")


# ------------------------------------------------------------ mesociclo completo

def contexto_del_atleta(db: Session, atleta: models.User, peticion: str) -> str:
    """Peso corporal + marcas (1RM) + lo que pidió el coach: el "súper contexto" para la IA."""
    marcas = db.query(models.PersonalRecord).filter(models.PersonalRecord.user_id == atleta.id).all()
    texto_marcas = ", ".join(f"{pr.exercise_name}: {pr.max_weight_kg}kg" for pr in marcas) if marcas else "Sin marcas registradas."
    peso_corporal = f"{atleta.body_weight}kg" if atleta.body_weight else "No registrado"
    return f"Peso corporal: {peso_corporal}. Marcas (1RM): {texto_marcas}. Peticiones: {peticion}"


def fechas_de_entrenamiento(start_date: date, weeks_count: int, training_days: List[int]) -> List[str]:
    """Todas las fechas (YYYY-MM-DD) del mesociclo que caen en un día de entrenamiento."""
    fechas = (start_date + timedelta(days=i) for i in range(weeks_count * 7))
    return [f.strftime("%Y-%m-%d") for f in fechas if f.weekday() in training_days]


def guia_por_fecha(fechas: List[str], day_focus: dict[int, str] | None) -> str:
    """Guía del coach por día de la semana, atada a la FECHA EXACTA: que la IA calcule sola a qué
    día de la semana corresponde una fecha es donde falla en la práctica (se vieron casos reales
    donde invirtió la guía de lunes y miércoles)."""
    if not day_focus:
        return ""
    lineas = []
    for fecha_str in fechas:
        dia = datetime.strptime(fecha_str, "%Y-%m-%d").weekday()
        if dia in day_focus:
            lineas.append(f"- {fecha_str} ({_NOMBRE_DIA_SEMANA[dia]}): {day_focus[dia]}")
    if not lineas:
        return ""
    return "GUÍA POR FECHA (para estas fechas exactas, en este orden):\n" + "\n".join(lineas)


def especificar_chunks(
    todas_las_fechas: List[str], weeks_count: int, sesiones_por_semana: int, day_focus: dict[int, str] | None
) -> list[tuple[int, int, List[str], str]]:
    """Parte el mesociclo en tandas de SEMANAS_POR_CHUNK semanas: (semana_inicio, semana_fin, fechas, guía)."""
    sesiones_por_chunk = SEMANAS_POR_CHUNK * sesiones_por_semana
    specs = []
    for start in range(1, weeks_count + 1, SEMANAS_POR_CHUNK):
        end = min(start + SEMANAS_POR_CHUNK - 1, weeks_count)
        idx_inicio = (start - 1) * sesiones_por_semana
        fechas_del_chunk = todas_las_fechas[idx_inicio:idx_inicio + sesiones_por_chunk]
        specs.append((start, end, fechas_del_chunk, guia_por_fecha(fechas_del_chunk, day_focus)))
    return specs


def guardar_rutinas(
    db: Session, meso: models.Mesocycle, rutinas: List[dict], start_date: date, duracion: int | None, prs: dict | None
) -> list[str]:
    """Guarda las sesiones y series de todas las respuestas de la IA (sin commit) y devuelve los
    avisos para el coach (cargas descartadas, ejercicios ilegibles...). Secuencial a propósito: una
    Session de SQLAlchemy no es segura para escribir desde varios hilos.

    `prs` son las marcas del atleta; `None` = no hay atleta (plantilla de plan o clase): los % se
    conservan y no se acepta ningún kg fijo de un levantamiento de barra."""
    por_texto: dict[str, list[date]] = {}   # aviso -> fechas en las que pasó (en orden de aparición)
    for rutina_ai in rutinas:
        sesiones = sesiones_de_respuesta(rutina_ai)
        fechas_pedidas = rutina_ai.get("_fechas") if isinstance(rutina_ai, dict) else None
        if fechas_pedidas:
            # La IA no decide cuándo se entrena, lo decide el calendario del coach
            pares = [(date.fromisoformat(f), s) for f, s in emparejar_fechas(sesiones, fechas_pedidas)[0]]
        else:
            pares = [(date.fromisoformat(fecha_de_texto(s.get("scheduled_date")) or start_date.isoformat()), s) for s in sesiones]

        for fecha, sesion_data in pares:
            limpia = limpiar_sesion(sesion_data, fecha, prs)
            _crear_sesion(db, meso, limpia, duracion)
            for aviso in limpia.advertencias:
                por_texto.setdefault(aviso, []).append(fecha)

    # El mismo problema en 12 sesiones es UN aviso para el coach, no 12
    return [
        f"{fechas[0]}: {texto}" if len(fechas) == 1 else f"{texto} (en {len(fechas)} sesiones)"
        for texto, fechas in por_texto.items()
    ]


def _sumar_uso(rutinas: List[dict]) -> dict[str, int]:
    """Los tokens que gastó la generación (lo que cobra Gemini), sumados por todas las tandas."""
    total = {"llamadas": 0, "tokens_prompt": 0, "tokens_salida": 0, "tokens_pensamiento": 0}
    for rutina in rutinas:
        uso = rutina.get("_uso") if isinstance(rutina, dict) else None
        if not isinstance(uso, dict):
            continue
        total["llamadas"] += 1
        total["tokens_prompt"] += int(uso.get("tokens_prompt") or 0)
        total["tokens_salida"] += int(uso.get("tokens_salida") or 0)
        total["tokens_pensamiento"] += int(uso.get("tokens_pensamiento") or 0)
    return total


def pedir_rutinas(
    nombre: str,
    discipline: str,
    contexto: str,
    fechas: List[str],
    weeks_count: int,
    sesiones_por_semana: int,
    session_duration_minutes: int | None,
    day_focus: dict[int, str] | None,
) -> List[dict]:
    """Pide a Gemini las sesiones de todas las fechas, por tandas de SEMANAS_POR_CHUNK semanas y en
    paralelo (cada tanda es una llamada HTTP independiente: tarda lo que la más lenta, no la suma).

    Cada tanda se valida: si la IA falla o no devuelve alguna de las fechas pedidas se reintenta UNA
    vez, y si sigue mal se rechaza toda la generación. Antes una tanda fallida (`{"error": ...}`)
    pasaba como vacía y se guardaba un mesociclo al que le faltaban semanas, sin avisar."""
    # Se importan aquí (y no arriba) para que las pruebas puedan sustituir la llamada a Gemini.
    from backend.ai_agent import generate_mesocycle_chunk
    from backend.knowledge_search import search_knowledge_base

    # Una sola vez para todo el mesociclo: discipline/context no cambian entre chunks.
    literatura = search_knowledge_base(f"{discipline} - {contexto}")
    specs = especificar_chunks(fechas, weeks_count, sesiones_por_semana, day_focus)

    def pedir_chunk(spec):
        start, end, fechas_del_chunk, guia = spec
        problema = "la IA no respondió"
        for _ in range(INTENTOS_POR_CHUNK):
            respuesta = generate_mesocycle_chunk(
                athlete_name=nombre,
                discipline=discipline,
                experience_notes=contexto,
                start_week=start,
                end_week=end,
                session_dates=fechas_del_chunk,
                session_duration_minutes=session_duration_minutes,
                literatura_cientifica=literatura,
                day_focus_text=guia,
            )
            if not isinstance(respuesta, dict) or respuesta.get("error"):
                problema = (respuesta or {}).get("error") if isinstance(respuesta, dict) else None
                problema = problema or "la IA devolvió una respuesta inválida"
                continue
            _, faltantes = emparejar_fechas(sesiones_de_respuesta(respuesta), fechas_del_chunk)
            if faltantes:
                problema = f"la IA no devolvió las sesiones de {', '.join(faltantes)}"
                continue
            return {**respuesta, "_fechas": fechas_del_chunk}
        raise RuntimeError(f"Semanas {start}-{end}: {problema}")

    # executor.map conserva el orden, así que las semanas se guardan en orden.
    with ThreadPoolExecutor(max_workers=len(specs)) as executor:
        return list(executor.map(pedir_chunk, specs))


def construir_mesociclo_inteligente(
    db: Session,
    atleta: models.User,
    name: str,
    discipline: str,
    start_date: date,
    weeks_count: int,
    training_days: List[int],
    context: str,
    group_id: UUID | None = None,
    session_duration_minutes: int | None = None,
    day_focus: dict[int, str] | None = None,
) -> dict:
    """Genera con IA un mesociclo completo para UN atleta. Hace commit propio; si algo falla hace
    rollback y lanza RuntimeError (el llamador decide cómo responder). Devuelve el id, los avisos
    para el coach y los tokens gastados."""
    fechas = fechas_de_entrenamiento(start_date, weeks_count, training_days)
    if not fechas:
        raise RuntimeError("Selecciona al menos un día de entrenamiento.")

    meso = models.Mesocycle(user_id=atleta.id, group_id=group_id, name=name, discipline=discipline, start_date=start_date)
    db.add(meso)
    db.flush()

    contexto = contexto_del_atleta(db, atleta, context)
    # Para resolver los porcentajes que devuelva la IA a kg reales con las marcas de hoy.
    prs = get_athlete_prs(db, atleta.id)

    try:
        rutinas = pedir_rutinas(
            atleta.full_name, discipline, contexto, fechas, weeks_count, len(training_days),
            session_duration_minutes, day_focus,
        )
        avisos = guardar_rutinas(db, meso, rutinas, start_date, session_duration_minutes, prs)
        meso.end_date = datetime.strptime(fechas[-1], "%Y-%m-%d").date()
        db.commit()
        uso = _sumar_uso(rutinas)
        logger.info("Mesociclo con IA %s: %s; avisos=%d", meso.id, uso, len(avisos))
        return {"mesocycle_id": str(meso.id), "advertencias": avisos, "uso": uso}

    except Exception as e:
        db.rollback()
        raise RuntimeError(str(e)) from e


def construir_mesociclo_en_su_propia_sesion(
    atleta_id: UUID,
    full_name: str,
    name: str,
    discipline: str,
    start_date: date,
    weeks_count: int,
    training_days: List[int],
    context: str,
    group_id: UUID,
    session_duration_minutes: int | None,
    day_focus: dict[int, str] | None,
) -> dict:
    """Para correr en un hilo del pool: una Session de SQLAlchemy NO es segura para compartir
    entre hilos, así que cada atleta usa la suya (se abre y se cierra aquí)."""
    db = SessionLocal()
    try:
        atleta = db.query(models.User).filter(models.User.id == atleta_id).first()
        if not atleta:
            return {"user_id": str(atleta_id), "full_name": full_name, "status": "error", "detail": "Atleta no encontrado"}
        resultado = construir_mesociclo_inteligente(
            db, atleta, name, discipline, start_date, weeks_count, training_days, context,
            group_id=group_id, session_duration_minutes=session_duration_minutes, day_focus=day_focus,
        )
        return {"user_id": str(atleta_id), "full_name": full_name, "status": "success", **resultado}
    except RuntimeError as e:
        return {"user_id": str(atleta_id), "full_name": full_name, "status": "error", "detail": str(e)}
    finally:
        db.close()


# Lo que se le dice a la IA al armar una plantilla: no hay un atleta concreto, así que no hay marcas.
_CONTEXTO_PLANTILLA = (
    "Esto es una PLANTILLA reutilizable para varios atletas, no para uno solo: no hay marcas "
    "individuales. Prescribe las cargas de fuerza y weightlifting SIEMPRE en porcentaje de 1RM "
    "(prescribed_percentage) con su reference_exercise, y no uses pesos fijos en kg; la app "
    "calculará los kg de cada atleta con sus propias marcas al asignarla. Como reference_exercise "
    "usa nombres estándar: Back Squat, Front Squat, Snatch, Clean & Jerk, Deadlift, Bench Press, "
    "Overhead Press. Peticiones del coach: "
)


def construir_plantilla_con_ia(
    db: Session,
    coach: models.User,
    name: str,
    description: str,
    discipline: str,
    level: str,
    weeks_count: int,
    training_days: List[int],
    context: str,
    session_duration_minutes: int | None = None,
    day_focus: dict[int, str] | None = None,
) -> models.Mesocycle:
    """Genera con IA UNA plantilla (plan en borrador del coach) con las cargas en % de 1RM: una
    sola generación sirve para todos los grupos y atletas a los que se asigne después. Hace commit
    propio; si algo falla hace rollback y lanza RuntimeError."""
    # Días relativos al primer día de entrenamiento (igual que un plan creado a mano): el patrón
    # semanal se conserva sin importar en qué día de la semana se asigne.
    fechas = fechas_de_entrenamiento(PLAN_EPOCH, weeks_count, training_days)
    if not fechas:
        raise RuntimeError("Selecciona al menos un día de entrenamiento.")

    plan = models.Mesocycle(
        user_id=None,
        is_template=True,
        is_published=False,
        created_by_coach_id=coach.id,
        box_id=coach.box_id,
        plan_visibility="box",
        name=name,
        description=description,
        discipline=discipline,
        level=level,
        start_date=PLAN_EPOCH,
    )
    db.add(plan)
    db.flush()

    try:
        rutinas = pedir_rutinas(
            "el grupo", discipline, _CONTEXTO_PLANTILLA + context, fechas, weeks_count, len(training_days),
            session_duration_minutes, day_focus,
        )
        # prs=None: una plantilla no tiene atleta, así que no hay marcas con qué respaldar un kg fijo
        avisos = guardar_rutinas(db, plan, rutinas, PLAN_EPOCH, session_duration_minutes, None)
        db.flush()

        base = (datetime.strptime(fechas[0], "%Y-%m-%d").date() - PLAN_EPOCH).days
        sesiones = db.query(models.Session).filter(models.Session.mesocycle_id == plan.id).all()
        for sesion in sesiones:
            offset = max(0, (sesion.scheduled_date - PLAN_EPOCH).days - base)
            sesion.day_offset = offset
            sesion.scheduled_date = PLAN_EPOCH + timedelta(days=offset)
        plan.end_date = PLAN_EPOCH + timedelta(days=max((s.day_offset for s in sesiones), default=0))
        db.commit()
        db.refresh(plan)
        logger.info("Plantilla con IA %s: %s; avisos=%d", plan.id, _sumar_uso(rutinas), len(avisos))
        return plan
    except Exception as e:
        db.rollback()
        raise RuntimeError(str(e)) from e
