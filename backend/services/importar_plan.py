"""Importar un plan desde un documento (PDF, Word o Excel).

Dos pasos, sin guardar nada en el primero:
1. `leer_documento` saca el texto del archivo y `interpretar_documento` se lo pasa a la IA, que lo
   devuelve como semanas/días/ejercicios. `armar_vista_previa` lo limpia con las mismas reglas que
   la generación con IA (ai_salida) y lo resume para que el coach lo revise.
2. `crear_plan_importado` repite esa limpieza sobre el documento ya interpretado (nunca se confía en
   lo que mande el cliente) y crea la plantilla en BORRADOR: el coach la termina de ajustar en el
   editor de planes y la asigna o la publica cuando quiera.

El texto del archivo es dato de un tercero: se limita su tamaño, se lee con librerías que no
ejecutan nada (sin macros, sin fórmulas) y a la IA se le entrega como dato, nunca como instrucción.
"""
import io
import logging
import zipfile
from dataclasses import dataclass, field
from datetime import timedelta

from sqlalchemy.orm import Session

from backend import ai_agent, models
from backend.core.errors import SolicitudInvalida
from backend.services.ai_mesocycles import _crear_sesion
from backend.services.ai_salida import SesionLimpia, limpiar_sesion
from backend.services.plans import PLAN_EPOCH

logger = logging.getLogger("neurolift.importar_plan")

MAX_BYTES = 5 * 1024 * 1024           # tamaño del archivo
MAX_PAGINAS = 80                      # PDF
MAX_HOJAS = 12                        # Excel
MAX_FILAS_POR_HOJA = 3000
MAX_CARACTERES = 80_000               # texto que se le entrega a la IA
MAX_DESCOMPRIMIDO = 60 * 1024 * 1024  # un .docx/.xlsx es un zip: evita las "bombas" de compresión
MAX_ARCHIVOS_EN_ZIP = 2000

MAX_SEMANAS = 52
MAX_SESIONES_POR_SEMANA = 7
MAX_SESIONES = 150                    # lo que cabe razonablemente en una sola respuesta de la IA

# Si el documento no dice en qué día de la semana cae cada sesión: los días repartidos según cuántas
# sesiones tiene la semana (lunes = 0).
_DIAS_POR_CANTIDAD = {
    1: (0,), 2: (0, 3), 3: (0, 2, 4), 4: (0, 1, 3, 4), 5: (0, 1, 2, 3, 4), 6: (0, 1, 2, 3, 4, 5),
    7: (0, 1, 2, 3, 4, 5, 6),
}

NIVELES = ("Principiante", "Intermedio", "Avanzado")


class DocumentoInvalido(SolicitudInvalida):
    """El archivo no sirve (tipo, tamaño, vacío, sin texto...). El mensaje se le muestra al coach."""


# ------------------------------------------------------------------ leer el archivo

def tipo_de_archivo(contenido: bytes) -> str:
    """"pdf", "docx" o "xlsx" según lo que el archivo ES (no según cómo se llame)."""
    if contenido[:5] == b"%PDF-":
        return "pdf"
    if contenido[:4] == b"PK\x03\x04":
        try:
            with zipfile.ZipFile(io.BytesIO(contenido)) as z:
                infos = z.infolist()
                if len(infos) > MAX_ARCHIVOS_EN_ZIP or sum(i.file_size for i in infos) > MAX_DESCOMPRIMIDO:
                    raise DocumentoInvalido("El archivo es demasiado grande una vez descomprimido.")
                nombres = {i.filename for i in infos}
        except zipfile.BadZipFile:
            raise DocumentoInvalido("El archivo está dañado o no es un documento válido.")
        if "xl/vbaProject.bin" in nombres or "word/vbaProject.bin" in nombres:
            raise DocumentoInvalido("El archivo contiene macros. Guárdalo sin macros (.xlsx o .docx) e inténtalo de nuevo.")
        if "word/document.xml" in nombres:
            return "docx"
        if "xl/workbook.xml" in nombres:
            return "xlsx"
    raise DocumentoInvalido("Formato no soportado. Sube un PDF, un Word (.docx) o un Excel (.xlsx).")


