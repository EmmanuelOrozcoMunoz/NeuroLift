"""Sube a Supabase Storage lo que haya quedado en backend/uploads/ (del almacenamiento viejo en
disco) preservando el MISMO nombre de archivo — así las columnas *_filename en la BD no necesitan
tocarse, solo cambia dónde viven los bytes.

Uso (una sola vez, antes de desplegar a un host sin disco persistente):
    venv/Scripts/python -m backend.migrate_uploads_to_storage

Seguro de correr varias veces: sube con upsert (reemplaza si ya existía) y nunca borra nada
localmente — revisa la salida y borra backend/uploads/ a mano cuando confirmes que todo llegó.
"""
from pathlib import Path

from backend import storage

_CONTENT_TYPES = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png", ".webp": "image/webp"}

_CARPETAS_A_BUCKETS = {
    "avatars": storage.AVATAR_BUCKET,
    "group_covers": storage.GROUP_COVER_BUCKET,
    "plan_covers": storage.PLAN_COVER_BUCKET,
}


def main() -> None:
    uploads_dir = Path(__file__).resolve().parent / "uploads"
    if not uploads_dir.is_dir():
        print("No hay backend/uploads/ — nada que migrar.")
        return

    storage.ensure_buckets()
    total = 0
    for carpeta, bucket in _CARPETAS_A_BUCKETS.items():
        origen = uploads_dir / carpeta
        if not origen.is_dir():
            continue
        for archivo in sorted(origen.iterdir()):
            if not archivo.is_file():
                continue
            content_type = _CONTENT_TYPES.get(archivo.suffix.lower(), "application/octet-stream")
            storage.upload_object_as(bucket, archivo.name, archivo.read_bytes(), content_type)
            print(f"  {carpeta}/{archivo.name} -> bucket '{bucket}'")
            total += 1

    print(f"\nListo: {total} archivo(s) subido(s) a Supabase Storage.")
    if total:
        print("Verifica en el Dashboard (Storage) y luego puedes borrar backend/uploads/ a mano.")


if __name__ == "__main__":
    main()
