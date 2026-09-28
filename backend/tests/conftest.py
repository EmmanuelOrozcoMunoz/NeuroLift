"""Fixtures compartidas. Las pruebas corren contra un Postgres DESCARTABLE.

Se exige `TEST_DATABASE_URL` a propósito: si usáramos `DATABASE_URL`, `load_dotenv()` podría
apuntar las pruebas a la base de Dev/QA/PRD del `.env` y llenarla de cuentas de prueba. Sin esa
variable (o si apunta a Supabase) la suite entera se salta.

Cómo correrlas en local:
    TEST_DATABASE_URL=postgresql://postgres:postgres@localhost:5432/postgres pytest
"""
import os
import uuid

import pytest

_TEST_DB = os.getenv("TEST_DATABASE_URL", "")
_SEGURA = bool(_TEST_DB) and "supabase" not in _TEST_DB

if _SEGURA:
    # Antes de importar backend.*: config, database y storage leen el entorno al importarse.
    # Se fijan (no setdefault) para que ni el .env ni un entorno real se cuelen en las pruebas.
    os.environ["DATABASE_URL"] = _TEST_DB
    os.environ["JWT_SECRET_KEY"] = "pruebas-no-es-un-secreto-pero-de-32-caracteres"
    os.environ["SUPABASE_URL"] = "https://dummy.supabase.co"
    os.environ["SUPABASE_SERVICE_ROLE_KEY"] = "pruebas-no-es-una-llave"
    os.environ["ENVIRONMENT"] = "development"


def pytest_collection_modifyitems(config, items):
    if _SEGURA:
        return
    motivo = pytest.mark.skip(
        reason="Define TEST_DATABASE_URL con un Postgres descartable (nunca Supabase) para correr las pruebas."
    )
    for item in items:
        item.add_marker(motivo)


PASSWORD = "password123"


@pytest.fixture(scope="session")
def client():
    from fastapi.testclient import TestClient

    from backend import models
    from backend.core.security import limiter
    from backend.database import engine
    from backend.main import app

    models.Base.metadata.create_all(bind=engine)
    limiter.enabled = False  # los límites por IP (3 registros/hora) romperían la suite
    # Sin `with`: no corre el lifespan, así que no se llama a Supabase Storage.
    return TestClient(app)


class Cuenta:
    """Una cuenta ya autenticada, con helpers para no repetir headers en cada llamada."""

    def __init__(self, client, email, token, datos):
        self.client, self.email, self.datos = client, email, datos
        self.headers = {"Authorization": f"Bearer {token}"}

    @property
    def id(self):
        return self.datos["id"]

    def get(self, ruta, **kw):
        return self.client.get(ruta, headers=self.headers, **kw)

    def post(self, ruta, **kw):
        return self.client.post(ruta, headers=self.headers, **kw)

    def put(self, ruta, **kw):
        return self.client.put(ruta, headers=self.headers, **kw)

    def delete(self, ruta, **kw):
        return self.client.delete(ruta, headers=self.headers, **kw)


def _login(client, email) -> Cuenta:
    r = client.post("/auth/login", json={"email": email, "password": PASSWORD})
    assert r.status_code == 200, r.text
    token = r.json()["access_token"]
    me = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"}).json()
    return Cuenta(client, email, token, me)


def _email(prefijo):
    return f"{prefijo}-{uuid.uuid4().hex[:10]}@example.com"


@pytest.fixture
def coach(client) -> Cuenta:
    """Coach independiente (activo, con prueba gratis)."""
    email = _email("coach")
    r = client.post("/boxes/register-coach", json={"full_name": "Coach Prueba", "email": email, "password": PASSWORD})
    assert r.status_code == 200, r.text
    return _login(client, email)


@pytest.fixture
def codigo_coach(coach) -> str:
    return coach.get("/boxes/me").json()["invite_code"]


@pytest.fixture
def atleta_de_coach(client, codigo_coach) -> Cuenta:
    """Atleta que se registró con el código del coach (tiene coach personal)."""
    email = _email("atleta")
    r = client.post(
        "/auth/register",
        json={"email": email, "full_name": "Atleta Prueba", "password": PASSWORD, "invite_code": codigo_coach},
    )
    assert r.status_code == 200, r.text
    return _login(client, email)


@pytest.fixture
def atleta_solo(client) -> Cuenta:
    """Atleta que se registró sin código (cuenta personal gratuita)."""
    email = _email("solo")
    r = client.post("/auth/register", json={"email": email, "full_name": "Atleta Solo", "password": PASSWORD})
    assert r.status_code == 200, r.text
    return _login(client, email)


def _admin(client) -> Cuenta:
    """Los admins no se registran por la API: se crea uno directo en la BD de pruebas."""
    from backend import models
    from backend.core.security import get_password_hash
    from backend.database import SessionLocal

    email = _email("admin")
    with SessionLocal() as db:
        db.add(models.User(email=email, full_name="Admin Prueba", hashed_password=get_password_hash(PASSWORD), role="admin"))
        db.commit()
    return _login(client, email)


def crear_box_activo(client) -> Cuenta:
    """Dueño de un box ya aprobado (el registro público lo deja pendiente hasta que un admin lo activa)."""
    email = _email("dueno")
    r = client.post(
        "/boxes/register",
        json={"box_name": "Box de Prueba", "city": "Bogotá", "owner_name": "Dueño Prueba", "email": email, "password": PASSWORD},
    )
    assert r.status_code == 200, r.text
    box_id = _login(client, email).datos["box"]["id"]
    aprobado = _admin(client).put(f"/admin/boxes/{box_id}/status", json={"status": "active"})
    assert aprobado.status_code == 200, aprobado.text
    return _login(client, email)


@pytest.fixture
def dueno_de_box(client) -> Cuenta:
    return crear_box_activo(client)


def crear_atleta_de_box(client, dueno) -> Cuenta:
    codigo = dueno.get("/boxes/me").json()["invite_code"]
    email = _email("atletabox")
    r = client.post(
        "/auth/register",
        json={"email": email, "full_name": "Atleta de Box", "password": PASSWORD, "invite_code": codigo},
    )
    assert r.status_code == 200, r.text
    return _login(client, email)


@pytest.fixture
def atleta_de_box(client, dueno_de_box) -> Cuenta:
    return crear_atleta_de_box(client, dueno_de_box)
