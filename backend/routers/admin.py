from datetime import datetime, timedelta
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from backend import models, schemas
from backend.core import billing
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
    total_boxes = db.query(models.Box).filter(models.Box.status == "active").count()
    boxes_pending = db.query(models.Box).filter(models.Box.status == "pending").count()
    total_groups = db.query(models.Group).count()
    total_mesocycles = db.query(models.Mesocycle).filter(models.Mesocycle.is_template == False).count()
    total_sessions = db.query(models.Session).count()
    sessions_completed = db.query(models.Session).filter(models.Session.status == "completed").count()

    return schemas.AdminOverview(
        total_users=total_users,
        total_coaches=total_coaches,
        total_athletes=total_athletes,
        total_admins=total_admins,
        total_boxes=total_boxes,
        boxes_pending=boxes_pending,
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

    if req.role == "admin":
        # El admin de plataforma no pertenece a ningún box
        usuario.box_id = None
        usuario.coach_id = None
    elif usuario.box_id is None:
        raise HTTPException(
            status_code=400,
            detail="Este usuario no pertenece a ningún box: solo puede ser admin de plataforma.",
        )
    if req.role not in models.COACHING_ROLES:
        # Deja de programar: sus atletas directos pasan a ser atletas "del box" (sin coach)
        # en vez de quedar ligados a alguien que ya no los puede atender.
        db.query(models.User).filter(models.User.coach_id == usuario.id).update({models.User.coach_id: None})

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


@router.get("/boxes", response_model=List[schemas.AdminBoxRow])
def list_boxes(
    status: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_admin),
):
    """Todos los boxes de la plataforma (los pendientes primero), con su dueño y cuántos
    coaches/atletas tiene cada uno."""
    query = db.query(models.Box)
    if status:
        query = query.filter(models.Box.status == status)
    boxes = query.order_by((models.Box.status == "pending").desc(), models.Box.created_at.desc()).all()

    conteos = {
        (box_id, role): total
        for box_id, role, total in db.query(models.User.box_id, models.User.role, func.count(models.User.id))
        .filter(models.User.box_id.in_([b.id for b in boxes]))
        .group_by(models.User.box_id, models.User.role)
        .all()
    }
    duenos = {
        u.box_id: u
        for u in db.query(models.User).filter(
            models.User.box_id.in_([b.id for b in boxes]), models.User.role == "owner"
        ).order_by(models.User.created_at)
    }
    filas = []
    for b in boxes:
        dueno = duenos.get(b.id)
        filas.append(schemas.AdminBoxRow(
            id=b.id,
            name=b.name,
            city=b.city,
            state=b.state,
            country=b.country,
            status=b.status,
            kind=b.kind,
            plan=b.plan,
            subscription_status=billing.subscription_status(b),
            trial_ends_at=b.trial_ends_at,
            paid_until=b.paid_until,
            max_athletes=billing.max_athletes(b),
            has_logo=b.has_logo,
            owner_name=dueno.full_name if dueno else None,
            owner_email=dueno.email if dueno else None,
            coaches_count=conteos.get((b.id, "coach"), 0),
            athletes_count=conteos.get((b.id, "athlete"), 0),
            created_at=b.created_at,
        ))
    return filas


@router.put("/boxes/{box_id}/status", response_model=schemas.MessageResponse)
def update_box_status(
    box_id: UUID,
    req: schemas.AdminBoxStatusUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_admin),
):
    """Aprueba, rechaza o suspende un box. Suspender surte efecto de inmediato: la siguiente
    petición de cualquiera de sus miembros ya se rechaza (ver get_current_user)."""
    box = db.query(models.Box).filter(models.Box.id == box_id).first()
    if not box:
        raise HTTPException(status_code=404, detail="Box no encontrado")
    anterior = box.status
    box.status = req.status
    if req.status == "active" and box.approved_at is None:
        box.approved_at = datetime.utcnow()
        # La prueba gratis de un box empieza al aprobarlo, no al registrarse (mientras está
        # pendiente no puede usar la app, así que no tendría sentido "gastarle" días de prueba)
        if box.trial_ends_at is None:
            box.trial_ends_at = billing.trial_end_from(box.approved_at)
    db.commit()
    security_logger.info(
        "Estado de box: admin=%s cambió '%s' de '%s' a '%s'", current_user.email, box.name, anterior, req.status
    )
    etiqueta = {"active": "activo", "pending": "pendiente", "rejected": "rechazado", "suspended": "suspendido"}
    return {"message": f"El box '{box.name}' ahora está {etiqueta[req.status]}."}


@router.put("/boxes/{box_id}/plan", response_model=schemas.MessageResponse)
def update_box_plan(
    box_id: UUID,
    req: schemas.AdminBoxPlanUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_admin),
):
    """Cambia el plan de una cuenta. Bajar a un plan con menos atletas de los que ya tiene NO
    saca a nadie: solo impide agregar nuevos hasta que vuelvan a estar dentro del límite."""
    box = db.query(models.Box).filter(models.Box.id == box_id).first()
    if not box:
        raise HTTPException(status_code=404, detail="Cuenta no encontrada")
    anterior = box.plan
    box.plan = req.plan
    db.commit()
    security_logger.info("Plan: admin=%s cambió '%s' de '%s' a '%s'", current_user.email, box.name, anterior, req.plan)
    return {"message": f"'{box.name}' ahora está en el plan {billing.PLANS[req.plan]['name'].lower()}."}


@router.post("/boxes/{box_id}/payment", response_model=schemas.MessageResponse)
def register_box_payment(
    box_id: UUID,
    req: schemas.AdminPaymentCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_admin),
):
    """Registra un pago manual (transferencia, Nequi, efectivo...): extiende la suscripción desde
    el vencimiento actual si sigue vigente, o desde hoy si ya había vencido."""
    box = db.query(models.Box).filter(models.Box.id == box_id).first()
    if not box:
        raise HTTPException(status_code=404, detail="Cuenta no encontrada")
    ahora = datetime.utcnow()
    desde = box.paid_until if box.paid_until and box.paid_until > ahora else ahora
    box.paid_until = desde + timedelta(days=billing.PAYMENT_PERIOD_DAYS * req.months)
    db.commit()
    security_logger.info(
        "Pago registrado: admin=%s, cuenta='%s', %s mes(es), pagado hasta %s",
        current_user.email, box.name, req.months, box.paid_until.date(),
    )
    return {"message": f"Pago registrado. '{box.name}' queda pagado hasta el {box.paid_until.strftime('%d/%m/%Y')}."}
