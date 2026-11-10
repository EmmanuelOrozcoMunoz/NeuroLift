"""Tope de peticiones de IA a la vez, por proceso.

Por qué. Una generación con IA tarda de segundos a minutos (hasta 45 s por llamada a Gemini, con reintentos, y un
mesociclo largo hace varias en paralelo). Cada una ocupa un hilo del servidor mientras espera, y el servidor
tiene un número fijo de hilos y de plazas (ver core/concurrency.py). Sin un tope, unas decenas de coaches
generando a la vez dejarían a TODOS los demás usuarios esperando por un lugar.

Qué hace. Deja procesar como máximo MAX_IA_SIMULTANEAS peticiones de IA a la vez; hasta MAX_IA_EN_ESPERA más
esperan hasta IA_ESPERA_MAXIMA_SEGUNDOS, y el resto (o quien agota la espera) recibe un 503 con Retry-After. Se
limita la cola porque quien espera también ocupa una plaza del servidor. Se usa como dependencia de FastAPI
(`Depends(plaza_de_ia)`), puesta DESPUÉS de la autenticación: quien no tiene permiso no gasta un lugar.
"""
import threading
from collections.abc import Iterator

from backend.core import config
from backend.core.errors import ErrorDeDominio

_semaforo: threading.BoundedSemaphore | None = None
_cerrojo = threading.Lock()
_en_espera = 0


class IAOcupada(ErrorDeDominio):
    """Hay demasiadas generaciones de IA en curso (503); conviene reintentar en unos segundos."""

    status_code = 503

    def __init__(self):
        super().__init__(
            "La IA está ocupada en este momento. Intenta de nuevo en un minuto.",
            headers={"Retry-After": "30"},
        )


def _obtener_semaforo() -> threading.BoundedSemaphore | None:
    global _semaforo
    if config.MAX_IA_SIMULTANEAS <= 0:
        return None
    with _cerrojo:
        if _semaforo is None:
            _semaforo = threading.BoundedSemaphore(config.MAX_IA_SIMULTANEAS)
        return _semaforo


def plaza_de_ia() -> Iterator[None]:
    """Reserva un lugar de IA mientras dura la petición (y lo suelta al terminar, con éxito o con error)."""
    global _en_espera
    semaforo = _obtener_semaforo()
    if semaforo is None:
        yield
        return
    # Un lugar libre se toma sin esperar; si no, se espera, pero la cola tiene un tope
    if not semaforo.acquire(blocking=False):
        with _cerrojo:
            if _en_espera >= config.MAX_IA_EN_ESPERA:
                raise IAOcupada()
            _en_espera += 1
        try:
            tomado = semaforo.acquire(timeout=config.IA_ESPERA_MAXIMA_SEGUNDOS)
        finally:
            with _cerrojo:
                _en_espera -= 1
        if not tomado:
            raise IAOcupada()
    try:
        yield
    finally:
        semaforo.release()
