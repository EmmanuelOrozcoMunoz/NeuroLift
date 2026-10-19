"""Evaluación de lo que devuelve la IA: reglas verificables sobre la respuesta CRUDA de Gemini.

Para qué sirve. Mejorar un prompt "a ojo" no es medir: sin números no se sabe si un cambio ayudó o
empeoró. Estas reglas revisan una respuesta ANTES de la limpieza (lo que ai_salida.py repara o
descarta) para medir cuánto se equivoca la IA misma: fechas inventadas, un kg sin marca, un bloque
que no existe, una progresión que baja, el enfoque del día que no aparece. Se usan de dos formas:

- En las pruebas, con respuestas guardadas (buenas y malas), para que las reglas mismas sean fiables.
- Con la IA real, a mano: `python -m backend.evals.run_ia` (gasta tokens, necesita GEMINI_API_KEY).

Los hallazgos son de dos niveles: "error" (algo que la limpieza tiene que reparar o descartar, o
que pone en riesgo al atleta) y "aviso" (algo discutible: calidad, no corrección).
"""
import unicodedata
from collections import defaultdict
from dataclasses import dataclass
from datetime import date

from backend.services.ai_salida import (
    BLOQUES,
    FORMATOS_CON_TIEMPO,
    FORMATOS_DE_WOD,
    MAX_EJERCICIOS_POR_SESION,
    MAX_PORCENTAJE,
    MAX_REPS,
    MAX_SERIES,
    a_float,
    es_levantamiento_con_marca,
    fecha_de_texto,
    sesiones_de_respuesta,
    wod_limpio,
)
from backend.services.prs import normalize_exercise_name

# Con más ejercicios que esto una sesión no cabe en una hora de clase: es un aviso de calidad
EJERCICIOS_RAZONABLES_POR_SESION = 15

# Bloques que solo tienen sentido en CrossFit (ver _INSTRUCCION_BLOQUES en ai_agent.py)
_BLOQUES_DE_CROSSFIT = {"metcon", "weightlifting", "skills"}

# Palabras del coach (en español) -> cómo aparecen en los nombres de ejercicios (en inglés): sin
# esto, "Sentadilla pesada" nunca "coincidiría" con un "Back Squat". Es una heurística, no una verdad.
_EQUIVALENCIAS = {
    "sentadilla": "squat", "pierna": "squat", "piernas": "squat", "muerto": "deadlift", "arranque": "snatch",
    "envion": "jerk", "cargada": "clean", "banca": "bench", "pecho": "bench", "empuje": "press", "hombro": "press",
    "hombros": "press", "dominadas": "pull", "gimnasia": "pull", "traccion": "pull", "remo": "row",
    "core": "core", "abdomen": "core", "movilidad": "mobility", "calentamiento": "warm",
}
_PALABRAS_VACIAS = {
    "para", "con", "sin", "una", "uno", "unos", "unas", "los", "las", "del", "dia", "dias", "entrenamiento",
    "trabajo", "hoy", "sesion", "enfoque", "mucho", "poco", "fuerte", "ligero", "pesada", "pesado", "tecnica",
    "ejercicios", "accesorios", "principal",
}


@dataclass(frozen=True)
class Hallazgo:
    nivel: str  # "error" | "aviso"
    regla: str
    detalle: str


def _plano(texto: str) -> str:
    sin_tildes = "".join(c for c in unicodedata.normalize("NFKD", texto) if not unicodedata.combining(c))
    return sin_tildes.lower()


def _ejercicios(sesion: dict) -> list[dict]:
    crudos = sesion.get("exercises")
    return [e for e in crudos if isinstance(e, dict)] if isinstance(crudos, list) else []


def _numero_de_series(ej: dict) -> int:
    series = ej.get("series")
    if isinstance(series, list) and series:
        return len(series)
    return int(a_float(ej.get("prescribed_sets")) or 1)


def _porcentajes(ej: dict) -> list[float]:
    """Los % de 1RM de un ejercicio (de cada serie si es una rampa)."""
    series = ej.get("series")
    filas = [f for f in series if isinstance(f, dict)] if isinstance(series, list) and series else [ej]
    return [p for p in (a_float(f.get("prescribed_percentage")) for f in filas) if p is not None and p > 0]


