from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend import models, schemas
from backend.core.logging import security_logger
from backend.core.security import require_admin
from backend.database import get_db

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/overview", response_model=schemas.AdminOverview)
def get_admin_overview(db: Session = Depends(get_db), current_user: models.User = Depends(require_admin)):
    """Vista completa de la app: conteos globales sin importar de qué coach o atleta sean."""
    total_users = db.query(models.User).count()
    total_coaches = db.query(models.User).filter(models.User.role == "coach").count()
    total_athletes = db.query(models.User).filter(models.User.role == "athlete").count()
    total_admins = db.query(models.User).filter(models.User.role == "admin").count()
    total_groups = db.query(models.Group).count()
    total_mesocycles = db.query(models.Mesocycle).filter(models.Mesocycle.is_template == False).count()
    total_sessions = db.query(models.Session).count()
    sessions_completed = db.query(models.Session).filter(models.Session.status == "completed").count()

    return schemas.AdminOverview(
        total_users=total_users,
        total_coaches=total_coaches,
        total_athletes=total_athletes,
        total_admins=total_admins,
        total_groups=total_groups,
        total_mesocycles=total_mesocycles,
        total_sessions=total_sessions,
        sessions_completed=sessions_completed,
        sessions_pending=total_sessions - sessions_completed,
    )


@router.put("/users/{user_id}/role", response_model=schemas.UserResponse)
def update_user_role(
    user_id: UUID,
    req: schemas.UserRoleUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_admin),
):
    """Cambia el rol de cualquier usuario (promover a coach/admin, o degradar a atleta)."""
    if user_id == current_user.id and req.role != "admin":
        raise HTTPException(status_code=400, detail="No puedes quitarte a ti mismo el rol de admin")

    usuario = db.query(models.User).filter(models.User.id == user_id).first()
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    rol_anterior = usuario.role
    usuario.role = req.role
    db.commit()
    db.refresh(usuario)

    security_logger.info(
        "Cambio de rol: admin=%s cambió a usuario=%s de rol '%s' a '%s'",
        current_user.email, usuario.email, rol_anterior, req.role,
    )
    return usuario


@router.post("/users/{user_id}/revoke-sessions", response_model=schemas.MessageResponse)
def revoke_user_sessions(
    user_id: UUID,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_admin),
):
    """Fuerza la revocación de TODOS los tokens de un usuario (todos sus dispositivos),
    útil ante sospecha de cuenta comprometida — sin esperar a que el token expire por sí solo."""
    usuario = db.query(models.User).filter(models.User.id == user_id).first()
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    usuario.token_version += 1
    db.commit()

    security_logger.warning(
        "Revocación forzada: admin=%s revocó todas las sesiones de usuario=%s",
        current_user.email, usuario.email,
    )
    return {"message": f"Todas las sesiones de {usuario.full_name} fueron revocadas."}


@router.get("/logs", response_model=List[schemas.AuditLogResponse])
def get_audit_logs(
    limit: int = 200,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_admin),
):
    """Historial de eventos de seguridad (logins fallidos, cambios de rol, revocaciones...),
    más reciente primero. Espejo persistente de lo que security_logger ya imprime en consola."""
    return (
        db.query(models.AuditLog)
        .order_by(models.AuditLog.created_at.desc())
        .limit(min(limit, 500))
        .all()
    )
