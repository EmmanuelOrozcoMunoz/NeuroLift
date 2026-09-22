from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, datetime, timedelta
from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from backend import models, schemas
from backend.core.security import _ip_and_user_key, ensure_owner_or_coach, limiter, require_coach
from backend.database import SessionLocal, get_db
from backend.routers.exercise_helpers import clean_ai_block
from backend.routers.group_helpers import get_owned_group
from backend.routers.pr_helpers import get_athlete_prs, resolve_weight_from_percentage

router = APIRouter(prefix="/ai", tags=["ai"])


@router.post("/generate-session/")
@limiter.limit("20/hour", key_func=_ip_and_user_key)
def generate_and_save_session(
    request: Request,
    req: schemas.AIGenerateRequest, db: Session = Depends(get_db), current_user: models.User = Depends(require_coach)
):
    meso = db.query(models.Mesocycle).filter(models.Mesocycle.id == req.mesocycle_id).first()
    if not meso:
        raise HTTPException(status_code=404, detail="Mesociclo no encontrado")
    ensure_owner_or_coach(db, meso.user_id, current_user)

    from backend.ai_agent import generate_workout_session
    rutina_ai = generate_workout_session(
        athlete_name=meso.user.full_name,
        discipline=meso.discipline,
        experience_notes=req.context,
    )

    if "error" in rutina_ai:
        raise HTTPException(status_code=500, detail=rutina_ai["error"])

    nueva_sesion = models.Session(
        mesocycle_id=meso.id,
        scheduled_date=date.today(),
        athlete_notes=rutina_ai.get("athlete_notes", ""),
        status="pending",
    )
    db.add(nueva_sesion)
    db.flush()

    orden = 1
    for ex_data in rutina_ai.get("exercises", []):
        ejercicio = db.query(models.Exercise).filter(models.Exercise.name == ex_data["exercise_name"]).first()
        if not ejercicio:
            ejercicio = models.Exercise(name=ex_data["exercise_name"], category="AI Generated")
            db.add(ejercicio)
            db.flush()

        nuevo_set = models.Set(
            session_id=nueva_sesion.id,
            exercise_id=ejercicio.id,
            set_order=orden,
            prescribed_reps=ex_data["prescribed_reps"],
            rpe=ex_data["rpe_target"],
            block=clean_ai_block(ex_data.get("block")),
        )
        db.add(nuevo_set)
        orden += 1

    db.commit()
    db.refresh(nueva_sesion)

    return {"status": "success", "session_focus": rutina_ai.get("session_focus"), "session_id": nueva_sesion.id}


_NOMBRE_DIA_SEMANA = {0: "Lunes", 1: "Martes", 2: "Miércoles", 3: "Jueves", 4: "Viernes", 5: "Sábado", 6: "Domingo"}


