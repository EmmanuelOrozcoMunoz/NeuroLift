"""Backfill de una sola vez: sincroniza Fit Level <-> "Récords (PRs)" para datos que ya existían
ANTES de que main.py empezara a mantenerlos en sincronía en cada guardado (ver
_FIT_LEVEL_LIFT_TO_PR_NAME / _upsert_personal_record_by_name en backend/main.py).

Sin esto, una marca de Snatch/Clean & Jerk/Back Squat/Deadlift guardada hace tiempo desde Fit
Level nunca aparecería en "Mis récords" (ni viceversa) hasta que alguien la vuelva a guardar a
mano desde cualquiera de las dos pantallas — este script lo resuelve una vez para todo lo que ya
está en la base de datos.

Uso (una sola vez, seguro de correr varias veces — no duplica nada):
    venv/Scripts/python -m backend.backfill_lift_records
"""
from sqlalchemy import func

from backend import models
from backend.database import SessionLocal

_FIT_LEVEL_LIFT_TO_PR_NAME = {
    "snatch_kg": "Snatch",
    "clean_jerk_kg": "Clean & Jerk",
    "back_squat_kg": "Back Squat",
    "deadlift_kg": "Deadlift",
}
_PR_NAME_TO_FIT_LEVEL_LIFT = {name.lower(): key for key, name in _FIT_LEVEL_LIFT_TO_PR_NAME.items()}


def main() -> None:
    db = SessionLocal()
    creados_pr = 0
    creados_benchmark = 0
    try:
        # 1) FitnessBenchmark -> PersonalRecord (el caso que reportó el usuario: marcas de Fit
        #    Level que nunca aparecieron en "Mis récords").
        benchmarks = db.query(models.FitnessBenchmark).filter(
            models.FitnessBenchmark.metric_key.in_(_FIT_LEVEL_LIFT_TO_PR_NAME.keys())
        ).all()
        for fila in benchmarks:
            nombre_pr = _FIT_LEVEL_LIFT_TO_PR_NAME[fila.metric_key]
            existente = db.query(models.PersonalRecord).filter(
                models.PersonalRecord.user_id == fila.user_id,
                func.lower(models.PersonalRecord.exercise_name) == nombre_pr.lower(),
            ).first()
            if not existente:
                db.add(models.PersonalRecord(
                    user_id=fila.user_id, exercise_name=nombre_pr, max_weight_kg=fila.value,
                ))
                creados_pr += 1

        # 2) PersonalRecord -> FitnessBenchmark (simétrico: una marca ya registrada a mano en
        #    "Récords" antes de esta sincronización, para que Fit Level la tenga guardada de
        #    verdad y no solo por el fallback de lectura en _build_fitness_level_response).
        prs = db.query(models.PersonalRecord).all()
        for pr in prs:
            metric_key = _PR_NAME_TO_FIT_LEVEL_LIFT.get(pr.exercise_name.strip().lower())
            if not metric_key:
                continue
            existente = db.query(models.FitnessBenchmark).filter(
                models.FitnessBenchmark.user_id == pr.user_id,
                models.FitnessBenchmark.metric_key == metric_key,
            ).first()
            if not existente:
                db.add(models.FitnessBenchmark(user_id=pr.user_id, metric_key=metric_key, value=pr.max_weight_kg))
                creados_benchmark += 1

        db.commit()
    finally:
        db.close()

    print(f"Listo: {creados_pr} PersonalRecord creado(s), {creados_benchmark} FitnessBenchmark creado(s).")


if __name__ == "__main__":
    main()
