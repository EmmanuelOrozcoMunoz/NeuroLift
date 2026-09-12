"""Almacenamiento de imágenes (avatares, portadas de grupo, portadas de plan) en Supabase
Storage — reemplaza el disco local (backend/uploads/), que no sirve para producción: casi
ningún hosting moderno (Render, Railway, Fly.io...) tiene disco persistente, y con más de una
instancia del backend cada una vería un disco distinto.

Diseño: los buckets son PRIVADOS (nadie los lee sin firmar una URL) y la firma solo se genera
del lado del servidor, con la service_role key, DESPUÉS de que el endpoint ya validó que quien
pregunta tiene permiso de ver esa imagen — el modelo de permisos no cambia, solo dónde viven los
bytes. La DB sigue guardando únicamente el nombre del archivo (idéntico al esquema anterior),
así que no hace falta ninguna migración de datos más allá de subir los archivos que ya existan
en disco (ver migrate_uploads_to_storage.py).
"""
import os
import uuid

import requests
from dotenv import load_dotenv
from fastapi import HTTPException

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY:
    raise RuntimeError(
        "SUPABASE_URL y SUPABASE_SERVICE_ROLE_KEY deben estar en tu .env (Supabase Dashboard -> "
        "Settings -> API: 'Project URL' y el secreto 'service_role'). La service_role key tiene "
        "acceso total al proyecto — nunca la mandes al frontend, solo vive aquí en el backend."
    )

_STORAGE_URL = f"{SUPABASE_URL.rstrip('/')}/storage/v1"
_HEADERS = {
    "Authorization": f"Bearer {SUPABASE_SERVICE_ROLE_KEY}",
    "apikey": SUPABASE_SERVICE_ROLE_KEY,
}
_REQUEST_TIMEOUT_SECONDS = 20

# Buckets usados por la app — ver ensure_buckets(), llamado una vez al arrancar el backend
# (main.py), igual que models.Base.metadata.create_all() para las tablas.
AVATAR_BUCKET = "avatars"
GROUP_COVER_BUCKET = "group-covers"
PLAN_COVER_BUCKET = "plan-covers"
ALL_BUCKETS = (AVATAR_BUCKET, GROUP_COVER_BUCKET, PLAN_COVER_BUCKET)


def ensure_buckets() -> None:
    """Crea los buckets privados si todavía no existen. Idempotente: seguro de llamar en cada
    arranque del backend. Nunca falla el arranque por esto — si Supabase está teniendo un mal
    momento, mejor que la app siga sirviendo el resto de endpoints (los uploads fallarán con un
    error claro cuando de verdad se intenten, no aquí)."""
    for bucket in ALL_BUCKETS:
        try:
            resp = requests.post(
                f"{_STORAGE_URL}/bucket",
                headers=_HEADERS,
                json={"id": bucket, "name": bucket, "public": False},
                timeout=_REQUEST_TIMEOUT_SECONDS,
            )
            # 200 = creado; 400 con "already exists" = ya estaba (Supabase no expone un 409 claro
            # aquí) — cualquier otro error se registra pero no tumba el arranque del backend.
            if resp.status_code not in (200, 201) and "already exists" not in resp.text.lower():
                print(f"[storage] No se pudo asegurar el bucket '{bucket}': {resp.status_code} {resp.text}")
        except requests.exceptions.RequestException as e:
            print(f"[storage] No se pudo contactar a Supabase Storage para el bucket '{bucket}': {e}")


def upload_object(bucket: str, data: bytes, extension: str, content_type: str) -> str:
    """Sube los bytes ya saneados con un nombre 100% aleatorio (nunca derivado de la entrada del
    usuario, igual que el viejo save_avatar() en disco) y devuelve la key generada — eso es lo
    que se guarda en la columna *_filename de la BD."""
    key = f"{uuid.uuid4().hex}{extension}"
    resp = requests.post(
        f"{_STORAGE_URL}/object/{bucket}/{key}",
        headers={**_HEADERS, "Content-Type": content_type, "x-upsert": "true"},
        data=data,
        timeout=_REQUEST_TIMEOUT_SECONDS,
    )
    if resp.status_code not in (200, 201):
        raise HTTPException(status_code=502, detail="No se pudo guardar la imagen. Intenta de nuevo.")
    return key


def upload_object_as(bucket: str, key: str, data: bytes, content_type: str) -> None:
    """Como upload_object, pero con una key EXPLÍCITA en vez de generar una nueva — solo para
    migrate_uploads_to_storage.py, que necesita preservar los nombres ya guardados en la BD."""
    resp = requests.post(
        f"{_STORAGE_URL}/object/{bucket}/{key}",
        headers={**_HEADERS, "Content-Type": content_type, "x-upsert": "true"},
        data=data,
        timeout=_REQUEST_TIMEOUT_SECONDS,
    )
    if resp.status_code not in (200, 201):
        raise RuntimeError(f"Supabase Storage rechazó '{bucket}/{key}': {resp.status_code} {resp.text}")


def delete_object(bucket: str, key: str | None) -> None:
    """Borra el objeto si existe. No lanza si ya no estaba (mismo comportamiento que
    delete_avatar_if_exists antes, cuando esto era un archivo en disco)."""
    if not key:
        return
    try:
        requests.delete(f"{_STORAGE_URL}/object/{bucket}/{key}", headers=_HEADERS, timeout=_REQUEST_TIMEOUT_SECONDS)
    except requests.exceptions.RequestException:
        pass  # el archivo viejo quedaría huérfano en Storage; no es motivo para romper el request


def create_signed_url(bucket: str, key: str, expires_in: int = 60) -> str:
    """Pide una URL firmada de corta duración (el navegador la usa de inmediato, así que 60s
    sobra) para leer un objeto privado. Solo se llama DESPUÉS de que el endpoint ya comprobó que
    el usuario autenticado tiene permiso de ver esta imagen — la firma no vuelve a chequear eso,
    por eso los buckets son privados y esta función nunca se expone directo al cliente."""
    resp = requests.post(
        f"{_STORAGE_URL}/object/sign/{bucket}/{key}",
        headers=_HEADERS,
        json={"expiresIn": expires_in},
        timeout=_REQUEST_TIMEOUT_SECONDS,
    )
    if resp.status_code != 200:
        raise HTTPException(status_code=404, detail="No hay imagen.")
    signed_path = resp.json().get("signedURL")
    if not signed_path:
        raise HTTPException(status_code=404, detail="No hay imagen.")
    return f"{_STORAGE_URL}{signed_path}"
