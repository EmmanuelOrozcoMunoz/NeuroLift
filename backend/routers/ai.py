from datetime import date, datetime, timedelta
from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from backend import models, schemas
from backend.core.security import ensure_owner_or_coach, limiter, require_coach
from backend.database import get_db
from backend.routers.shared import clean_ai_block, get_owned_group

router = APIRouter(prefix="/ai", tags=["ai"])


@router.post("/generate-session/")
@limiter.limit("20/hour")
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
        # 4. Bucle de generación por "chunks" (semanas)
        from backend.ai_agent import generate_mesocycle_chunk, search_knowledge_base

        # Se calcula UNA sola vez para todo el mesociclo (no por chunk): discipline/context no
        # cambian entre chunks, así que repetirla era una llamada a Gemini + consulta a la base
        # de datos redundante en cada iteración.
        literatura_cientifica = search_knowledge_base(f"{discipline} - {contexto_enriquecido}")

        for start in range(1, weeks_count + 1, semanas_por_chunk):
            end = min(start + semanas_por_chunk - 1, weeks_count)

            idx_inicio = (start - 1) * sesiones_por_semana
            idx_fin = idx_inicio + sesiones_por_chunk
            fechas_del_chunk = todas_las_fechas[idx_inicio:idx_fin]

            rutina_ai = generate_mesocycle_chunk(
                athlete_name=atleta.full_name,
                discipline=discipline,
                experience_notes=contexto_enriquecido,
                start_week=start,
                end_week=end,
                session_dates=fechas_del_chunk,
                session_duration_minutes=session_duration_minutes,
                literatura_cientifica=literatura_cientifica,
            )

            # 5. Parseo y guardado en base de datos
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

                        bloque_limpio = clean_ai_block(ej_data.get("block"))

                        for _ in range(num_series):
                            nuevo_set = models.Set(
                                session_id=nueva_sesion.id,
                                exercise_id=ejercicio.id,
                                set_order=contador_orden,
                                prescribed_reps=reps,
                                rpe=rpe_limpio,
                                prescribed_weight=peso_limpio,
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


@router.post("/generate-smart-mesocycle/")
@limiter.limit("10/hour")
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
            session_duration_minutes=req.session_duration_minutes,
        )
        return {"message": "Mesociclo Inteligente generado y guardado exitosamente."}
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=f"Error interno generando la rutina: {str(e)}")


@router.post("/generate-smart-mesocycle/group")
@limiter.limit("3/hour")
def generate_and_save_smart_mesocycle_for_group(
    request: Request,
    req: schemas.AIGenerateSmartGroup, db: Session = Depends(get_db), current_user: models.User = Depends(require_coach)
):
    """Genera con IA el mismo mesociclo (contexto compartido + marcas propias de cada atleta) para todo el grupo.
    Se ejecuta atleta por atleta y cada uno hace su propio commit, así que si uno falla
    (p. ej. error de la IA) no se pierde el trabajo ya guardado de los demás."""
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
    for atleta in grupo.members:
        try:
            resultado = _build_smart_mesocycle(
                db, atleta, req.name, req.discipline, req.start_date, req.weeks_count, req.training_days, req.context,
                group_id=grupo.id, session_duration_minutes=req.session_duration_minutes,
            )
            resultados.append({"user_id": str(atleta.id), "full_name": atleta.full_name, "status": "success", **resultado})
        except RuntimeError as e:
            resultados.append({"user_id": str(atleta.id), "full_name": atleta.full_name, "status": "error", "detail": str(e)})

    exitosos = sum(1 for r in resultados if r["status"] == "success")
    return {
        "message": f"Mesociclo generado para {exitosos}/{len(resultados)} atleta(s) del grupo '{grupo.name}'",
        "results": resultados,
    }
