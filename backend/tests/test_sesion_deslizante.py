"""La sesión dura 30 días y se renueva mientras se use (POST /auth/refresh)."""
import jwt

from backend.core.config import ACCESS_TOKEN_EXPIRE_MINUTES, ALGORITHM, SECRET_KEY


def _exp(token):
    return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])["exp"]


def test_el_token_dura_30_dias():
    assert ACCESS_TOKEN_EXPIRE_MINUTES == 60 * 24 * 30


def test_refresh_entrega_un_token_valido_con_la_misma_identidad(client, coach):
    r = client.post("/auth/refresh", headers=coach.headers)
    assert r.status_code == 200, r.text
    nuevo = r.json()["access_token"]
    assert jwt.decode(nuevo, SECRET_KEY, algorithms=[ALGORITHM])["id"] == coach.id
    assert client.get("/auth/me", headers={"Authorization": f"Bearer {nuevo}"}).json()["id"] == coach.id


def test_refresh_sin_token_o_con_sesion_cerrada_no_renueva(client, coach):
    assert client.post("/auth/refresh").status_code == 401
    assert coach.post("/auth/logout").status_code == 200
    assert coach.post("/auth/refresh").status_code == 401   # el token revocado no se puede renovar