def _texto_pdf(contenido: bytes) -> str:
    from pypdf import PdfReader
    from pypdf.errors import PyPdfError

    try:
        lector = PdfReader(io.BytesIO(contenido), strict=False)
        if lector.is_encrypted:
            raise DocumentoInvalido("El PDF está protegido con contraseña. Quítale la protección e inténtalo de nuevo.")
        if len(lector.pages) > MAX_PAGINAS:
            raise DocumentoInvalido(f"El PDF tiene demasiadas páginas (máximo {MAX_PAGINAS}).")
        paginas = [(pagina.extract_text() or "") for pagina in lector.pages]
    except DocumentoInvalido:
        raise
    except (PyPdfError, ValueError, KeyError, TypeError, RecursionError) as e:
        logger.warning("PDF ilegible: %s", e)
        raise DocumentoInvalido("No se pudo leer el PDF: está dañado o tiene un formato raro.")
    return "\n\n".join(paginas)


def _texto_docx(contenido: bytes) -> str:
    from docx import Document
    from docx.table import Table
    from docx.text.paragraph import Paragraph

    try:
        doc = Document(io.BytesIO(contenido))
    except Exception as e:  # noqa: BLE001 — cualquier fallo de la librería: el archivo no sirve
        logger.warning("Word ilegible: %s", e)
        raise DocumentoInvalido("No se pudo leer el documento de Word: está dañado.")

    lineas: list[str] = []
    # En el orden en que aparecen en el documento (párrafos y tablas mezclados)
    for hijo in doc.element.body.iterchildren():
        etiqueta = hijo.tag.rsplit("}", 1)[-1]
        if etiqueta == "p":
            texto = Paragraph(hijo, doc).text.strip()
            if texto:
                lineas.append(texto)
        elif etiqueta == "tbl":
            for fila in Table(hijo, doc).rows:
                celdas: list[str] = []
                for celda in fila.cells:
                    texto = " ".join(celda.text.split())
                    if texto and (not celdas or celdas[-1] != texto):  # las celdas combinadas se repiten
                        celdas.append(texto)
                if celdas:
                    lineas.append(" | ".join(celdas))
    return "\n".join(lineas)


def _texto_xlsx(contenido: bytes) -> str:
    from openpyxl import load_workbook

    try:
        libro = load_workbook(io.BytesIO(contenido), read_only=True, data_only=True)
    except Exception as e:  # noqa: BLE001
        logger.warning("Excel ilegible: %s", e)
        raise DocumentoInvalido("No se pudo leer el Excel: está dañado.")

    bloques: list[str] = []
    try:
        for hoja in libro.worksheets[:MAX_HOJAS]:
            filas: list[str] = []
            for i, fila in enumerate(hoja.iter_rows(values_only=True)):
                if i >= MAX_FILAS_POR_HOJA:
                    break
                celdas = [str(c).strip() for c in fila if c is not None and str(c).strip()]
                if celdas:
                    filas.append(" | ".join(celdas))
            if filas:
                bloques.append(f"Hoja: {hoja.title}\n" + "\n".join(filas))
    finally:
        libro.close()
    return "\n\n".join(bloques)


def leer_documento(contenido: bytes) -> str:
    """El texto de un PDF, Word o Excel, o `DocumentoInvalido` con un mensaje claro para el coach."""
    if not contenido:
        raise DocumentoInvalido("El archivo está vacío.")
    if len(contenido) > MAX_BYTES:
        raise DocumentoInvalido(f"El archivo es demasiado grande (máximo {MAX_BYTES // (1024 * 1024)} MB).")
    tipo = tipo_de_archivo(contenido)
    texto = {"pdf": _texto_pdf, "docx": _texto_docx, "xlsx": _texto_xlsx}[tipo](contenido).strip()
    if len(texto) < 30:
        raise DocumentoInvalido(
            "No se encontró texto en el archivo. Si es un PDF escaneado o una foto, no se puede leer: "
            "sube una versión con texto (Word, Excel o un PDF exportado)."
        )
    if len(texto) > MAX_CARACTERES:
        raise DocumentoInvalido(
            "El documento es demasiado largo para importarlo de una vez. Divídelo en partes (por ejemplo, "
            "por bloques de semanas) e impórtalas por separado."
        )
    return texto


# ------------------------------------------------------------------ interpretar y limpiar

def interpretar_documento(texto: str) -> dict:
    """El documento como semanas/días/ejercicios, o `DocumentoInvalido` si la IA no pudo."""
    respuesta = ai_agent.parse_training_document(texto)
    if not isinstance(respuesta, dict) or respuesta.get("error"):
        raise DocumentoInvalido((respuesta or {}).get("error") or "No se pudo interpretar el documento.")
    uso = respuesta.pop("_uso", None)
    if uso:
        logger.info("Importar documento: tokens entrada=%s salida=%s", uso.get("tokens_prompt"), uso.get("tokens_salida"))
    return respuesta


