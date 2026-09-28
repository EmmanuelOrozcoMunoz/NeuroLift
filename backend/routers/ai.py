from concurrent.futures import ThreadPoolExecutor, as_completed

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from backend import models, schemas
from backend.core.security import (
    _ip_and_user_key,
    ensure_can_manage_mesocycle,
    ensure_has_personal_coach,
    ensure_owner_or_coach,
    limiter,
    require_coach,
)
from backend.database import get_db
from backend.routers.group_helpers import get_owned_group
from backend.services.ai_mesocycles import (
    construir_mesociclo_en_su_propia_sesion,
    construir_mesociclo_inteligente,
    guardar_sesion_ia,
)

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
    ensure_can_manage_mesocycle(db, meso, current_user)

    from backend.ai_agent import generate_workout_session
    rutina_ai = generate_workout_session(
        # La programación de una clase no tiene atleta: la IA la arma para el grupo de la clase
        athlete_name=meso.user.full_name if meso.user else f"la clase {meso.box_class.name}",
        discipline=meso.discipline,
        experience_notes=req.context,
    )

    if "error" in rutina_ai:
        raise HTTPException(status_code=500, detail=rutina_ai["error"])

    nueva_sesion = guardar_sesion_ia(db, meso, rutina_ai)
    db.commit()
    db.refresh(nueva_sesion)

    return {"status": "success", "session_focus": rutina_ai.get("session_focus"), "session_id": nueva_sesion.id}


MAX_ATLETAS_POR_GENERACION_GRUPAL = 25  # cada atleta dispara su propia tanda de llamadas a Gemini
# Cuántos atletas se generan en paralelo a la vez. No es "cuanto más, mejor": cada uno abre su
# propia conexión a la base de datos (pool por defecto de SQLAlchemy: 5 + 10 de overflow) y hace
# sus propias llamadas a Gemini (que también tiene su propio límite de tasa) — un número moderado
# evita agotar el pool de conexiones o disparar 429 de Gemini de golpe con grupos grandes.
MAX_ATLETAS_EN_PARALELO = 5


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
    ensure_has_personal_coach([atleta])

    try:
        construir_mesociclo_inteligente(
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
    ensure_has_personal_coach(grupo.members)
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
                construir_mesociclo_en_su_propia_sesion,
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