def _build_smart_mesocycle(
    db: Session,
    atleta: models.User,
    name: str,
    discipline: str,
    start_date,
    weeks_count: int,
    training_days: List[int],
    context: str,
    group_id: UUID | None = None,
    session_duration_minutes: int | None = None,
    day_focus: dict[int, str] | None = None,
) -> dict:
    """Genera con IA un mesociclo inteligente completo para UN atleta. Hace commit propio;
    en caso de error hace rollback y relanza la excepción (el llamador decide cómo manejarla)."""
    # 1. Crear el cascarón del mesociclo
    nuevo_meso = models.Mesocycle(
        user_id=atleta.id,
        group_id=group_id,
        name=name,
        discipline=discipline,
        start_date=start_date,
    )
    db.add(nuevo_meso)
    db.flush()

    # 2. Construir el súper contexto (peso y RMs)
    marcas = db.query(models.PersonalRecord).filter(models.PersonalRecord.user_id == atleta.id).all()

    texto_marcas = "Sin marcas registradas."
    if marcas:
        texto_marcas = ", ".join([f"{pr.exercise_name}: {pr.max_weight_kg}kg" for pr in marcas])

    peso_corporal = f"{atleta.body_weight}kg" if atleta.body_weight else "No registrado"
    contexto_enriquecido = f"Peso corporal: {peso_corporal}. Marcas (1RM): {texto_marcas}. Peticiones: {context}"

    # Para resolver los "prescribed_percentage" que devuelva la IA a kg reales — mismo mecanismo
    # que usan las prescripciones manuales/de grupo (ver shared.py), así el peso se recalcula
    # solo si el atleta actualiza su 1RM más adelante, en vez de quedar congelado.
    prs = get_athlete_prs(db, atleta.id)

    # 3. Calcular todas las fechas del mesociclo
    total_dias = weeks_count * 7
    todas_las_fechas = []
    for i in range(total_dias):
        fecha_evaluada = start_date + timedelta(days=i)
        if fecha_evaluada.weekday() in training_days:
            todas_las_fechas.append(fecha_evaluada.strftime("%Y-%m-%d"))

    # 3 semanas por chunk (antes 2): un mesociclo corto (3-4 semanas, el caso más común) queda
    # en UNA sola llamada a Gemini en vez de dos, sin acercarse al límite de tokens de salida
    # del modelo — ver conversación sobre por qué la generación tardaba varios minutos.
    semanas_por_chunk = 3
    sesiones_por_semana = len(training_days)
    sesiones_por_chunk = semanas_por_chunk * sesiones_por_semana

    try:
        # 4. Construir las especificaciones de cada "chunk" (semanas) y pedirlas todas a Gemini
        # EN PARALELO: cada chunk es una llamada HTTP independiente que no depende del resultado
        # de los demás (mismo contexto/marcas, solo cambian las semanas/fechas), así que esperarlas
        # una por una en fila era puro tiempo muerto — un mesociclo de 8 semanas (3 chunks) antes
        # tardaba la SUMA de los 3 chunks; ahora tarda lo que tarda el más lento de ellos.
        from backend.ai_agent import generate_mesocycle_chunk
        from backend.knowledge_search import search_knowledge_base

        # Se calcula UNA sola vez para todo el mesociclo (no por chunk): discipline/context no
        # cambian entre chunks, así que repetirla era una llamada a Gemini + consulta a la base
        # de datos redundante en cada iteración.
        literatura_cientifica = search_knowledge_base(f"{discipline} - {contexto_enriquecido}")

        specs_chunks = []
        for start in range(1, weeks_count + 1, semanas_por_chunk):
            end = min(start + semanas_por_chunk - 1, weeks_count)

            idx_inicio = (start - 1) * sesiones_por_semana
            idx_fin = idx_inicio + sesiones_por_chunk
            fechas_del_chunk = todas_las_fechas[idx_inicio:idx_fin]

            # La guía por día se ata a la FECHA EXACTA (no al nombre del día de la semana): que
            # la IA tenga que calcular ella misma a qué día de la semana corresponde una fecha es
            # justo el tipo de razonamiento donde falla en la práctica (se vieron casos reales
            # donde invirtió la guía de lunes y miércoles). Atándola a la fecha, que la IA YA
            # recibe literal en la REGLA CRÍTICA DE CALENDARIO, no le queda nada que calcular.
            texto_guia_dias = ""
            if day_focus:
                lineas_guia = [
                    f"- {fecha_str} ({_NOMBRE_DIA_SEMANA[datetime.strptime(fecha_str, '%Y-%m-%d').weekday()]}): "
                    f"{day_focus[datetime.strptime(fecha_str, '%Y-%m-%d').weekday()]}"
                    for fecha_str in fechas_del_chunk
                    if datetime.strptime(fecha_str, "%Y-%m-%d").weekday() in day_focus
                ]
                if lineas_guia:
                    texto_guia_dias = (
                        "GUÍA POR FECHA (para estas fechas exactas, en este orden):\n" + "\n".join(lineas_guia)
                    )

            specs_chunks.append((start, end, fechas_del_chunk, texto_guia_dias))

        def _pedir_chunk(spec):
            start, end, fechas_del_chunk, texto_guia_dias = spec
            return generate_mesocycle_chunk(
                athlete_name=atleta.full_name,
                discipline=discipline,
                experience_notes=contexto_enriquecido,
                start_week=start,
                end_week=end,
                session_dates=fechas_del_chunk,
                session_duration_minutes=session_duration_minutes,
                literatura_cientifica=literatura_cientifica,
                day_focus_text=texto_guia_dias,
            )

        # executor.map conserva el orden de entrada en los resultados, así que las semanas se
        # siguen guardando en orden cronológico aunque las respuestas lleguen en otro orden.
        with ThreadPoolExecutor(max_workers=len(specs_chunks)) as executor:
            rutinas_por_chunk = list(executor.map(_pedir_chunk, specs_chunks))

        # 5. Parseo y guardado en base de datos — secuencial a propósito: una sola Session de
        # SQLAlchemy no es segura para escribir desde varios hilos a la vez (a diferencia del
        # paso anterior, que solo hace peticiones HTTP y no toca la base de datos).
        for rutina_ai in rutinas_por_chunk:
            semanas = rutina_ai.get("weeks", [])
            for semana in semanas:
                sesiones = semana.get("sessions", [])

                for sesion_data in sesiones:
                    fecha_str = sesion_data.get("scheduled_date")
                    if fecha_str:
                        fecha_real = datetime.strptime(fecha_str, "%Y-%m-%d").date()
                    else:
                        fecha_real = start_date  # Fallback por seguridad

                    nueva_sesion = models.Session(
                        mesocycle_id=nuevo_meso.id,
                        scheduled_date=fecha_real,
                        athlete_notes=sesion_data.get("athlete_notes", ""),
                        status="pending",
                        duration_minutes=session_duration_minutes,
                    )
                    db.add(nueva_sesion)
                    db.flush()

                    contador_orden = 1
                    ejercicios = sesion_data.get("exercises", [])

                    for ej_data in ejercicios:
                        nombre_ejercicio = ej_data.get("exercise_name", "Ejercicio Desconocido")
                        ejercicio = db.query(models.Exercise).filter(models.Exercise.name == nombre_ejercicio).first()
                        if not ejercicio:
                            ejercicio = models.Exercise(name=nombre_ejercicio, category="General")
                            db.add(ejercicio)
                            db.flush()

                        num_series = ej_data.get("prescribed_sets", 1)
                        reps = ej_data.get("prescribed_reps", 1)

                        rpe_raw = ej_data.get("rpe_target") or ej_data.get("rpe")
                        rpe_limpio = int(float(rpe_raw)) if rpe_raw is not None else None

                        peso_raw = (
                            ej_data.get("prescribed_weight")
                            or ej_data.get("weight_kg")
                            or ej_data.get("weight")
                            or ej_data.get("target_weight")
                        )
                        peso_limpio = None
                        if peso_raw is not None:
                            try:
                                peso_limpio = float(peso_raw)
                            except (ValueError, TypeError):
                                peso_limpio = None

                        porcentaje_raw = ej_data.get("prescribed_percentage")
                        porcentaje_limpio = None
                        if porcentaje_raw is not None:
                            try:
                                porcentaje_limpio = float(porcentaje_raw)
                            except (ValueError, TypeError):
                                porcentaje_limpio = None

                        referencia = ej_data.get("reference_exercise") or nombre_ejercicio
                        if porcentaje_limpio is not None:
                            # La IA sí dio un %: recalcula el kg a partir de la marca ACTUAL del
                            # atleta en vez de confiar en un número que ella misma haya calculado.
                            peso_limpio = resolve_weight_from_percentage(porcentaje_limpio, peso_limpio, referencia, prs)
                        elif peso_limpio is not None:
                            # La IA ignoró la instrucción y dio un kg fijo (pasa seguido, incluso
                            # con el modelo bueno) — si ese kg coincide con una marca de ESTE
                            # atleta para el mismo ejercicio, derivamos el % nosotros, para que la
                            # prescripción quede igual de "viva" que si la hubiera dado ella misma.
                            pr_valor = prs.get(nombre_ejercicio.strip().lower())
                            if pr_valor:
                                porcentaje_limpio = round(peso_limpio / pr_valor * 100)
                                referencia = nombre_ejercicio

                        bloque_limpio = clean_ai_block(ej_data.get("block"))

                        for _ in range(num_series):
                            nuevo_set = models.Set(
                                session_id=nueva_sesion.id,
                                exercise_id=ejercicio.id,
                                set_order=contador_orden,
                                prescribed_reps=reps,
                                rpe=rpe_limpio,
                                prescribed_weight=peso_limpio,
                                prescribed_percentage=porcentaje_limpio,
                                reference_exercise=referencia if porcentaje_limpio is not None else None,
                                block=bloque_limpio,
                            )
                            db.add(nuevo_set)
                            contador_orden += 1

        # 6. Actualizar la fecha de fin
        nuevo_meso.end_date = datetime.strptime(todas_las_fechas[-1], "%Y-%m-%d").date()
        db.commit()
        return {"mesocycle_id": str(nuevo_meso.id)}

    except Exception as e:
        db.rollback()
        raise RuntimeError(str(e)) from e