def _texto_de_sesion(sesion: dict) -> str:
    partes = [str(sesion.get("athlete_notes") or ""), str(sesion.get("warmup_notes") or "")]
    wod = sesion.get("wod")
    if isinstance(wod, dict):
        partes += [str(wod.get("name") or ""), str(wod.get("description") or "")]
    for ej in _ejercicios(sesion):
        partes += [str(ej.get("exercise_name") or ""), str(ej.get("coach_note") or "")]
    return _plano(" ".join(partes))


def _palabras_clave(enfoque: str) -> set[str]:
    palabras = {p for p in _plano(enfoque).replace(",", " ").replace(".", " ").split() if len(p) >= 4}
    return {_EQUIVALENCIAS.get(p, p) for p in palabras if p not in _PALABRAS_VACIAS}


def evaluar_respuesta(
    respuesta: dict,
    *,
    fechas: list[str],
    prs: dict[str, float] | None = None,
    disciplina: str = "CrossFit",
    day_focus: dict[int, str] | None = None,
) -> list[Hallazgo]:
    """Revisa una respuesta cruda de la IA contra lo que se le pidió.

    `fechas`: las fechas (YYYY-MM-DD) que se pidieron. `prs`: las marcas del atleta con la llave
    normalizada (None = no hay atleta, una plantilla). `day_focus`: la guía por día de la semana."""
    hallazgos: list[Hallazgo] = []
    sesiones = sesiones_de_respuesta(respuesta)
    es_crossfit = _plano(disciplina) == "crossfit"
    prs_conocidas = prs if prs is not None else {}

    def error(regla: str, detalle: str) -> None:
        hallazgos.append(Hallazgo("error", regla, detalle))

    def aviso(regla: str, detalle: str) -> None:
        hallazgos.append(Hallazgo("aviso", regla, detalle))

    # ---------------------------------------------------------------- cobertura de fechas
    vistas: dict[str | None, int] = defaultdict(int)
    for sesion in sesiones:
        vistas[fecha_de_texto(sesion.get("scheduled_date"))] += 1
    for fecha in fechas:
        if fecha not in vistas:
            error("sin_sesion", f"no hay sesión para {fecha}")
    for fecha, veces in vistas.items():
        if fecha is None:
            aviso("fecha_ilegible", f"{veces} sesión(es) sin una fecha válida")
        elif fecha not in fechas:
            aviso("fecha_inventada", f"{fecha} no se pidió")
        elif veces > 1:
            aviso("fecha_repetida", f"{fecha} aparece {veces} veces")

    # ---------------------------------------------------------------- por sesión
    por_fecha: dict[str, dict] = {}
    for sesion in sesiones:
        fecha = fecha_de_texto(sesion.get("scheduled_date")) or "?"
        por_fecha.setdefault(fecha, sesion)
        ejercicios = _ejercicios(sesion)

        if len(ejercicios) > MAX_EJERCICIOS_POR_SESION:
            error("demasiados_ejercicios", f"{fecha}: {len(ejercicios)} ejercicios")
        elif len(ejercicios) > EJERCICIOS_RAZONABLES_POR_SESION:
            aviso("sesion_muy_larga", f"{fecha}: {len(ejercicios)} ejercicios")

        wod = sesion.get("wod")
        if wod is not None:
            limpio = wod_limpio(wod)
            formato = wod.get("format") if isinstance(wod, dict) else None
            if limpio is None or formato not in FORMATOS_DE_WOD:
                aviso("wod_invalido", f"{fecha}: formato {formato!r}")
            elif formato in FORMATOS_CON_TIEMPO and limpio["time_cap_seconds"] is None:
                aviso("wod_sin_tiempo", f"{fecha}: un {formato} sin duración o time cap válido")

        for ej in ejercicios:
            nombre = str(ej.get("exercise_name") or "?")
            bloque = ej.get("block")
            if bloque not in BLOQUES:
                aviso("bloque_invalido", f"{fecha} {nombre}: bloque {bloque!r}")
            elif es_crossfit and bloque == "main":
                aviso("bloque_generico", f"{fecha} {nombre}: 'main' en CrossFit")
            elif not es_crossfit and bloque in _BLOQUES_DE_CROSSFIT:
                aviso("bloque_ajeno_a_la_disciplina", f"{fecha} {nombre}: '{bloque}' fuera de CrossFit")

            series, reps = _numero_de_series(ej), a_float(ej.get("prescribed_reps")) or 0
            if series > MAX_SERIES:
                error("series_absurdas", f"{fecha} {nombre}: {series} series")
            if reps > MAX_REPS:
                error("repeticiones_absurdas", f"{fecha} {nombre}: {reps:g} repeticiones")
            rpe = a_float(ej.get("rpe_target"))
            if rpe is not None and not 1 <= rpe <= 10:
                aviso("rpe_fuera_de_rango", f"{fecha} {nombre}: RPE {rpe:g}")

            # ------------------------------------------------------------ cargas
            referencia = ej.get("reference_exercise") if isinstance(ej.get("reference_exercise"), str) else None
            llave_marca = normalize_exercise_name(referencia or nombre)
            hay_marca = bool(prs_conocidas.get(llave_marca)) or bool(prs_conocidas.get(normalize_exercise_name(nombre)))
            kg = a_float(ej.get("prescribed_weight"))
            porcentajes = _porcentajes(ej)
            es_levantamiento = es_levantamiento_con_marca(nombre) or es_levantamiento_con_marca(referencia)
            if kg and not porcentajes:
                if prs is not None and hay_marca:
                    aviso("kg_con_marca", f"{fecha} {nombre}: kg fijo habiendo marca (debía ir en %)")
                elif es_levantamiento:
                    error("kg_inventado", f"{fecha} {nombre}: {kg:g} kg sin marca de 1RM")
            for porcentaje in porcentajes:
                if porcentaje > MAX_PORCENTAJE:
                    error("porcentaje_absurdo", f"{fecha} {nombre}: {porcentaje:g} %")
                elif porcentaje > 100:
                    aviso("porcentaje_alto", f"{fecha} {nombre}: {porcentaje:g} %")
            if porcentajes and prs is not None and not hay_marca:
                aviso("porcentaje_sin_marca", f"{fecha} {nombre}: % de {referencia or nombre} sin marca registrada")

    # ---------------------------------------------------------------- progresión entre semanas
    if len(fechas) > 1:
        primera = date.fromisoformat(fechas[0])
        por_semana: dict[int, list[float]] = defaultdict(list)
        for fecha, sesion in por_fecha.items():
            if fecha in fechas:
                semana = (date.fromisoformat(fecha) - primera).days // 7
                for ej in _ejercicios(sesion):
                    por_semana[semana].extend(_porcentajes(ej))
        medias = [sum(v) / len(v) for _, v in sorted(por_semana.items()) if v]
        if len(medias) >= 3:
            if medias[-1] < medias[0] - 5:
                aviso("progresion_decreciente", f"la intensidad media baja de {medias[0]:.0f} % a {medias[-1]:.0f} %")
            elif max(medias) - min(medias) < 1:
                aviso("sin_progresion", f"la intensidad media no cambia ({medias[0]:.0f} %) en {len(medias)} semanas")

    # ---------------------------------------------------------------- enfoque pedido por día
    for fecha in fechas:
        enfoque = (day_focus or {}).get(date.fromisoformat(fecha).weekday())
        sesion = por_fecha.get(fecha)
        if not enfoque or sesion is None:
            continue
        clave = _palabras_clave(enfoque)
        texto = _texto_de_sesion(sesion)
        if clave and not any(palabra in texto for palabra in clave):
            aviso("enfoque_no_reflejado", f"{fecha}: se pidió «{enfoque}» y no aparece en la sesión")

    return hallazgos


