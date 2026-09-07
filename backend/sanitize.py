import re

import bleach

_WHITESPACE_RE = re.compile(r"\s+")


def clean_text(value: str | None, max_length: int | None = None) -> str | None:
    """Sanea un texto libre antes de guardarlo: quita cualquier HTML/script (bleach, no un
    regex casero, para evitar los bypasses clásicos de strip-tags ingenuo), colapsa espacios
    repetidos, recorta y opcionalmente trunca a una longitud máxima."""
    if value is None or not isinstance(value, str):
        return value

    value = bleach.clean(value, tags=[], attributes={}, strip=True)
    value = value.replace("\x00", "")
    value = _WHITESPACE_RE.sub(" ", value).strip()

    if max_length is not None:
        value = value[:max_length]

    return value
