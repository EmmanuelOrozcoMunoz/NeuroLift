"""Códigos de invitación de las cuentas (boxes, coaches independientes y atletas solos)."""
import secrets

from sqlalchemy.orm import Session

from backend import models

# Sin 0/O ni 1/I: el código se dicta en voz alta o se copia de una pantalla
_CODE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"


def new_invite_code(db: Session) -> str:
    """Código de 8 caracteres (32^8 ≈ 10^12 combinaciones: no se adivina probando)."""
    while True:
        code = "".join(secrets.choice(_CODE_ALPHABET) for _ in range(8))
        if not db.query(models.Box.id).filter(models.Box.invite_code == code).first():
            return code
