"""Generación de entrenamientos con IA: arma lo que se le pide a Gemini y guarda lo que responde.

Separado en pasos pequeños (contexto, fechas, guía por día, llamadas en paralelo, limpieza de
cada ejercicio y guardado) para poder probar cada uno sin pasar por HTTP. La llamada real a
Gemini está en backend/ai_agent.py y en las pruebas se sustituye.
"""
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import List
from uuid import UUID

from sqlalchemy.orm import Session

from backend import models
from backend.sanitize import clean_multiline, clean_text
from backend.database import SessionLocal
from backend.services.exercises import clean_ai_block
from backend.services.plans import PLAN_EPOCH
from backend.services.prs import get_athlete_prs, normalize_exercise_name, resolve_weight_from_percentage

_NOMBRE_DIA_SEMANA = {0: "Lunes", 1: "Martes", 2: "Miércoles", 3: "Jueves", 4: "Viernes", 5: "Sábado", 6: "Domingo"}

# 3 semanas por chunk: un mesociclo corto (3-4 semanas, el caso más común) queda en UNA sola
# llamada a Gemini sin acercarse al límite de tokens de salida del modelo.
SEMANAS_POR_CHUNK = 3


@dataclass
class EjercicioLimpio:
    """Un ejercicio de la respuesta de la IA, ya con tipos y valores validados."""
    nombre: str
    series: int
    reps: int
    rpe: int | None
    peso: float | None
    porcentaje: float | None
    referencia: str | None
    bloque: str | None


def _ejercicio(db: Session, nombre: str, categoria: str) -> models.Exercise:
    ejercicio = db.query(models.Exercise).filter(models.Exercise.name == nombre).first()
    if not ejercicio:
        ejercicio = models.Exercise(name=nombre, category=categoria)
        db.add(ejercicio)
        db.flush()
    return ejercicio


def _a_float(valor) -> float | None:
    if valor is None:
        return None
    try:
        return float(valor)
    except (ValueError, TypeError):
        return None


# ------------------------------------------------------------ el WOD de una sesión

# Formatos que la IA puede devolver y cuáles llevan tiempo límite / duración (el temporizador del
# atleta lo usa). Coinciden con backend/schemas/common.py:FormatoWod y web/src/lib/wod.ts.
FORMATOS_DE_WOD = ("for_time", "amrap", "amrap_reps", "emom", "tabata", "1rm", "calories", "distance", "watts")
FORMATOS_CON_TIEMPO = ("for_time", "amrap", "amrap_reps", "emom", "calories", "distance", "watts")
_MAX_NOTAS_WOD = 2000
_MAX_MINUTOS_WOD = 180


def wod_limpio(wod) -> dict | None:
    """Valida el WOD que devolvió la IA y lo deja como lo guarda la plantilla de WOD de la app:
    {"format", "time_cap_seconds", "notes"}. Devuelve None si no hay nada usable (la IA a veces
    devuelve null, un texto o valores inventados: mejor sin WOD que uno mal configurado)."""
    if not isinstance(wod, dict):
        return None
    formato = wod.get("format")
    formato = formato.strip().lower() if isinstance(formato, str) else None
    if formato not in FORMATOS_DE_WOD:
        formato = None

    segundos = None
    if formato in FORMATOS_CON_TIEMPO:
        minutos = _a_float(wod.get("time_cap_minutes"))
        if minutos is not None and 0 < minutos <= _MAX_MINUTOS_WOD:
            segundos = int(round(minutos * 60))

    # El nombre va en una línea; la descripción conserva sus saltos de línea (un WOD de varias
    # líneas se queda así). Ambos pasan por el mismo saneo que el texto que escribe un coach.
    partes = [
        limpio
        for clave in ("name", "description")
        if isinstance(wod.get(clave), str)
        and (limpio := clean_multiline(wod.get(clave)) if clave == "description" else clean_text(wod.get(clave)))
    ]
    notas = "\n".join(partes)[:_MAX_NOTAS_WOD] or None

    if formato is None and notas is None:
        return None
    return {"format": formato, "time_cap_seconds": segundos, "notes": notas}


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


# ------------------------------------------------------------ una sesión suelta

def guardar_sesion_ia(db: Session, meso: models.Mesocycle, rutina_ai: dict) -> models.Session:
    """Guarda como sesión de hoy la rutina que devolvió la IA (sin hacer commit)."""
    sesion = models.Session(
        mesocycle_id=meso.id,
        scheduled_date=date.today(),
        athlete_notes=rutina_ai.get("athlete_notes", ""),
        status="pending",
    )
    aplicar_wod(sesion, rutina_ai.get("wod"))
    db.add(sesion)
    db.flush()

    for orden, ex_data in enumerate(rutina_ai.get("exercises", []), start=1):
        ejercicio = _ejercicio(db, ex_data["exercise_name"], "AI Generated")
        db.add(models.Set(
            session_id=sesion.id,
            exercise_id=ejercicio.id,
            set_order=orden,
            prescribed_reps=ex_data["prescribed_reps"],
            rpe=ex_data["rpe_target"],
            block=clean_ai_block(ex_data.get("block")),
        ))
    return sesion


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