def uso_de_componentes(respuesta: dict) -> dict[str, int]:
    """Cuántos de los componentes de una sesión armada a mano usó la IA. No son errores: sirven para
    ver si un cambio de prompt hace que la IA use (o deje de usar) el calentamiento en texto, el
    orden de bloques, las notas por ejercicio y las rampas."""
    sesiones = sesiones_de_respuesta(respuesta)
    ejercicios = [e for s in sesiones for e in _ejercicios(s)]
    return {
        "sesiones": len(sesiones),
        "con_calentamiento_en_texto": sum(1 for s in sesiones if str(s.get("warmup_notes") or "").strip()),
        "con_orden_de_bloques": sum(1 for s in sesiones if s.get("block_order")),
        "con_wod": sum(1 for s in sesiones if isinstance(s.get("wod"), dict)),
        "ejercicios": len(ejercicios),
        "ejercicios_con_nota": sum(1 for e in ejercicios if str(e.get("coach_note") or "").strip()),
        "ejercicios_con_rampa": sum(1 for e in ejercicios if isinstance(e.get("series"), list) and len(e["series"]) > 1),
    }


def resumen(hallazgos: list[Hallazgo]) -> dict[str, int]:
    return {
        "errores": sum(1 for h in hallazgos if h.nivel == "error"),
        "avisos": sum(1 for h in hallazgos if h.nivel == "aviso"),
    }
