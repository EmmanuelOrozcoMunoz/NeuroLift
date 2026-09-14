import logging

from backend import models
from backend.database import SessionLocal

# ==========================================
# LOGGING DE SEGURIDAD (logins fallidos, 401/403, cambios de rol)
# ==========================================
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
security_logger = logging.getLogger("neurolift.security")


class _AuditLogHandler(logging.Handler):
    """Espejo de security_logger en la tabla audit_logs (ver backend/models.py): antes estos
    eventos solo vivían en la consola del proceso y se perdían al reiniciar. Una conexión
    propia (no Depends(get_db)) porque un logger no vive dentro del ciclo de vida de un
    request. Nunca debe romper el flujo que disparó el log si la escritura falla."""

    def emit(self, record: logging.LogRecord) -> None:
        db = SessionLocal()
        try:
            db.add(models.AuditLog(level=record.levelname, message=record.getMessage()))
            db.commit()
        except Exception:
            db.rollback()
        finally:
            db.close()


security_logger.addHandler(_AuditLogHandler())
