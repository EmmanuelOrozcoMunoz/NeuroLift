from datetime import timedelta
from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload

from backend import models, schemas
from backend.core.security import _coach_athlete_ids, ensure_owner_or_coach, get_current_user, require_coach
from backend.database import get_db
from backend.routers.shared import get_owned_group

router = APIRouter(prefix="/mesocycles", tags=["mesocycles"])


@router.post("/", response_model=schemas.MesocycleResponse)
def create_mesocycle(
    mesocycle: schemas.MesocycleCreate, db: Session = Depends(get_db), current_user: models.User = Depends(require_coach)
):
    db_user = db.query(models.User).filter(models.User.id == mesocycle.user_id).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    ensure_owner_or_coach(db, db_user.id, current_user)

    new_meso = models.Mesocycle(
        user_id=mesocycle.user_id,
        name=mesocycle.name,
        discipline=mesocycle.discipline,
        start_date=mesocycle.start_date,
    )
    db.add(new_meso)
    db.commit()
    db.refresh(new_meso)
    return new_meso


@router.get("/", response_model=List[schemas.MesocycleResponse])
def listar_mesociclos(db: Session = Depends(get_db), current_user: models.User = Depends(require_coach)):
    """Mesociclos básicos (sin plantillas de planes). Un admin los ve todos; un coach, solo los
    de sus propios atletas."""
    query = db.query(models.Mesocycle).filter(models.Mesocycle.is_template == False)
    if current_user.role != "admin":
        ids = _coach_athlete_ids(db, current_user.id)
        if not ids:
            return []
        query = query.filter(models.Mesocycle.user_id.in_(ids))
    return query.all()


@router.get("/{mesocycle_id}", response_model=schemas.MesocycleFullResponse)
def get_full_mesocycle(
    mesocycle_id: UUID, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)
):
    """Obtiene un mesociclo completo con todas sus sesiones, series y ejercicios anidados."""
    meso = db.query(models.Mesocycle).options(
        joinedload(models.Mesocycle.sessions)
        .joinedload(models.Session.sets)
        .joinedload(models.Set.exercise)
    ).filter(models.Mesocycle.id == mesocycle_id).first()

    if not meso:
        raise HTTPException(status_code=404, detail="Mesociclo no encontrado")

    ensure_owner_or_coach(db, meso.user_id, current_user)

    # Ordenamos sesiones por fecha y series por su set_order
    meso.sessions.sort(key=lambda s: s.scheduled_date)
    for sesion in meso.sessions:
        sesion.sets.sort(key=lambda serie: serie.set_order)

    return meso


def _build_manual_mesocycle(
    db: Session,
    user_id: UUID,
    name: str,
    discipline: str,
    start_date,
    weeks_count: int,
    training_days: List[int],
    group_id: UUID | None = None,
) -> dict:
    """Crea el cascarón de un mesociclo manual y sus sesiones vacías para UN atleta. Hace commit propio."""
    nuevo_meso = models.Mesocycle(
        user_id=user_id,
        group_id=group_id,
        name=name,
        discipline=discipline,
        start_date=start_date,
    )
    db.add(nuevo_meso)
    db.flush()

    total_dias_mesociclo = weeks_count * 7
    sesiones_creadas = 0

    for i in range(total_dias_mesociclo):
        fecha_evaluada = start_date + timedelta(days=i)
        if fecha_evaluada.weekday() in training_days:
            nueva_sesion = models.Session(
                mesocycle_id=nuevo_meso.id,
                scheduled_date=fecha_evaluada,
                athlete_notes="Sesión manual. Añade tus ejercicios.",
                status="pending",
            )
            db.add(nueva_sesion)
            sesiones_creadas += 1

    nuevo_meso.end_date = start_date + timedelta(days=total_dias_mesociclo - 1)
    db.commit()

    return {"mesocycle_id": str(nuevo_meso.id), "total_sessions": sesiones_creadas}


@router.post("/manual")
def create_manual_mesocycle(
    req: schemas.MesocycleManualCreate, db: Session = Depends(get_db), current_user: models.User = Depends(require_coach)
):
    """Crea el cascarón del mesociclo y las sesiones vacías según el calendario."""
    db_user = db.query(models.User).filter(models.User.id == req.user_id).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    ensure_owner_or_coach(db, db_user.id, current_user)

    resultado = _build_manual_mesocycle(
        db, req.user_id, req.name, req.discipline, req.start_date, req.weeks_count, req.training_days
    )
    return {"message": "Mesociclo manual creado con éxito", **resultado}


@router.post("/manual/group")
def create_manual_mesocycle_for_group(
    req: schemas.MesocycleManualGroupCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_coach),
):
    """Crea el mismo mesociclo manual (cascarón + calendario) para cada atleta del grupo."""
    grupo = get_owned_group(db, req.group_id, current_user)
    if not grupo.members:
        raise HTTPException(status_code=400, detail="El grupo no tiene atletas asignados")

    resultados = []
    for atleta in grupo.members:
        resultado = _build_manual_mesocycle(
            db, atleta.id, req.name, req.discipline, req.start_date, req.weeks_count, req.training_days,
            group_id=grupo.id,
        )
        resultados.append({"user_id": str(atleta.id), "full_name": atleta.full_name, **resultado})

    return {
        "message": f"Mesociclo manual creado para {len(resultados)} atleta(s) del grupo '{grupo.name}'",
        "results": resultados,
    }
