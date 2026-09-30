"""Límite de peticiones simultáneas: que no se procesen de más y que la API no se bloquee bajo carga."""
import asyncio
import time

import httpx
import pytest

from backend.core.concurrency import LimitarConcurrencia


def _cliente(app) -> httpx.AsyncClient:
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://prueba", timeout=60)


class AppLenta:
    """App ASGI de mentira: cada petición dura `duracion` y se anota cuántas había a la vez."""

    def __init__(self, duracion=0.05):
        self.duracion = duracion
        self.ahora = 0
        self.maximo_visto = 0
        self.llamadas_lifespan = 0

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            self.llamadas_lifespan += 1
            return
        self.ahora += 1
        self.maximo_visto = max(self.maximo_visto, self.ahora)
        try:
            await asyncio.sleep(0.0 if scope["path"] == "/" else self.duracion)
        finally:
            self.ahora -= 1
        await send({"type": "http.response.start", "status": 200, "headers": [(b"content-type", b"text/plain")]})
        await send({"type": "http.response.body", "body": b"ok"})


def test_nunca_procesa_mas_peticiones_a_la_vez_que_el_maximo_y_todas_terminan():
    async def prueba():
        base = AppLenta(0.05)
        async with _cliente(LimitarConcurrencia(base, maximo=3, espera_maxima=10)) as c:
            respuestas = await asyncio.gather(*[c.get("/x") for _ in range(12)])
        return base, respuestas

    base, respuestas = asyncio.run(prueba())
    assert [r.status_code for r in respuestas] == [200] * 12       # ninguna se pierde: esperan su turno
    assert base.maximo_visto == 3                                     # y nunca hubo más de 3 a la vez


def test_quien_espera_demasiado_recibe_un_503_claro_con_retry_after():
    async def prueba():
        base = AppLenta(0.6)
        async with _cliente(LimitarConcurrencia(base, maximo=1, espera_maxima=0.1)) as c:
            return await asyncio.gather(c.get("/x"), c.get("/x"))

    respuestas = asyncio.run(prueba())
    assert sorted(r.status_code for r in respuestas) == [200, 503]
    ocupado = next(r for r in respuestas if r.status_code == 503)
    assert ocupado.headers["retry-after"] == "2"
    assert ocupado.headers["content-type"] == "application/json"
    assert "ocupado" in ocupado.json()["detail"]


def test_la_ruta_de_salud_no_hace_fila_aunque_todo_este_ocupado():
    async def prueba():
        base = AppLenta(0.5)
        async with _cliente(LimitarConcurrencia(base, maximo=1, espera_maxima=5)) as c:
            lenta = asyncio.create_task(c.get("/x"))
            await asyncio.sleep(0.05)                      # /x ya ocupa el único lugar
            inicio = time.perf_counter()
            salud = await c.get("/")
            espera = time.perf_counter() - inicio
            await lenta
            return salud.status_code, espera

    estado, espera = asyncio.run(prueba())
    assert estado == 200 and espera < 0.3                  # no esperó a que /x terminara (0.5 s)


def test_con_maximo_cero_el_limite_esta_desactivado_y_lifespan_pasa_de_largo():
    async def prueba():
        base = AppLenta(0.02)
        async with _cliente(LimitarConcurrencia(base, maximo=0)) as c:
            await asyncio.gather(*[c.get("/x") for _ in range(10)])
        await LimitarConcurrencia(base, maximo=2)({"type": "lifespan"}, None, None)
        return base

    base = asyncio.run(prueba())
    assert base.maximo_visto == 10                          # sin límite
    assert base.llamadas_lifespan == 1                      # el arranque del servidor no se encola


def test_el_limite_esta_instalado_por_dentro_de_cors_y_no_supera_el_pool():
    from backend.database import MAX_OVERFLOW, POOL_SIZE
    from backend.main import app

    nombres = [m.cls.__name__ for m in app.user_middleware]          # de afuera hacia adentro
    assert nombres[0] == "CORSMiddleware" and nombres[-1] == "LimitarConcurrencia"
    limite = app.user_middleware[-1].kwargs["maximo"]
    assert 0 < limite <= POOL_SIZE + MAX_OVERFLOW                     # nunca más peticiones que conexiones


def test_la_api_real_atiende_muchas_peticiones_simultaneas_sin_bloquearse(atleta_solo):
    """Sin el límite, unas decenas de peticiones a la vez agotaban las conexiones de la base y las
    demás quedaban colgadas hasta vencer el tiempo de espera (segundos de 'nada', y errores)."""
    from backend.main import app

    async def lanzar(n):
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://prueba", headers=atleta_solo.headers, timeout=60
        ) as c:
            return await asyncio.gather(*[c.get("/auth/me") for _ in range(n)])

    app.middleware_stack = None                   # construye el límite de nuevo, con un semáforo limpio
    try:
        inicio = time.perf_counter()
        respuestas = asyncio.run(lanzar(150))
        duracion = time.perf_counter() - inicio
    finally:
        app.middleware_stack = None
    assert [r.status_code for r in respuestas] == [200] * 150
    assert duracion < 30