MAX_ATLETAS_POR_GENERACION_GRUPAL = 25  # cada atleta dispara su propia tanda de llamadas a Gemini
# Cuántos atletas se generan en paralelo a la vez. No es "cuanto más, mejor": cada uno abre su
# propia conexión a la base de datos (pool por defecto de SQLAlchemy: 5 + 10 de overflow) y hace
# sus propias llamadas a Gemini (que también tiene su propio límite de tasa) — un número moderado
# evita agotar el pool de conexiones o disparar 429 de Gemini de golpe con grupos grandes.
MAX_ATLETAS_EN_PARALELO = 5


def _build_smart_mesocycle_en_su_propia_sesion(
    atleta_id: UUID,
    full_name: str,
    name: str,
    discipline: str,
    start_date,
    weeks_count: int,
    training_days: List[int],
    context: str,
    group_id: UUID,
    session_duration_minutes: int | None,
    day_focus: dict[int, str] | None,
) -> dict:
    """Wrapper para correr _build_smart_mesocycle en un hilo del pool: una Session de SQLAlchemy
    NO es segura para compartir entre hilos, así que cada atleta necesita la suya (nunca la del
    request original) — se abre y se cierra aquí mismo, sin importar cómo termine."""
    db = SessionLocal()
    try:
        atleta = db.query(models.User).filter(models.User.id == atleta_id).first()
        if not atleta:
            return {"user_id": str(atleta_id), "full_name": full_name, "status": "error", "detail": "Atleta no encontrado"}
        resultado = _build_smart_mesocycle(
            db, atleta, name, discipline, start_date, weeks_count, training_days, context,
            group_id=group_id, session_duration_minutes=session_duration_minutes, day_focus=day_focus,
        )
        return {"user_id": str(atleta_id), "full_name": full_name, "status": "success", **resultado}
    except RuntimeError as e:
        return {"user_id": str(atleta_id), "full_name": full_name, "status": "error", "detail": str(e)}
    finally:
        db.close()


