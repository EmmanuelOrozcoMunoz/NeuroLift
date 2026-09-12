"""Backfill de una sola vez: llena users.coach_id para atletas que ya existian ANTES de que esa
columna existiera (ver migracion b1c2d3e4f5a6) y que nunca pasaron por el unico camino que la
llena hoy (que un coach YA logueado los registre desde "Registrar atleta" en POST /auth/register,
ver main.py).

Para cada atleta con coach_id=NULL, se infiere el coach a partir de sus grupos: si pertenece a
UN solo coach (ya sea porque esta en un solo grupo, o en varios grupos del mismo coach), se le
asigna ese coach_id. Si esta en grupos de coaches DISTINTOS (ambiguo) o no esta en ningun grupo,
se deja en NULL -- ahi si es el valor correcto, no hay un unico coach que inferir.

Uso (una sola vez, seguro de correr varias veces -- solo toca coach_id que sigan en NULL):
    venv/Scripts/python -m backend.backfill_coach_id
"""
from backend import models
from backend.database import SessionLocal


def main() -> None:
    db = SessionLocal()
    actualizados = []
    ambiguos = []
    sin_grupo = []
    try:
        atletas = db.query(models.User).filter(
            models.User.role == "athlete", models.User.coach_id.is_(None),
        ).all()

        for atleta in atletas:
            grupos = (
                db.query(models.Group)
                .join(models.group_members, models.Group.id == models.group_members.c.group_id)
                .filter(models.group_members.c.user_id == atleta.id)
                .all()
            )
            coaches_distintos = {g.coach_id for g in grupos}

            if len(coaches_distintos) == 1:
                atleta.coach_id = coaches_distintos.pop()
                actualizados.append(atleta.email)
            elif len(coaches_distintos) > 1:
                ambiguos.append((atleta.email, [str(c) for c in coaches_distintos]))
            else:
                sin_grupo.append(atleta.email)

        db.commit()
    finally:
        db.close()

    print(f"Actualizados ({len(actualizados)}): {actualizados}")
    if ambiguos:
        print(f"Ambiguos, dejados en NULL ({len(ambiguos)}): {ambiguos}")
    print(f"Sin grupo, correctamente en NULL ({len(sin_grupo)}): {sin_grupo}")


if __name__ == "__main__":
    main()
