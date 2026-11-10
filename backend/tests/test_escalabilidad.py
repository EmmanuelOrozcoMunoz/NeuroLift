"""Lo que mantiene la API en pie con muchos usuarios: la IP real detrás de un proxy, el tope de IA y que la
pantalla de Atletas no lea todo el historial."""
from datetime import timedelta

import pytest
from starlette.requests import Request

from backend.core import ia_limite, security
from backend.core.errors import ErrorDeDominio
from backend.tests.test_asignar_plan import grupo, plantilla, _asignar  # noqa: F401  (fixtures)
from backend.tests.test_entrenos_del_coach import LUNES, _con_wod, _terminar


# ------------------------------------------------------------------ la IP del cliente

def _peticion(xff: str | None, conexion: str = "10.0.0.1") -> Request:
    cabeceras = [(b"x-forwarded-for", xff.encode())] if xff is not None else []
    return Request({"type": "http", "headers": cabeceras, "client": (conexion, 5000)})


def test_sin_proxy_la_ip_es_la_de_la_conexion_y_el_encabezado_no_cuenta(monkeypatch):
    monkeypatch.setattr(security, "PROXY_HOPS", 0)
    assert security.ip_del_cliente(_peticion("9.9.9.9")) == "10.0.0.1"   # un cliente no puede falsearla


@pytest.mark.parametrize("saltos, esperada", [(1, "1.2.3.4"), (2, "9.9.9.9"), (3, "10.0.0.1")])
def test_detras_de_un_proxy_se_toma_la_direccion_que_el_proxy_añadio(monkeypatch, saltos, esperada):
    monkeypatch.setattr(security, "PROXY_HOPS", saltos)
    # "9.9.9.9" es lo que mandó el cliente; "1.2.3.4" lo añadió el proxy. Con 3 saltos falta información: la conexión.
    assert security.ip_del_cliente(_peticion("9.9.9.9, 1.2.3.4")) == esperada


def test_lo_que_el_cliente_pone_a_la_izquierda_no_cambia_su_ip(monkeypatch):
    monkeypatch.setattr(security, "PROXY_HOPS", 1)
    a = security.ip_del_cliente(_peticion("falsa-1, 8.8.8.8"))
    b = security.ip_del_cliente(_peticion("falsa-2, otra, 8.8.8.8"))
    assert a == b == "8.8.8.8"


def test_sin_encabezado_se_usa_la_conexion(monkeypatch):
    monkeypatch.setattr(security, "PROXY_HOPS", 1)
    assert security.ip_del_cliente(_peticion(None)) == "10.0.0.1"


# ------------------------------------------------------------------ el tope de IA

@pytest.fixture
def un_lugar_de_ia(monkeypatch):
    """Un solo lugar de IA, sin cola: el segundo que llega recibe el 503 al instante."""
    monkeypatch.setattr(ia_limite.config, "MAX_IA_SIMULTANEAS", 1)
    monkeypatch.setattr(ia_limite.config, "MAX_IA_EN_ESPERA", 0)
    monkeypatch.setattr(ia_limite, "_semaforo", None)
    yield
    monkeypatch.setattr(ia_limite, "_semaforo", None)


def test_con_el_lugar_ocupado_el_siguiente_recibe_un_503_y_al_soltarlo_vuelve_a_haber(un_lugar_de_ia):
    primero = ia_limite.plaza_de_ia()
    next(primero)
    with pytest.raises(ErrorDeDominio) as error:
        next(ia_limite.plaza_de_ia())
    assert error.value.status_code == 503 and error.value.headers == {"Retry-After": "30"}
    primero.close()                                   # termina la petición: el lugar se libera
    otro = ia_limite.plaza_de_ia()
    next(otro)
    otro.close()


def test_la_espera_tiene_tope_de_tiempo(monkeypatch):
    monkeypatch.setattr(ia_limite.config, "MAX_IA_SIMULTANEAS", 1)
    monkeypatch.setattr(ia_limite.config, "MAX_IA_EN_ESPERA", 2)
    monkeypatch.setattr(ia_limite.config, "IA_ESPERA_MAXIMA_SEGUNDOS", 0.1)
    monkeypatch.setattr(ia_limite, "_semaforo", None)
    primero = ia_limite.plaza_de_ia()
    next(primero)
    with pytest.raises(ErrorDeDominio):               # espera 0,1 s y se rinde
        next(ia_limite.plaza_de_ia())
    assert ia_limite._en_espera == 0                  # y no deja a nadie "en la cola"
    primero.close()


def test_un_endpoint_de_ia_responde_503_cuando_no_hay_lugar_y_un_atleta_ni_gasta_lugar(client, coach, atleta_de_coach, un_lugar_de_ia):
    ocupado = ia_limite.plaza_de_ia()
    next(ocupado)
    cuerpo = {"name": "Plantilla", "description": "", "discipline": "CrossFit", "level": "Intermedio",
              "weeks_count": 2, "training_days": [0, 3], "context": "fuerza"}
    r = coach.post("/ai/generate-plan-template/", json=cuerpo)
    assert r.status_code == 503 and r.headers["retry-after"] == "30"
    assert "ocupada" in r.json()["detail"]
    # quien no tiene permiso recibe su 403 de siempre, no el 503 (los permisos se revisan antes del lugar)
    assert atleta_de_coach.post("/ai/generate-plan-template/", json=cuerpo).status_code == 403
    ocupado.close()


# ------------------------------------------------------------------ la pantalla de Atletas

def test_atletas_muestra_el_ultimo_wod_de_cada_uno_sin_leer_todo_el_historial(coach, grupo):
    g, ana, beto = grupo
    _con_wod(coach, g, LUNES)
    _con_wod(coach, g, LUNES + timedelta(days=1))
    _terminar(ana, LUNES, 600)
    _terminar(beto, LUNES, 540)
    _terminar(ana, LUNES + timedelta(days=1), 500)    # el último de Ana, más rápido que el primero

    filas = {f["full_name"]: f for f in coach.get("/coach/leaderboard").json()}
    assert filas["Ana"]["last_wod_summary"] == "Por tiempo: 8:20"
    assert filas["Beto"]["last_wod_summary"] == "Por tiempo: 9:00"
    assert filas["Ana"]["completed_total"] == 2 and filas["Beto"]["completed_total"] == 1


def test_un_atleta_sin_wod_termina_con_el_resumen_vacio(coach, grupo):
    g, ana, beto = grupo
    filas = {f["full_name"]: f for f in coach.get("/coach/leaderboard").json()}
    assert filas["Ana"]["last_wod_summary"] is None and filas["Beto"]["completed_total"] == 0