@router.post("/generate-smart-mesocycle/")
@limiter.limit("10/hour", key_func=_ip_and_user_key)
def generate_and_save_smart_mesocycle(
    request: Request,
    req: schemas.AIGenerateSmart, db: Session = Depends(get_db), current_user: models.User = Depends(require_coach)
):
    atleta = db.query(models.User).filter(models.User.id == req.user_id).first()
    if not atleta:
        raise HTTPException(status_code=404, detail="Atleta no encontrado")
    ensure_owner_or_coach(db, atleta.id, current_user)

    try:
        _build_smart_mesocycle(
            db, atleta, req.name, req.discipline, req.start_date, req.weeks_count, req.training_days, req.context,
            session_duration_minutes=req.session_duration_minutes, day_focus=req.day_focus,
        )
        return {"message": "Mesociclo Inteligente generado y guardado exitosamente."}
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=f"Error interno generando la rutina: {str(e)}")


@router.post("/generate-smart-mesocycle/group")
@limiter.limit("3/hour", key_func=_ip_and_user_key)
def generate_and_save_smart_mesocycle_for_group(
    request: Request,
    req: schemas.AIGenerateSmartGroup, db: Session = Depends(get_db), current_user: models.User = Depends(require_coach)
):
    """Genera con IA el mismo mesociclo (contexto compartido + marcas propias de cada atleta) para todo el grupo.
    Los atletas se generan en paralelo (ver MAX_ATLETAS_EN_PARALELO), cada uno con su propia
    sesión de base de datos y su propio commit — antes se hacía uno por uno, en fila, así que un
    grupo de 25 atletas podía tardar 15-25 minutos reales; en paralelo tarda lo que tarda el
    atleta más lento del lote, no la suma de todos. Si uno falla (p. ej. error de la IA) no se
    pierde el trabajo ya guardado de los demás."""
    grupo = get_owned_group(db, req.group_id, current_user)
    if not grupo.members:
        raise HTTPException(status_code=400, detail="El grupo no tiene atletas asignados")
    if len(grupo.members) > MAX_ATLETAS_POR_GENERACION_GRUPAL:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Este grupo tiene {len(grupo.members)} atletas; el máximo para generar con IA de una vez "
                f"es {MAX_ATLETAS_POR_GENERACION_GRUPAL} (cada atleta dispara varias llamadas a Gemini). "
                "Divide el grupo en subgrupos más pequeños."
            ),
        )

    resultados = []
    with ThreadPoolExecutor(max_workers=min(MAX_ATLETAS_EN_PARALELO, len(grupo.members))) as executor:
        futuros = {
            executor.submit(
                _build_smart_mesocycle_en_su_propia_sesion,
                atleta.id, atleta.full_name, req.name, req.discipline, req.start_date, req.weeks_count,
                req.training_days, req.context, grupo.id, req.session_duration_minutes, req.day_focus,
            ): atleta
            for atleta in grupo.members
        }
        for futuro in as_completed(futuros):
            resultados.append(futuro.result())

    exitosos = sum(1 for r in resultados if r["status"] == "success")
    return {
        "message": f"Mesociclo generado para {exitosos}/{len(resultados)} atleta(s) del grupo '{grupo.name}'",
        "results": resultados,
    }
