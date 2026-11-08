"""Monitoreo de errores con Sentry. Solo se activa si hay SENTRY_DSN; sin él no se importa ni se envía nada.

Lo que sale a Sentry son las excepciones NO controladas (los 500): los errores de negocio (400/403/404...)
los traduce `main.py` y no cuentan. No se envían cuerpos de petición (llevan contraseñas) ni datos
personales por defecto (cabeceras, cookies, IP)."""
from backend.core.config import ENVIRONMENT, SENTRY_DSN
from backend.core.logging import security_logger


def iniciar() -> bool:
    if not SENTRY_DSN:
        return False
    import sentry_sdk

    sentry_sdk.init(
        dsn=SENTRY_DSN,
        environment=ENVIRONMENT,
        send_default_pii=False,
        max_request_body_size="never",
        traces_sample_rate=0.0,
    )
    security_logger.info("Sentry activo (entorno %s)", ENVIRONMENT)
    return True
