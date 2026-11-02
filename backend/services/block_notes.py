"""Texto libre por bloque de una sesión (`Session.block_notes`).

El coach puede escribir cada bloque de un día como un bloc de notas, sin estructurarlo en ejercicios
y series. El Calentamiento y el WOD ya tienen su propio texto (`warmup_notes` y `wod_notes`, este
último con su formato y temporizador), así que aquí van los demás bloques. El atleta ve el texto bajo
el título del bloque y lo registra con el "Terminar entrenamiento" de la sesión.
"""
from backend.core.errors import SolicitudInvalida
from backend.sanitize import clean_multiline

# Los bloques cuyo texto vive en `block_notes`. Los demás (warmup, metcon) usan sus campos de siempre.
BLOQUES_CON_TEXTO = ("strength", "weightlifting", "skills", "accessory", "main")

MAX_TEXTO_POR_BLOQUE = 2000


def limpiar_block_notes(notas: dict | None, *, actuales: dict | None = None) -> dict | None:
    """Las notas listas para guardar, o None si no queda ninguna.

    `notas` trae los bloques que se están cambiando: un texto vacío (o solo espacios) QUITA el bloque.
    Con `actuales` se parte de lo que la sesión ya tiene, así que escribir un bloque no borra los demás.
    Los valores NO pasan por la limpieza automática de los esquemas (esa solo mira campos sueltos),
    por eso se sanean aquí uno por uno. Un bloque que no admite texto es un error del cliente."""
    resultado = dict(actuales or {})
    for bloque, texto in (notas or {}).items():
        if bloque not in BLOQUES_CON_TEXTO:
            raise SolicitudInvalida(
                f"El bloque '{bloque}' no admite texto aquí (el calentamiento y el WOD tienen su propio campo)."
            )
        if texto is not None and not isinstance(texto, str):
            raise SolicitudInvalida(f"El texto del bloque '{bloque}' debe ser texto.")
        limpio = clean_multiline(texto or "", MAX_TEXTO_POR_BLOQUE)
        if limpio:
            resultado[bloque] = limpio
        else:
            resultado.pop(bloque, None)
    return resultado or None


def aplicar_block_notes(sesion, notas: dict | None) -> None:
    """Cambia SOLO los bloques indicados en `notas` (sin commit)."""
    sesion.block_notes = limpiar_block_notes(notas, actuales=sesion.block_notes)


MAX_CALENTAMIENTO = 1000  # el mismo límite que tiene warmup_notes al editarlo sesión por sesión


def validar_bloque_de_grupo(bloque: str) -> None:
    """Para la escritura masiva de un grupo: admite los bloques con texto y el calentamiento."""
    if bloque != "warmup":
        limpiar_block_notes({bloque: ""})


def aplicar_texto_de_bloque(sesion, bloque: str, texto: str) -> None:
    """Escribe el texto de UN bloque de una sesión (sin commit): el calentamiento va a su propio campo
    (`warmup_notes`) y los demás a `block_notes`. Un texto vacío lo quita."""
    if bloque == "warmup":
        sesion.warmup_notes = clean_multiline(texto or "", MAX_CALENTAMIENTO) or None
    else:
        aplicar_block_notes(sesion, {bloque: texto})
