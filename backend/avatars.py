"""Validación y saneo de imágenes subidas por el usuario (avatar, portada de grupo/plan).

Implementa las medidas exigidas para cualquier upload de imagen:

1. Validación de entrada: tamaño estricto ANTES de decodificar nada, y verificación del
   "magic number" real del archivo (nunca del Content-Type ni de la extensión que mandó el
   cliente) contra una lista blanca de formatos.
2. Procesamiento: la imagen se decodifica con Pillow y se reconstruye pixel por pixel en un
   lienzo nuevo — esto destruye cualquier payload oculto en la estructura del archivo original
   (polyglots, chunks manipulados, etc.) y de paso elimina TODOS los metadatos (EXIF, GPS,
   perfiles ICC, comentarios) porque el objeto nuevo no hereda el `.info` del original.

El almacenamiento de los bytes ya saneados (Supabase Storage, con nombre aleatorio uuid4) vive
en backend/storage.py, no aquí — este módulo solo se preocupa de que el contenido sea una
imagen válida y esté limpia, sin importar dónde termine guardándose.
"""
from io import BytesIO

from fastapi import HTTPException, UploadFile
from PIL import Image, UnidentifiedImageError

MAX_AVATAR_BYTES = 5 * 1024 * 1024  # 5 MB

# Firmas binarias reales de cada formato permitido (independientes del Content-Type que
# declare el cliente, que no es de fiar). WEBP es un contenedor RIFF: los primeros 4 bytes
# son "RIFF", y "WEBP" aparece en los bytes 8-11.
_MAGIC_NUMBERS: dict[str, tuple[bytes, ...]] = {
    "jpeg": (b"\xff\xd8\xff",),
    "png": (b"\x89PNG\r\n\x1a\n",),
    "webp": (b"RIFF",),  # se confirma con la marca "WEBP" en el offset 8 (ver abajo)
}

# Formato Pillow -> extensión de archivo permitida (lista blanca; nunca se usa la extensión
# que mandó el cliente).
_ALLOWED_OUTPUT: dict[str, tuple[str, str]] = {
    # pillow_format: (extension, save_format)
    "JPEG": (".jpg", "JPEG"),
    "PNG": (".png", "PNG"),
    "WEBP": (".webp", "WEBP"),
}


def _sniff_magic_number(data: bytes) -> str | None:
    """Identifica el formato real por su firma binaria. Devuelve None si no coincide con
    ninguno de los formatos de la lista blanca (jpg/png/webp)."""
    if data.startswith(_MAGIC_NUMBERS["jpeg"][0]):
        return "jpeg"
    if data.startswith(_MAGIC_NUMBERS["png"][0]):
        return "png"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "webp"
    return None


class AvatarRejected(HTTPException):
    def __init__(self, detail: str):
        super().__init__(status_code=400, detail=detail)


async def read_and_validate_upload(file: UploadFile) -> bytes:
    """Lee el archivo del request respetando el límite de tamaño DESDE la lectura misma
    (no solo mirando Content-Length, que el cliente puede falsear u omitir) y confirma que
    el contenido real es uno de los formatos de imagen permitidos."""
    # +1: si llega justo ese byte de más, sabemos que el archivo real excede el límite,
    # sin necesidad de haberlo leído completo primero (evita el DoS de subir un archivo enorme).
    data = await file.read(MAX_AVATAR_BYTES + 1)
    if len(data) > MAX_AVATAR_BYTES:
        raise AvatarRejected(f"La imagen supera el límite de {MAX_AVATAR_BYTES // (1024 * 1024)} MB.")
    if not data:
        raise AvatarRejected("El archivo está vacío.")

    if _sniff_magic_number(data) is None:
        raise AvatarRejected(
            "Formato no permitido. Solo se aceptan imágenes JPG, PNG o WEBP (se valida el "
            "contenido real del archivo, no la extensión)."
        )

    return data


def rerender_and_strip_metadata(data: bytes) -> tuple[bytes, str]:
    """Decodifica la imagen y la reconstruye en un lienzo completamente nuevo, copiando solo
    los píxeles. Esto es lo que de verdad neutraliza un archivo malicioso: cualquier código o
    estructura oculta en el archivo original (que no sea el propio mapa de píxeles) desaparece,
    incluyendo EXIF/GPS/ICC/comentarios, porque el objeto Image nuevo no hereda el `.info` del
    original. Devuelve (bytes_listos_para_guardar, extension_de_archivo)."""
    try:
        with Image.open(BytesIO(data)) as probe:
            probe.verify()  # valida la integridad estructural; lanza si el archivo está corrupto
    except (UnidentifiedImageError, OSError, ValueError):
        raise AvatarRejected("El archivo no es una imagen válida o está corrupto.")
    except Image.DecompressionBombError:
        raise AvatarRejected("La imagen es demasiado grande en resolución.")

    # verify() deja el objeto inutilizable para seguir leyendo: se reabre para decodificar
    # los píxeles de verdad.
    try:
        with Image.open(BytesIO(data)) as original:
            original.load()
            pillow_format = original.format  # el que Pillow detectó de verdad, no el declarado
            if pillow_format not in _ALLOWED_OUTPUT:
                raise AvatarRejected("Formato de imagen no soportado.")

            extension, save_format = _ALLOWED_OUTPUT[pillow_format]

            # JPEG no soporta transparencia: se aplana sobre fondo blanco. PNG/WEBP sí, así
            # que se preserva el canal alfa si lo había.
            if save_format == "JPEG":
                base = Image.new("RGB", original.size, (255, 255, 255))
                rgba = original.convert("RGBA")
                base.paste(rgba, mask=rgba.split()[3])
                clean = base
            else:
                source = original.convert("RGBA") if "A" in original.getbands() else original.convert("RGB")
                clean = Image.new(source.mode, source.size)
                clean.putdata(list(source.getdata()))  # solo píxeles: cero metadatos heredados

            # Límite razonable de resolución: además de proteger memoria/disco, recorta
            # imágenes absurdamente grandes que no aportan nada a una foto de perfil.
            clean.thumbnail((1600, 1600), Image.LANCZOS)

            buffer = BytesIO()
            save_kwargs = {"quality": 85, "optimize": True} if save_format in ("JPEG", "WEBP") else {}
            clean.save(buffer, format=save_format, **save_kwargs)
            return buffer.getvalue(), extension
    except AvatarRejected:
        raise
    except Image.DecompressionBombError:
        raise AvatarRejected("La imagen es demasiado grande en resolución.")
    except (UnidentifiedImageError, OSError, ValueError):
        raise AvatarRejected("No se pudo procesar la imagen.")
