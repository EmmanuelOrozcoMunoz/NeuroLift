"""Borra los registros ANTIGUOS de clases que los atletas tienen en su historial.

Cuando las clases se podían registrar, cada registro copiaba a la cuenta del atleta el contenido
que había programado el profesor (mesociclo "Clases del box", `is_class_log`). Como las clases
pasaron a ser solo para los entrenadores, esas copias son contenido confidencial que sigue en las
cuentas de los atletas. Este script las elimina, con sus sesiones y series.

ES DESTRUCTIVO: por defecto solo cuenta lo que borraría. Para borrar de verdad, agrega --yes.
Se corre una vez por ambiente (Dev, QA, PRD), con el DATABASE_URL de ese ambiente:

    python -m backend.scripts.purgar_registros_de_clase          # solo cuenta (no borra)
    python -m backend.scripts.purgar_registros_de_clase --yes    # borra
"""
import argparse
import sys

from sqlalchemy.orm import Session

from backend import models


def purgar_registros_de_clase(db: Session, ejecutar: bool = False) -> dict[str, int]:
    """Cuenta (y, si `ejecutar`, borra) los mesociclos de registro de clases de los atletas."""
    mesos = db.query(models.Mesocycle).filter(models.Mesocycle.is_class_log == True).all()  # noqa: E712
    sesiones = 0
    series = 0
    for meso in mesos:
        for sesion in meso.sessions:
            sesiones += 1
            series += len(sesion.sets)
    resumen = {"atletas": len({m.user_id for m in mesos}), "mesociclos": len(mesos), "sesiones": sesiones, "series": series}
    if ejecutar:
        for meso in mesos:
            db.delete(meso)  # en cascada: sus sesiones y series
        db.commit()
    return resumen


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--yes", action="store_true", help="borra de verdad (sin esto solo cuenta)")
    args = parser.parse_args(argv)

    from backend.database import SessionLocal

    with SessionLocal() as db:
        resumen = purgar_registros_de_clase(db, ejecutar=args.yes)

    accion = "BORRADOS" if args.yes else "se borrarían (no se borró nada; usa --yes)"
    print(
        f"Registros de clase: {resumen['mesociclos']} mesociclo(s) de {resumen['atletas']} atleta(s), "
        f"{resumen['sesiones']} sesión(es), {resumen['series']} serie(s) → {accion}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
