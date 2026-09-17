import html
import re

import bleach

_WHITESPACE_RE = re.compile(r"\s+")


def clean_text(value: str | None, max_length: int | None = None) -> str | None:
    """Sanea un texto libre antes de guardarlo: quita cualquier HTML/script (bleach, no un
    regex casero, para evitar los bypasses clásicos de strip-tags ingenuo), colapsa espacios
    repetidos, recorta y opcionalmente trunca a una longitud máxima."""
    if value is None or not isinstance(value, str):
        return value

    # bleach.clean() serializa el texto que sobrevive como HTML válido, así que escapa
    # "&", "<", ">" aunque el usuario nunca haya escrito una etiqueta (p. ej. "Clean & Jerk"
    # quedaba guardado como "Clean &amp; Jerk"). Los tags peligrosos ya se quitaron como
    # elementos reales durante el parseo (strip=True), no como texto escapado, así que
    # des-escapar el resultado no reintroduce ningún tag — solo recupera el texto plano tal
    # cual lo escribió el usuario.
    value = html.unescape(bleach.clean(value, tags=[], attributes={}, strip=True))
    value = value.replace("\x00", "")
    value = _WHITESPACE_RE.sub(" ", value).strip()

    if max_length is not None:
        value = value[:max_length]

    return value
