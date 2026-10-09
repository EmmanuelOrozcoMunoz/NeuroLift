import html
import re

import bleach

_WHITESPACE_RE = re.compile(r"\s+")
# Para texto largo: el espacio en blanco de una línea (todo MENOS el salto de línea), los
# separadores de línea que no son "\n" y las rachas de líneas en blanco.
_ESPACIOS_EN_LINEA_RE = re.compile(r"[^\S\n]+")
_SALTOS_RE = re.compile(r"\r\n?|[  \x0b\x0c]")
_LINEAS_EN_BLANCO_RE = re.compile(r"\n{3,}")


def _sin_html(value: str) -> str:
    """Quita cualquier HTML/script (bleach, no un regex casero, para evitar los bypasses clásicos
    de strip-tags ingenuo) y los caracteres nulos."""
    # bleach.clean() serializa el texto que sobrevive como HTML válido, así que escapa
    # "&", "<", ">" aunque el usuario nunca haya escrito una etiqueta (p. ej. "Clean & Jerk"
    # quedaba guardado como "Clean &amp; Jerk"). Los tags peligrosos ya se quitaron como
    # elementos reales durante el parseo (strip=True), no como texto escapado, así que
    # des-escapar el resultado no reintroduce ningún tag — solo recupera el texto plano tal
    # cual lo escribió el usuario.
    return html.unescape(bleach.clean(value, tags=[], attributes={}, strip=True)).replace("\x00", "")


def clean_text(value: str | None, max_length: int | None = None) -> str | None:
    """Sanea un texto libre de UNA línea (nombres, correos, títulos) antes de guardarlo: quita
    cualquier HTML/script, colapsa espacios y saltos de línea en un solo espacio, recorta y
    opcionalmente trunca a una longitud máxima. Para texto largo de varias líneas, ver
    clean_multiline."""
    if value is None or not isinstance(value, str):
        return value

    value = _WHITESPACE_RE.sub(" ", _sin_html(value)).strip()

    if max_length is not None:
        value = value[:max_length]

    return value


def clean_multiline(value: str | None, max_length: int | None = None) -> str | None:
    """Como clean_text pero para TEXTO LARGO que alguien escribe en varias líneas (un WOD, las
    pautas de calentamiento, una nota): conserva los saltos de línea. Quita el HTML igual de
    seguro que clean_text, pero solo colapsa los espacios DENTRO de cada línea, quita los de los
    extremos de cada línea y deja como mucho UNA línea en blanco seguida, para que un esquema como
    "21-15-9 / Thrusters / Pull-ups" o una lista llegue como se escribió."""
    if value is None or not isinstance(value, str):
        return value

    value = _SALTOS_RE.sub("\n", _sin_html(value))
    lineas = (_ESPACIOS_EN_LINEA_RE.sub(" ", linea).strip() for linea in value.split("\n"))
    value = _LINEAS_EN_BLANCO_RE.sub("\n\n", "\n".join(lineas)).strip()

    if max_length is not None:
        value = value[:max_length]

    return value
