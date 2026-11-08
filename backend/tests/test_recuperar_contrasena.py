"""Recuperar la contraseña con un enlace enviado por correo."""
from urllib.parse import parse_qs, urlparse

import pytest

from backend.services import correo
from backend.tests.conftest import PASSWORD

NUEVA = "OtraClave987!"


@pytest.fixture
def enviados(monkeypatch):
    """Intercepta los correos: cada uno queda como (destino, texto)."""
    lista = []
    monkeypatch.setattr(correo, "enviar_correo", lambda para, asunto, html, texto: lista.append((para, texto)) or True)
    return lista


def _token(enviados):
    texto = enviados[-1][1]
    enlace = next(p for p in texto.split() if p.startswith("http"))
    return parse_qs(urlparse(enlace).query)["token"][0]


def test_pide_el_enlace_y_cambia_la_contrasena(client, coach, enviados):
    r = client.post("/auth/forgot-password", json={"email": coach.email})
    assert r.status_code == 200
    assert [d for d, _ in enviados] == [coach.email]

    r = client.post("/auth/reset-password", json={"token": _token(enviados), "password": NUEVA})
    assert r.status_code == 200, r.text
    assert client.post("/auth/login", json={"email": coach.email, "password": PASSWORD}).status_code == 401
    assert client.post("/auth/login", json={"email": coach.email, "password": NUEVA}).status_code == 200


def test_responde_igual_si_el_correo_no_existe_y_no_envia_nada(client, enviados):
    existente = client.post("/auth/forgot-password", json={"email": "nadie-existe@example.com"})
    assert existente.status_code == 200 and enviados == []
    assert "enviamos" in existente.json()["message"]


def test_el_enlace_sirve_una_sola_vez(client, coach, enviados):
    client.post("/auth/forgot-password", json={"email": coach.email})
    token = _token(enviados)
    assert client.post("/auth/reset-password", json={"token": token, "password": NUEVA}).status_code == 200
    r = client.post("/auth/reset-password", json={"token": token, "password": "Tercera12345"})
    assert r.status_code == 400
    assert client.post("/auth/login", json={"email": coach.email, "password": NUEVA}).status_code == 200


def test_cambiar_la_contrasena_cierra_las_sesiones_abiertas(client, coach, enviados):
    assert coach.get("/auth/me").status_code == 200
    client.post("/auth/forgot-password", json={"email": coach.email})
    client.post("/auth/reset-password", json={"token": _token(enviados), "password": NUEVA})
    assert coach.get("/auth/me").status_code == 401


def test_un_token_de_sesion_no_sirve_para_restablecer_y_viceversa(client, coach, enviados):
    sesion = coach.headers["Authorization"].split()[1]
    assert client.post("/auth/reset-password", json={"token": sesion, "password": NUEVA}).status_code == 400

    client.post("/auth/forgot-password", json={"email": coach.email})
    reset = _token(enviados)
    assert client.get("/auth/me", headers={"Authorization": f"Bearer {reset}"}).status_code == 401


def test_rechaza_tokens_basura_y_contrasenas_cortas(client, coach, enviados):
    assert client.post("/auth/reset-password", json={"token": "x" * 40, "password": NUEVA}).status_code == 400
    client.post("/auth/forgot-password", json={"email": coach.email})
    assert client.post("/auth/reset-password", json={"token": _token(enviados), "password": "corta"}).status_code == 422
