"""Límite de peticiones HTTP procesándose a la vez, por proceso.

Por qué existe. Los endpoints son síncronos: FastAPI los corre en un pool de 40 hilos, y cada
petición retiene una conexión de la base de datos (el pool tiene 30) desde su primera consulta
hasta terminar. Con más peticiones en vuelo que conexiones, las conexiones se agotan y los hilos
quedan bloqueados esperando una; las peticiones que YA tienen conexión necesitan un hilo libre
para terminar y no lo hay. Es un bloqueo mutuo que solo se resuelve cuando vence el tiempo de
espera del pool, y el servicio pasa de ~100 peticiones por segundo a ~3, con errores 500.
(Medido en local: colapsaba a partir de unas 40-80 peticiones simultáneas.)

Qué hace. Deja procesar como máximo `maximo` peticiones a la vez; las demás esperan en cola (en el
bucle de eventos, sin hilos ni conexiones) y, si esperan más de `espera_maxima` segundos, reciben
un 503 con `Retry-After` en lugar de colgarse. Mientras `maximo` sea menor que las conexiones del
pool, el bloqueo no puede ocurrir.

Es un middleware ASGI puro (no BaseHTTPMiddleware) para no sumar costo a cada petición.
"""
import asyncio
import json
import logging

logger = logging.getLogger("neurolift.concurrency")

# No se encola lo que sirve para saber si el servicio está vivo (p. ej. el health check de Render).
RUTAS_EXENTAS = frozenset({"/"})

_MENSAJE_OCUPADO = "El servidor está ocupado en este momento. Intenta de nuevo en unos segundos."


class LimitarConcurrencia:
    def __init__(self, app, maximo: int, espera_maxima: float = 15.0):
        self.app = app
        self.maximo = maximo
        self.espera_maxima = espera_maxima
        # Se crea en el primer uso, ya dentro del bucle de eventos (no al importar el módulo).
        self._semaforo: asyncio.Semaphore | None = None

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http" or self.maximo <= 0 or scope.get("path") in RUTAS_EXENTAS:
            return await self.app(scope, receive, send)

        if self._semaforo is None:
            self._semaforo = asyncio.Semaphore(self.maximo)
        try:
            await asyncio.wait_for(self._semaforo.acquire(), timeout=self.espera_maxima)
        except asyncio.TimeoutError:
            logger.warning("503: %s %s esperó más de %.0f s por un lugar", scope.get("method"), scope.get("path"), self.espera_maxima)
            return await self._responder_ocupado(send)

        try:
            await self.app(scope, receive, send)
        finally:
            self._semaforo.release()

    @staticmethod
    async def _responder_ocupado(send) -> None:
        cuerpo = json.dumps({"detail": _MENSAJE_OCUPADO}).encode("utf-8")
        await send({
            "type": "http.response.start",
            "status": 503,
            "headers": [
                (b"content-type", b"application/json"),
                (b"content-length", str(len(cuerpo)).encode()),
                (b"retry-after", b"2"),
            ],
        })
        await send({"type": "http.response.body", "body": cuerpo})