@dataclass
class DiaImportado:
    semana: int
    dia_de_semana: int          # 0 = lunes
    desplazamiento: int         # días desde el primer día del plan
    etiqueta: str | None
    sesion: SesionLimpia


@dataclass
class PlanImportado:
    nombre: str | None
    descripcion: str | None
    disciplina: str | None
    nivel: str | None
    dias: list[DiaImportado] = field(default_factory=list)
    advertencias: list[str] = field(default_factory=list)

    @property
    def semanas(self) -> int:
        return max((d.semana for d in self.dias), default=0)


def _entero(valor, minimo: int, maximo: int) -> int | None:
    if isinstance(valor, bool) or not isinstance(valor, (int, float)):
        return None
    numero = int(valor)
    return numero if minimo <= numero <= maximo else None


def _texto(valor, largo: int) -> str | None:
    if not isinstance(valor, str):
        return None
    limpio = " ".join(valor.split())
    return limpio[:largo] or None


def _dias_de_la_semana(sesiones: list[dict]) -> list[int]:
    """El día de la semana (0 = lunes) de cada sesión: el que dice el documento y, donde no lo dice
    (o se repite), un día libre siguiendo el reparto habitual para esa cantidad de sesiones."""
    tomados: set[int] = set()
    dias: list[int | None] = []
    for sesion in sesiones:
        dia = _entero(sesion.get("weekday"), 0, 6)
        if dia is not None and dia not in tomados:
            tomados.add(dia)
            dias.append(dia)
        else:
            dias.append(None)
    habitual = _DIAS_POR_CANTIDAD[max(1, min(7, len(sesiones)))]
    libres = [d for d in habitual if d not in tomados] + [d for d in range(7) if d not in tomados and d not in habitual]
    return [dia if dia is not None else libres.pop(0) for dia in dias]


def armar_plan(documento: dict) -> PlanImportado:
    """Limpia el documento interpretado y le pone a cada sesión su día. Lanza `DocumentoInvalido` si no
    queda ninguna sesión con ejercicios o el plan es demasiado grande."""
    if not isinstance(documento, dict):
        raise DocumentoInvalido("El documento interpretado no tiene el formato esperado.")
    semanas = documento.get("weeks")
    semanas = [s for s in semanas if isinstance(s, dict)] if isinstance(semanas, list) else []

    nivel = _texto(documento.get("level"), 20)
    plan = PlanImportado(
        nombre=_texto(documento.get("plan_name"), 100),
        descripcion=_texto(documento.get("description"), 2000),
        disciplina=_texto(documento.get("discipline"), 50),
        nivel=next((n for n in NIVELES if nivel and n.lower() == nivel.lower()), None),
    )

    # Cada semana con su número (el del documento si es válido y no se repite; si no, el siguiente)
    por_semana: dict[int, list[dict]] = {}
    for semana in semanas:
        numero = _entero(semana.get("week_number"), 1, MAX_SEMANAS)
        if numero is None or numero in por_semana:
            numero = max(por_semana, default=0) + 1
        if numero > MAX_SEMANAS:
            raise DocumentoInvalido(f"El plan tiene más de {MAX_SEMANAS} semanas.")
        crudas = semana.get("sessions")
        por_semana[numero] = [s for s in crudas if isinstance(s, dict)] if isinstance(crudas, list) else []

    if sum(len(v) for v in por_semana.values()) > MAX_SESIONES:
        raise DocumentoInvalido(
            f"El plan tiene demasiadas sesiones (máximo {MAX_SESIONES}). Divide el documento e impórtalo por partes."
        )

    # Se numeran de nuevo 1, 2, 3... en orden (por si el documento se saltó semanas) y cada sesión
    # recibe su día de la semana.
    dias_crudos: list[tuple[int, int, dict]] = []
    for semana_nueva, numero in enumerate(sorted(por_semana), start=1):
        sesiones = por_semana[numero]
        if len(sesiones) > MAX_SESIONES_POR_SEMANA:
            plan.advertencias.append(
                f"Semana {numero}: tenía {len(sesiones)} sesiones; solo se importan las primeras {MAX_SESIONES_POR_SEMANA}."
            )
            sesiones = sesiones[:MAX_SESIONES_POR_SEMANA]
        for sesion, dia in zip(sesiones, _dias_de_la_semana(sesiones)):
            dias_crudos.append((semana_nueva, dia, sesion))

    if not dias_crudos:
        raise DocumentoInvalido("No se encontró ningún plan de entrenamiento en el documento.")

    base = min(d for semana, d, _ in dias_crudos if semana == 1)
    for semana, dia, cruda in sorted(dias_crudos, key=lambda t: (t[0], t[1])):
        desplazamiento = (semana - 1) * 7 + dia - base
        limpia = limpiar_sesion(cruda, PLAN_EPOCH + timedelta(days=desplazamiento), prs=None, conservar_kg=True)
        if not limpia.ejercicios and not limpia.wod and not limpia.calentamiento:
            plan.advertencias.append(f"Semana {semana}: se omitió un día sin contenido ({_texto(cruda.get('day_label'), 60) or 'sin nombre'}).")
            continue
        plan.advertencias.extend(f"Semana {semana}: {a}" for a in limpia.advertencias)
        plan.dias.append(DiaImportado(semana, dia, desplazamiento, _texto(cruda.get("day_label"), 60), limpia))

    if not plan.dias:
        raise DocumentoInvalido("No se encontró ningún día con ejercicios en el documento.")
    return plan


