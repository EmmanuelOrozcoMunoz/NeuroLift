"""Errores de negocio, independientes de HTTP.

Las reglas de permisos, suscripción e imágenes (core/, servicios, helpers) lanzan estas
excepciones en vez de `HTTPException`: así no saben nada de la capa web y se pueden usar desde
un servicio, un script o una prueba. `main.py` registra UN manejador que las traduce a la
respuesta HTTP (mismo código y mismo `detail` que antes).

Los routers, que SÍ son la capa HTTP, pueden seguir usando `HTTPException` directamente.
"""


class ErrorDeDominio(Exception):
    """Base. `status_code` es el código HTTP con el que se responde al cliente."""

    status_code = 400

    def __init__(self, detail: str, *, headers: dict[str, str] | None = None):
        super().__init__(detail)
        self.detail = detail
        self.headers = headers


class SolicitudInvalida(ErrorDeDominio):
    """La petición es válida como HTTP pero rompe una regla de negocio (400)."""

    status_code = 400


class NoAutenticado(ErrorDeDominio):
    """Falta o falló la identidad (401). Lleva la cabecera que exige el esquema Bearer."""

    status_code = 401

    def __init__(self, detail: str, *, headers: dict[str, str] | None = None):
        super().__init__(detail, headers=headers or {"WWW-Authenticate": "Bearer"})


class Prohibido(ErrorDeDominio):
    """Se sabe quién es, pero no tiene permiso o la regla se lo impide (403)."""

    status_code = 403


class NoEncontrado(ErrorDeDominio):
    """El recurso no existe (o no se le puede revelar que existe) (404)."""

    status_code = 404


class ServicioNoDisponible(ErrorDeDominio):
    """Falló un servicio externo del que depende la operación, p. ej. el almacenamiento (502)."""

    status_code = 502