def limpiar_ejercicio(ej_data: dict, prs: dict) -> EjercicioLimpio:
    """Valida los tipos que devuelve la IA y resuelve la carga con las marcas ACTUALES del atleta."""
    nombre = ej_data.get("exercise_name", "Ejercicio Desconocido")

    rpe_raw = ej_data.get("rpe_target") or ej_data.get("rpe")
    rpe = int(float(rpe_raw)) if rpe_raw is not None else None

    peso = _a_float(
        ej_data.get("prescribed_weight") or ej_data.get("weight_kg") or ej_data.get("weight") or ej_data.get("target_weight")
    )
    porcentaje = _a_float(ej_data.get("prescribed_percentage"))
    referencia = ej_data.get("reference_exercise") or nombre

    if porcentaje is not None:
        # La IA sí dio un %: recalcula el kg a partir de la marca ACTUAL del atleta en vez de
        # confiar en un número que ella misma haya calculado (así se mantiene "vivo").
        peso = resolve_weight_from_percentage(porcentaje, peso, referencia, prs)
    elif peso is not None:
        # La IA ignoró la instrucción y dio un kg fijo (pasa seguido): si coincide con una marca
        # de ESTE atleta para el mismo ejercicio, se deriva el % para que quede igual de "vivo".
        pr_valor = prs.get(normalize_exercise_name(nombre))
        if pr_valor:
            porcentaje = round(peso / pr_valor * 100)
            referencia = nombre

    return EjercicioLimpio(
        nombre=nombre,
        series=ej_data.get("prescribed_sets", 1),
        reps=ej_data.get("prescribed_reps", 1),
        rpe=rpe,
        peso=peso,
        porcentaje=porcentaje,
        referencia=referencia if porcentaje is not None else None,
        bloque=clean_ai_block(ej_data.get("block")),
    )


def guardar_rutinas(
    db: Session, meso: models.Mesocycle, rutinas: List[dict], start_date: date, duracion: int | None, prs: dict
) -> None:
    """Guarda las sesiones y series de todas las respuestas de la IA (sin commit). Secuencial a
    propósito: una Session de SQLAlchemy no es segura para escribir desde varios hilos."""
    for rutina_ai in rutinas:
        for semana in rutina_ai.get("weeks", []):
            for sesion_data in semana.get("sessions", []):
                fecha_str = sesion_data.get("scheduled_date")
                fecha_real = datetime.strptime(fecha_str, "%Y-%m-%d").date() if fecha_str else start_date
                sesion = models.Session(
                    mesocycle_id=meso.id,
                    scheduled_date=fecha_real,
                    athlete_notes=sesion_data.get("athlete_notes", ""),
                    status="pending",
                    duration_minutes=duracion,
                )
                aplicar_wod(sesion, sesion_data.get("wod"))
                db.add(sesion)
                db.flush()

                orden = 1
                for ej_data in sesion_data.get("exercises", []):
                    ej = limpiar_ejercicio(ej_data, prs)
                    ejercicio = _ejercicio(db, ej.nombre, "General")
                    for _ in range(ej.series):
                        db.add(models.Set(
                            session_id=sesion.id,
                            exercise_id=ejercicio.id,
                            set_order=orden,
                            prescribed_reps=ej.reps,
                            rpe=ej.rpe,
                            prescribed_weight=ej.peso,
                            prescribed_percentage=ej.porcentaje,
                            reference_exercise=ej.referencia,
                            block=ej.bloque,
                        ))
                        orden += 1


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
    paralelo (cada tanda es una llamada HTTP independiente: tarda lo que la más lenta, no la suma)."""
    # Se importan aquí (y no arriba) para que las pruebas puedan sustituir la llamada a Gemini.
    from backend.ai_agent import generate_mesocycle_chunk
    from backend.knowledge_search import search_knowledge_base

    # Una sola vez para todo el mesociclo: discipline/context no cambian entre chunks.
    literatura = search_knowledge_base(f"{discipline} - {contexto}")
    specs = especificar_chunks(fechas, weeks_count, sesiones_por_semana, day_focus)

    def pedir_chunk(spec):
        start, end, fechas_del_chunk, guia = spec
        return generate_mesocycle_chunk(
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
    rollback y lanza RuntimeError (el llamador decide cómo responder)."""
    meso = models.Mesocycle(user_id=atleta.id, group_id=group_id, name=name, discipline=discipline, start_date=start_date)
    db.add(meso)
    db.flush()

    contexto = contexto_del_atleta(db, atleta, context)
    # Para resolver los porcentajes que devuelva la IA a kg reales con las marcas de hoy.
    prs = get_athlete_prs(db, atleta.id)
    fechas = fechas_de_entrenamiento(start_date, weeks_count, training_days)

    try:
        rutinas = pedir_rutinas(
            atleta.full_name, discipline, contexto, fechas, weeks_count, len(training_days),
            session_duration_minutes, day_focus,
        )
        guardar_rutinas(db, meso, rutinas, start_date, session_duration_minutes, prs)
        meso.end_date = datetime.strptime(fechas[-1], "%Y-%m-%d").date()
        db.commit()
        return {"mesocycle_id": str(meso.id)}

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
        guardar_rutinas(db, plan, rutinas, PLAN_EPOCH, session_duration_minutes, {})
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
        return plan
    except Exception as e:
        db.rollback()
        raise RuntimeError(str(e)) from e