def vista_previa(plan: PlanImportado) -> dict:
    """Lo que se le muestra al coach para que confirme: nada de esto se ha guardado."""
    return {
        "name": plan.nombre,
        "description": plan.descripcion,
        "discipline": plan.disciplina,
        "level": plan.nivel,
        "weeks_count": plan.semanas,
        "sessions_count": len(plan.dias),
        "warnings": plan.advertencias,
        "days": [
            {
                "week": d.semana,
                "weekday": d.dia_de_semana,
                "label": d.etiqueta,
                "warmup": d.sesion.calentamiento,
                "block_order": d.sesion.orden_de_bloques,
                "wod": (
                    {"format": d.sesion.wod["format"], "time_cap_seconds": d.sesion.wod["time_cap_seconds"],
                     "description": d.sesion.wod["notes"]}
                    if d.sesion.wod else None
                ),
                "exercises": [
                    {
                        "name": e.nombre,
                        "block": e.bloque,
                        "sets": len(e.filas_a_guardar()),
                        "reps": e.filas_a_guardar()[0].reps,
                        "summary": _resumen_de_carga(e),
                        "note": e.nota,
                    }
                    for e in d.sesion.ejercicios
                ],
            }
            for d in plan.dias
        ],
    }


def _resumen_de_carga(ejercicio) -> str:
    """"3 x 5 @ 80 %", "5-3-1" o "4 x 8 @ 60 kg · RPE 8": lo prescrito en una línea."""
    filas = ejercicio.filas_a_guardar()
    cargas = {(f.peso, f.porcentaje) for f in filas}
    reps = [f.reps for f in filas]

    def carga(peso, porcentaje) -> str:
        if porcentaje is not None:
            return f"{porcentaje:g} %"
        return f"{peso:g} kg" if peso is not None else ""

    if len(set(reps)) == 1 and len(cargas) == 1:
        c = carga(*next(iter(cargas)))
        texto = f"{len(filas)} x {reps[0]}" + (f" @ {c}" if c else "")
    else:
        texto = " · ".join(f"{f.reps}" + (f" @ {carga(f.peso, f.porcentaje)}" if carga(f.peso, f.porcentaje) else "") for f in filas)
    if ejercicio.rpe:
        texto += f" · RPE {ejercicio.rpe}"
    return texto


# ------------------------------------------------------------------ crear el plan

def crear_plan_importado(
    db: Session, coach: models.User, plan: PlanImportado, nombre: str, descripcion: str, disciplina: str, nivel: str
) -> models.Mesocycle:
    """Crea la plantilla en borrador con los días ya limpios. Sin commit (lo hace el llamador)."""
    mesociclo = models.Mesocycle(
        user_id=None,
        is_template=True,
        is_published=False,
        created_by_coach_id=coach.id,
        box_id=coach.box_id,
        plan_visibility="box",
        name=nombre,
        description=descripcion,
        discipline=disciplina,
        level=nivel,
        start_date=PLAN_EPOCH,
    )
    db.add(mesociclo)
    db.flush()

    for dia in plan.dias:
        sesion = _crear_sesion(db, mesociclo, dia.sesion, None, "Importado")
        sesion.day_offset = dia.desplazamiento
        sesion.scheduled_date = PLAN_EPOCH + timedelta(days=dia.desplazamiento)
    mesociclo.end_date = PLAN_EPOCH + timedelta(days=max(d.desplazamiento for d in plan.dias))
    return mesociclo
