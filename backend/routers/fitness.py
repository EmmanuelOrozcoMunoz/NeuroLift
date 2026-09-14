from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend import fitness_scoring, models, schemas
from backend.core.security import ensure_owner_or_coach, get_current_user
from backend.database import get_db
from backend.routers.shared import FIT_LEVEL_LIFT_TO_PR_NAME, upsert_personal_record_by_name

router = APIRouter(tags=["fitness"])


@router.put("/users/{user_id}/fitness-benchmarks", response_model=schemas.FitnessLevelResponse)
def update_fitness_benchmarks(
    user_id: UUID,
    req: schemas.FitnessBenchmarkUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Guarda las marcas que el atleta (dueño) o su coach hayan llenado, y devuelve el
    Fit Level ya recalculado. Solo se tocan los campos enviados (no None)."""
    ensure_owner_or_coach(db, user_id, current_user)

    usuario = db.query(models.User).filter(models.User.id == user_id).first()
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    datos = req.model_dump(exclude_unset=True, exclude_none=True)

    if "body_weight" in datos:
        usuario.body_weight = datos.pop("body_weight")
    if "sex" in datos:
        usuario.sex = datos.pop("sex")
    if "age" in datos:
        usuario.age = datos.pop("age")
    if "category" in datos:
        usuario.category = datos.pop("category")

    for metric_key, value in datos.items():
        if metric_key not in fitness_scoring.METRICS:
            continue
        valor = float(value)
        fila = db.query(models.FitnessBenchmark).filter(
            models.FitnessBenchmark.user_id == user_id,
            models.FitnessBenchmark.metric_key == metric_key,
        ).first()
        if fila:
            fila.value = valor
        else:
            db.add(models.FitnessBenchmark(user_id=user_id, metric_key=metric_key, value=valor))

        # Los 4 levantamientos de halterofilia también son un RM: que aparezcan en "Récords
        # (PRs)" sin tener que volver a escribirlos ahí a mano.
        nombre_pr = FIT_LEVEL_LIFT_TO_PR_NAME.get(metric_key)
        if nombre_pr:
            upsert_personal_record_by_name(db, user_id, nombre_pr, valor)

    db.commit()
    return _build_fitness_level_response(db, usuario)


@router.get("/users/{user_id}/fitness-level", response_model=schemas.FitnessLevelResponse)
def get_fitness_level(
    user_id: UUID, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)
):
    """Devuelve las marcas guardadas y el Fit Level calculado a partir de ellas."""
    ensure_owner_or_coach(db, user_id, current_user)
    usuario = db.query(models.User).filter(models.User.id == user_id).first()
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    return _build_fitness_level_response(db, usuario)


def _build_fitness_level_response(db: Session, usuario: models.User) -> schemas.FitnessLevelResponse:
    filas = db.query(models.FitnessBenchmark).filter(models.FitnessBenchmark.user_id == usuario.id).all()
    valores = {f.metric_key: f.value for f in filas}

    # Si algún RM de halterofilia no se llenó nunca desde Fit Level pero sí existe como
    # PersonalRecord (p. ej. lo registró el coach desde "Récords (PRs)" antes de que esta
    # sincronización existiera), se usa ese valor en vez de dejar el campo vacío.
    faltantes = [k for k in FIT_LEVEL_LIFT_TO_PR_NAME if k not in valores]
    if faltantes:
        prs = db.query(models.PersonalRecord).filter(models.PersonalRecord.user_id == usuario.id).all()
        prs_por_nombre = {pr.exercise_name.strip().lower(): pr.max_weight_kg for pr in prs}
        for metric_key in faltantes:
            nombre_pr = FIT_LEVEL_LIFT_TO_PR_NAME[metric_key].lower()
            if nombre_pr in prs_por_nombre:
                valores[metric_key] = prs_por_nombre[nombre_pr]

    resultado = fitness_scoring.compute_fitness_level(valores, usuario.body_weight, usuario.sex, usuario.age)
    return schemas.FitnessLevelResponse(
        body_weight=usuario.body_weight,
        sex=usuario.sex,
        age=usuario.age,
        category=usuario.category,
        values=valores,
        category_scores=resultado["category_scores"],
        category_levels=resultado["category_levels"],
        overall_score=resultado["overall_score"],
        overall_level=resultado["overall_level"],
    )
