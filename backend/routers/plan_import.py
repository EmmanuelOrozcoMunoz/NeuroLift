"""Importar un plan desde un documento (PDF, Word o Excel). Ver services/importar_plan.py."""
import json

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile
from sqlalchemy.orm import Session

from backend import models, schemas
from backend.core.security import _ip_and_user_key, limiter, require_coach
from backend.database import get_db
from backend.services import importar_plan
from backend.services.importar_plan import DocumentoInvalido

router = APIRouter(prefix="/plan-import", tags=["plan-import"])

MAX_DOCUMENTO_JSON = 2_000_000  # lo que el cliente puede devolver al confirmar


def _leer_archivo(archivo: UploadFile) -> bytes:
    """Lee el archivo sin pasarse del tamaño máximo (un byte de más basta para rechazarlo)."""
    contenido = archivo.file.read(importar_plan.MAX_BYTES + 1)
    if len(contenido) > importar_plan.MAX_BYTES:
        raise DocumentoInvalido(
            f"El archivo es demasiado grande (máximo {importar_plan.MAX_BYTES // (1024 * 1024)} MB)."
        )
    return contenido


@router.post("/preview", response_model=schemas.PlanImportPreviewResponse)
@limiter.limit("10/hour", key_func=_ip_and_user_key)
def vista_previa_de_importacion(
    request: Request,
    file: UploadFile = File(...),
    current_user: models.User = Depends(require_coach),
):
    """Lee el documento y devuelve cómo quedaría el plan, SIN guardar nada. Usa la IA (gasta tokens),
    por eso tiene su propio límite por hora. Es una función normal (no async): leer el archivo y esperar
    a Gemini bloquean, y así FastAPI las corre en un hilo sin frenar al resto de las peticiones."""
    contenido = _leer_archivo(file)
    texto = importar_plan.leer_documento(contenido)
    documento = importar_plan.interpretar_documento(texto)
    plan = importar_plan.armar_plan(documento)
    return {"preview": importar_plan.vista_previa(plan), "document": documento}


@router.post("/confirm", response_model=schemas.PlanSummaryResponse)
@limiter.limit("30/hour", key_func=_ip_and_user_key)
def confirmar_importacion(
    request: Request,
    req: schemas.PlanImportConfirm,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_coach),
):
    """Crea el plan (en borrador) con lo que devolvió la vista previa. No vuelve a usar la IA, pero
    tampoco se fía del cliente: el documento se limpia otra vez con las mismas reglas."""
    if len(json.dumps(req.document, default=str)) > MAX_DOCUMENTO_JSON:
        raise HTTPException(status_code=413, detail="El documento es demasiado grande.")
    plan = importar_plan.armar_plan(req.document)
    try:
        mesociclo = importar_plan.crear_plan_importado(
            db, current_user, plan, req.name, req.description, req.discipline, req.level
        )
        db.commit()
    except Exception:
        db.rollback()
        raise
    db.refresh(mesociclo)
    from backend.routers.plans import _plan_summary
    return _plan_summary(db, mesociclo)
