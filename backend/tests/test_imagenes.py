"""Imágenes subidas por el usuario: JPG, PNG, WEBP y HEIC (las fotos del iPhone). Lo que se guarda siempre
es JPG, PNG o WEBP, sin metadatos y con la orientación ya aplicada."""
import asyncio
import io

import pillow_heif
import pytest
from fastapi import UploadFile
from PIL import Image

from backend import avatars, storage
from backend.avatars import AvatarRejected, rerender_and_strip_metadata

pillow_heif.register_heif_opener()


def _imagen(formato: str, tamano=(64, 48), modo="RGB", **kw) -> bytes:
    salida = io.BytesIO()
    Image.new(modo, tamano, (200, 30, 30) if modo == "RGB" else (200, 30, 30, 128)).save(salida, format=formato, **kw)
    return salida.getvalue()


HEIC = _imagen("HEIF")


def _abrir(datos: bytes) -> Image.Image:
    return Image.open(io.BytesIO(datos))


# ------------------------------------------------------------------ qué formato es

@pytest.mark.parametrize("datos,esperado", [
    (_imagen("JPEG"), "jpeg"),
    (_imagen("PNG"), "png"),
    (_imagen("WEBP"), "webp"),
    (HEIC, "heic"),
])
def test_los_formatos_permitidos_se_reconocen_por_su_contenido(datos, esperado):
    assert avatars._sniff_magic_number(datos) == esperado


def test_avif_gif_svg_y_bmp_siguen_sin_admitirse():
    avif = b"\x00\x00\x00\x1cftypavif" + b"\x00" * 16
    assert avatars._sniff_magic_number(avif) is None           # mismo contenedor que HEIC, otra marca
    assert avatars._sniff_magic_number(_imagen("GIF")) is None
    assert avatars._sniff_magic_number(_imagen("BMP")) is None
    assert avatars._sniff_magic_number(b"<svg xmlns='http://www.w3.org/2000/svg'></svg>") is None


def _subida(datos: bytes) -> UploadFile:
    return UploadFile(file=io.BytesIO(datos), filename="foto.jpg")


def test_un_heic_pasa_la_validacion_aunque_se_llame_jpg_y_un_gif_no():
    assert asyncio.run(avatars.read_and_validate_upload(_subida(HEIC))) == HEIC
    with pytest.raises(AvatarRejected, match="HEIC"):
        asyncio.run(avatars.read_and_validate_upload(_subida(_imagen("GIF"))))


# ------------------------------------------------------------------ se guarda como JPG limpio

def test_un_heic_se_guarda_como_jpg_con_el_mismo_tamano():
    limpio, extension = rerender_and_strip_metadata(HEIC)
    assert extension == ".jpg"
    imagen = _abrir(limpio)
    assert imagen.format == "JPEG" and imagen.size == (64, 48)


def test_un_heic_con_transparencia_se_aplana_sobre_blanco():
    limpio, extension = rerender_and_strip_metadata(_imagen("HEIF", modo="RGBA"))
    assert extension == ".jpg"
    assert _abrir(limpio).convert("RGB").getpixel((0, 0))[0] > 200


def test_los_metadatos_del_heic_no_sobreviven():
    exif = Image.Exif()
    exif[0x010F] = "MarcaDeLaCamara"          # Make
    con_exif = io.BytesIO()
    Image.new("RGB", (32, 32), (10, 20, 30)).save(con_exif, format="HEIF", exif=exif)
    limpio, _ = rerender_and_strip_metadata(con_exif.getvalue())
    assert b"MarcaDeLaCamara" not in limpio
    assert not _abrir(limpio).getexif()


def test_una_foto_con_orientacion_exif_se_guarda_derecha():
    """Una foto de celular guarda 'girada 90°' en el EXIF, que se borra: hay que aplicarla antes."""
    exif = Image.Exif()
    exif[0x0112] = 6                            # Orientation: girar 90° para verla derecha
    de_lado = io.BytesIO()
    Image.new("RGB", (40, 20), (10, 20, 30)).save(de_lado, format="JPEG", exif=exif)
    limpio, _ = rerender_and_strip_metadata(de_lado.getvalue())
    assert _abrir(limpio).size == (20, 40)


def test_png_y_webp_conservan_su_formato_y_un_jpg_sigue_siendo_jpg():
    assert rerender_and_strip_metadata(_imagen("PNG"))[1] == ".png"
    assert rerender_and_strip_metadata(_imagen("WEBP"))[1] == ".webp"
    assert rerender_and_strip_metadata(_imagen("JPEG"))[1] == ".jpg"


def test_una_imagen_muy_grande_se_reduce_a_1600_px():
    limpio, _ = rerender_and_strip_metadata(_imagen("PNG", tamano=(3200, 2400)))
    assert max(_abrir(limpio).size) == 1600


# ------------------------------------------------------------------ rechazos

def test_un_heic_corrupto_o_truncado_se_rechaza_con_un_mensaje_claro():
    with pytest.raises(AvatarRejected):
        rerender_and_strip_metadata(HEIC[:60])
    with pytest.raises(AvatarRejected):
        rerender_and_strip_metadata(b"\x00\x00\x00\x1cftypheic" + b"\x00" * 40)


def test_una_resolucion_enorme_se_rechaza_antes_de_decodificar(monkeypatch):
    monkeypatch.setattr(avatars, "MAX_PIXELES", 1000)
    with pytest.raises(AvatarRejected, match="resolución"):
        rerender_and_strip_metadata(HEIC)           # 64 x 48 = 3072 píxeles
    with pytest.raises(AvatarRejected, match="resolución"):
        rerender_and_strip_metadata(_imagen("PNG"))


# ------------------------------------------------------------------ por el endpoint

def test_subir_un_heic_como_foto_de_perfil_guarda_un_jpg(atleta_solo, monkeypatch):
    guardado = {}

    def falso_upload(bucket, datos, extension, content_type):
        guardado.update(datos=datos, extension=extension, content_type=content_type)
        return "foto-nueva" + extension

    monkeypatch.setattr(storage, "upload_object", falso_upload)
    monkeypatch.setattr(storage, "delete_object", lambda *a, **k: None)

    r = atleta_solo.post("/users/me/avatar", files={"file": ("IMG_0001.HEIC", HEIC, "image/heic")})
    assert r.status_code == 200, r.text
    assert guardado["extension"] == ".jpg" and guardado["content_type"] == "image/jpeg"
    assert _abrir(guardado["datos"]).format == "JPEG"


def test_subir_un_gif_o_un_archivo_cualquiera_da_400_y_dice_los_formatos(atleta_solo):
    r = atleta_solo.post("/users/me/avatar", files={"file": ("a.gif", _imagen("GIF"), "image/gif")})
    assert r.status_code == 400 and "HEIC" in r.json()["detail"]
    r = atleta_solo.post("/users/me/avatar", files={"file": ("a.heic", b"no soy una imagen" * 5, "image/heic")})
    assert r.status_code == 400
