"""Envío de correos (hoy, solo recuperar contraseña) por la API de Resend.

Nunca lanza: si el envío falla, queda en el log y la petición que lo pidió responde igual. Así un
fallo del proveedor no revela si un correo está registrado ni tumba el endpoint."""
import requests

from backend.core.config import EMAIL_API_KEY, EMAIL_FROM, ENVIRONMENT
from backend.core.logging import security_logger

_RESEND_URL = "https://api.resend.com/emails"


def enviar_correo(para: str, asunto: str, html: str, texto: str) -> bool:
    """True si el proveedor lo aceptó. Sin EMAIL_API_KEY no se envía (en desarrollo, el contenido se
    imprime en el log para poder probar el flujo sin proveedor)."""
    if not EMAIL_API_KEY:
        if ENVIRONMENT == "production":
            security_logger.warning("Correo no enviado a %s: falta EMAIL_API_KEY", para)
        else:
            security_logger.info("[correo de desarrollo] Para: %s | %s\n%s", para, asunto, texto)
        return False
    try:
        r = requests.post(
            _RESEND_URL,
            headers={"Authorization": f"Bearer {EMAIL_API_KEY}"},
            json={"from": EMAIL_FROM, "to": [para], "subject": asunto, "html": html, "text": texto},
            timeout=10,
        )
    except requests.RequestException as exc:
        security_logger.error("Correo a %s: no se pudo contactar al proveedor (%s)", para, type(exc).__name__)
        return False
    if r.status_code >= 300:
        security_logger.error("Correo a %s rechazado por el proveedor (HTTP %s)", para, r.status_code)
        return False
    return True


def correo_de_recuperacion(nombre: str, enlace: str, minutos: int) -> tuple[str, str, str]:
    """(asunto, html, texto) del correo con el enlace para elegir una contraseña nueva."""
    asunto = "Restablece tu contraseña de NeuroLift"
    texto = (
        f"Hola {nombre},\n\n"
        f"Recibimos una solicitud para restablecer tu contraseña. Entra a este enlace para elegir una nueva "
        f"(sirve una sola vez y vence en {minutos} minutos):\n\n{enlace}\n\n"
        "Si no fuiste tú, ignora este correo: tu contraseña no cambia."
    )
    html = (
        f"<p>Hola {_esc(nombre)},</p>"
        "<p>Recibimos una solicitud para restablecer tu contraseña. Toca el botón para elegir una nueva "
        f"(sirve una sola vez y vence en {minutos} minutos).</p>"
        f'<p><a href="{_esc(enlace)}" style="display:inline-block;padding:12px 20px;border-radius:10px;'
        'background:#e5484d;color:#fff;text-decoration:none;font-weight:600">Elegir contraseña nueva</a></p>'
        f'<p style="color:#666;font-size:13px">Si el botón no funciona, copia este enlace:<br>{_esc(enlace)}</p>'
        '<p style="color:#666;font-size:13px">Si no fuiste tú, ignora este correo: tu contraseña no cambia.</p>'
    )
    return asunto, html, texto


def _esc(valor: str) -> str:
    return valor.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")
