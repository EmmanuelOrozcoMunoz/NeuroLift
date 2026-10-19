"""Lo que devuelve la IA al generar entrenamientos, convertido en datos limpios y válidos.

La IA responde JSON, pero nada garantiza que cada campo venga bien: un número como texto, un bloque
inventado, un porcentaje absurdo, una fecha que no se pidió. Este módulo (sin base de datos ni red,
para poder probarlo a fondo) hace tres cosas:

1. Limpia cada ejercicio, sesión y WOD: tipos, rangos y textos (`limpiar_ejercicio`,
   `limpiar_sesion`, `wod_limpio`).
2. Empareja las sesiones que devolvió la IA con las fechas que se pidieron
   (`emparejar_fechas`): la IA a veces inventa, repite o se salta una fecha.
3. Resuelve las cargas con las marcas del atleta, y NUNCA deja pasar un kg inventado para un
   levantamiento de barra sin marca (el caso más riesgoso: una carga adivinada va directo al atleta).

Quien guarda en la base (services/ai_mesocycles.py) solo recibe lo que sale de aquí.
"""
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any

from backend.sanitize import clean_multiline, clean_text
from backend.services.exercises import clean_ai_block
from backend.services.prs import normalize_exercise_name, resolve_weight_from_percentage

# ------------------------------------------------------------------ límites

# Tope de series de UN ejercicio (incluye rampas). Una respuesta con 500 series no es una rampa,
# es una alucinación: se recorta en vez de crear 500 filas.
MAX_SERIES = 12
MAX_REPS = 100
MAX_EJERCICIOS_POR_SESION = 30
# Un % de 1RM por encima de esto no es una prescripción de trabajo (ni siquiera un intento de
# marca llega al 120 %): se descarta y se avisa.
MAX_PORCENTAJE = 120
MAX_KG = 1000
MAX_NOTA_EJERCICIO = 300
MAX_CALENTAMIENTO = 1000
MAX_NOTAS_ATLETA = 2000

BLOQUES = ("warmup", "strength", "weightlifting", "skills", "metcon", "accessory", "main")

# Formatos de WOD que la app sabe puntuar y cronometrar (coinciden con schemas/common.py:FormatoWod
# y web/src/lib/wod.ts) y cuáles llevan tiempo límite / duración (el temporizador del atleta lo usa).
FORMATOS_DE_WOD = ("for_time", "amrap", "amrap_reps", "emom", "tabata", "1rm", "calories", "distance", "watts")
FORMATOS_CON_TIEMPO = ("for_time", "amrap", "amrap_reps", "emom", "calories", "distance", "watts")
_MAX_NOTAS_WOD = 2000
_MAX_MINUTOS_WOD = 180

# ------------------------------------------------------------------ nombres de ejercicios

# Levantamientos de barra donde "% de 1RM" es el lenguaje normal y, por eso mismo, donde un kg
# adivinado es peligroso. Llaves ya normalizadas (ver prs.normalize_exercise_name).
LEVANTAMIENTOS_CON_MARCA = frozenset({
    "back squat", "front squat", "overhead squat", "deadlift", "bench press", "strict press",
    "push press", "push jerk", "snatch", "power snatch", "hang snatch", "clean", "power clean",
    "hang clean", "clean and jerk", "split jerk", "jerk",
})

# Cómo se muestra cada levantamiento cuando la IA lo escribe en español, abreviado o en minúsculas:
# así "sentadilla trasera", "back squat" y "Back Squat" son UN solo ejercicio del catálogo y no tres.
# Solo se usa con lo que devuelve la IA; los nombres que escribe un coach se respetan tal cual.
NOMBRES_CANONICOS = {
    "back squat": "Back Squat", "front squat": "Front Squat", "overhead squat": "Overhead Squat",
    "deadlift": "Deadlift", "bench press": "Bench Press", "strict press": "Strict Press",
    "push press": "Push Press", "push jerk": "Push Jerk", "snatch": "Snatch",
    "power snatch": "Power Snatch", "hang snatch": "Hang Snatch", "clean": "Clean",
    "power clean": "Power Clean", "hang clean": "Hang Clean", "clean and jerk": "Clean & Jerk",
    "split jerk": "Split Jerk", "jerk": "Jerk",
}


def nombre_canonico(nombre: Any) -> str | None:
    """El nombre con el que se guarda un ejercicio que devolvió la IA (None si no trae nombre)."""
    if not isinstance(nombre, str):
        return None
    llave = normalize_exercise_name(nombre)
    return NOMBRES_CANONICOS.get(llave) or clean_text(nombre, 100) or None


def es_levantamiento_con_marca(nombre: str | None) -> bool:
    return normalize_exercise_name(nombre) in LEVANTAMIENTOS_CON_MARCA


# ------------------------------------------------------------------ conversiones tolerantes

def a_float(valor) -> float | None:
    if valor is None or isinstance(valor, bool):
        return None
    try:
        return float(valor)
    except (ValueError, TypeError):
        return None


def a_entero(valor, minimo: int, maximo: int, acotar: bool = False) -> int | None:
    """Un entero dentro de [minimo, maximo]; None si no es número o queda fuera (en vez de inventar
    un valor: quien llama decide el default). Con `acotar`, uno que se pasa del máximo se recorta a
    él (una IA que pide "500 series" quiere decir "muchas", no "ninguna")."""
    numero = a_float(valor)
    if numero is None or numero != numero or numero in (float("inf"), float("-inf")):  # NaN o infinito
        return None
    entero = int(numero)
    if acotar and entero > maximo:
        return maximo
    return entero if minimo <= entero <= maximo else None


def _texto_largo(valor, maximo: int) -> str | None:
    return clean_multiline(valor, maximo) or None if isinstance(valor, str) else None


# ------------------------------------------------------------------ WOD

def wod_limpio(wod) -> dict | None:
    """Valida el WOD que devolvió la IA y lo deja como lo guarda la plantilla de WOD de la app:
    {"format", "time_cap_seconds", "notes"}. Devuelve None si no hay nada usable (la IA a veces
    devuelve null, un texto o valores inventados: mejor sin WOD que uno mal configurado)."""
    if not isinstance(wod, dict):
        return None
    formato = wod.get("format")
    formato = formato.strip().lower() if isinstance(formato, str) else None
    if formato not in FORMATOS_DE_WOD:
        formato = None

    segundos = None
    if formato in FORMATOS_CON_TIEMPO:
        minutos = a_float(wod.get("time_cap_minutes"))
        if minutos is not None and 0 < minutos <= _MAX_MINUTOS_WOD:
            segundos = int(round(minutos * 60))

    # El nombre va en una línea; la descripción conserva sus saltos de línea (un WOD de varias
    # líneas se queda así). Ambos pasan por el mismo saneo que el texto que escribe un coach.
    partes = [
        limpio
        for clave in ("name", "description")
        if isinstance(wod.get(clave), str)
        and (limpio := clean_multiline(wod.get(clave)) if clave == "description" else clean_text(wod.get(clave)))
    ]
    notas = "\n".join(partes)[:_MAX_NOTAS_WOD] or None

    if formato is None and notas is None:
        return None
    return {"format": formato, "time_cap_seconds": segundos, "notes": notas}


# ------------------------------------------------------------------ ejercicios

@dataclass
class FilaLimpia:
    """Una serie ya resuelta: sus repeticiones y su carga (kg y/o % de 1RM)."""
    reps: int
    peso: float | None
    porcentaje: float | None


@dataclass
class EjercicioLimpio:
    """Un ejercicio de la respuesta de la IA, ya con tipos y valores validados.

    `series`, `reps`, `peso` y `porcentaje` describen las series IGUALES (el caso común); `filas`
    solo viene cuando la IA pidió una rampa (series distintas), y entonces manda sobre lo demás."""
    nombre: str
    series: int
    reps: int
    rpe: int | None
    peso: float | None
    porcentaje: float | None
    referencia: str | None
    bloque: str | None
    nota: str | None = None
    filas: list[FilaLimpia] | None = None
    advertencias: list[str] = field(default_factory=list)

    def filas_a_guardar(self) -> list[FilaLimpia]:
        """Las series que se crean en la base, una por fila."""
        return self.filas or [FilaLimpia(self.reps, self.peso, self.porcentaje)] * self.series


def _primero(ej_data: dict, *claves) -> Any:
    """El primer valor "verdadero" entre varias claves (la IA no siempre usa el nombre pedido)."""
    for clave in claves:
        if ej_data.get(clave):
            return ej_data[clave]
    return None


def limpiar_ejercicio(ej_data: dict, prs: dict | None, conservar_kg: bool = False) -> EjercicioLimpio:
    """Valida los tipos que devuelve la IA y resuelve la carga con las marcas ACTUALES del atleta.

    `prs` es el diccionario de marcas del atleta (ver prs.get_athlete_prs). `None` significa que NO
    hay atleta (una plantilla de plan o la programación de una clase): los % se conservan como
    están y ningún kg fijo de un levantamiento de barra se acepta, porque no hay marca con qué
    respaldarlo.

    `conservar_kg` es para un documento que escribió el propio coach (importar un plan): ahí un kg fijo
    NO lo inventó la IA, es lo que el coach prescribió, y se respeta tal cual aunque no haya marca."""
    advertencias: list[str] = []
    es_plantilla = prs is None
    prs = prs or {}

    nombre = nombre_canonico(ej_data.get("exercise_name")) or "Ejercicio Desconocido"
    rpe = a_entero(_primero(ej_data, "rpe_target", "rpe"), 1, 10)
    referencia = nombre_canonico(ej_data.get("reference_exercise")) or nombre
    levantamiento = es_levantamiento_con_marca(nombre) or es_levantamiento_con_marca(referencia)
    marca_propia = prs.get(normalize_exercise_name(nombre))
    marca_referencia = prs.get(normalize_exercise_name(referencia))

    def peso_valido(valor) -> float | None:
        peso = a_float(valor)
        return peso if peso is not None and 0 < peso <= MAX_KG else None

    def porcentaje_valido(valor) -> float | None:
        porcentaje = a_float(valor)
        if porcentaje is None or porcentaje <= 0:
            return None
        if porcentaje > MAX_PORCENTAJE:
            advertencias.append(f"{nombre}: se descartó un {porcentaje:g} % de 1RM (fuera de rango)")
            return None
        return porcentaje

    derivo_porcentaje = False
    carga_pendiente = False
    kg_descartado = False

    def resolver_fila(reps: int, peso_ia, porcentaje_ia) -> FilaLimpia:
        """La carga de UNA serie: % -> kg con la marca de hoy; kg fijo -> se respeta o se descarta."""
        nonlocal derivo_porcentaje, carga_pendiente, kg_descartado
        peso, porcentaje = peso_valido(peso_ia), porcentaje_valido(porcentaje_ia)
        if porcentaje is not None:
            if not es_plantilla and not marca_referencia:
                carga_pendiente = True
            # La IA sí dio un %: recalcula el kg a partir de la marca ACTUAL del atleta en vez de
            # confiar en un número que ella misma haya calculado (así se mantiene "vivo").
            return FilaLimpia(reps, resolve_weight_from_percentage(porcentaje, peso, referencia, prs), porcentaje)
        if peso is None:
            return FilaLimpia(reps, None, None)
        if conservar_kg:
            return FilaLimpia(reps, peso, None)
        if marca_propia:
            # La IA ignoró la instrucción y dio un kg fijo (pasa seguido): si coincide con una marca
            # de ESTE atleta para el mismo ejercicio, se deriva el % para que quede igual de "vivo".
            derivo_porcentaje = True
            return FilaLimpia(reps, peso, float(round(peso / marca_propia * 100)))
        if levantamiento:
            # Un levantamiento de barra SIN marca: ese kg es inventado, no se guarda.
            kg_descartado = True
            return FilaLimpia(reps, None, None)
        return FilaLimpia(reps, peso, None)

    filas: list[FilaLimpia] | None = None
    series_ia = ej_data.get("series")
    if isinstance(series_ia, list):
        candidatas = [fila for fila in series_ia[:MAX_SERIES] if isinstance(fila, dict)]
        if len(candidatas) > 1:
            filas = [
                resolver_fila(
                    a_entero(fila.get("prescribed_reps"), 1, MAX_REPS, acotar=True) or 1,
                    fila.get("prescribed_weight"), fila.get("prescribed_percentage"),
                )
                for fila in candidatas
            ]
        elif len(candidatas) == 1:
            # Una "rampa" de una sola serie es un ejercicio normal de una serie
            unica = candidatas[0]
            ej_data = {**ej_data, "prescribed_sets": 1, "prescribed_reps": unica.get("prescribed_reps"),
                       "prescribed_weight": unica.get("prescribed_weight"),
                       "prescribed_percentage": unica.get("prescribed_percentage")}

    if filas:
        primera = filas[0]
        series, reps, peso, porcentaje = len(filas), primera.reps, primera.peso, primera.porcentaje
    else:
        reps = a_entero(ej_data.get("prescribed_reps"), 1, MAX_REPS, acotar=True) or 1
        series = a_entero(ej_data.get("prescribed_sets"), 1, MAX_SERIES, acotar=True) or 1
        fila = resolver_fila(reps, _primero(ej_data, "prescribed_weight", "weight_kg", "weight", "target_weight"),
                             ej_data.get("prescribed_percentage"))
        peso, porcentaje = fila.peso, fila.porcentaje

    if kg_descartado:
        advertencias.append(f"{nombre}: la IA puso un kg sin que haya marca de 1RM; la carga quedó libre (por RPE)")
    if carga_pendiente:
        advertencias.append(f"{nombre}: sin marca de {referencia} el % de 1RM queda sin kg hasta registrarla")

    tiene_porcentaje = porcentaje is not None or any(f.porcentaje is not None for f in (filas or []))
    return EjercicioLimpio(
        nombre=nombre,
        series=series,
        reps=reps,
        rpe=rpe,
        peso=peso,
        porcentaje=porcentaje,
        referencia=(nombre if derivo_porcentaje else referencia) if tiene_porcentaje else None,
        bloque=clean_ai_block(ej_data.get("block")),
        nota=_texto_largo(ej_data.get("coach_note"), MAX_NOTA_EJERCICIO),
        filas=filas,
        advertencias=advertencias,
    )


# ------------------------------------------------------------------ sesiones

@dataclass
class SesionLimpia:
    fecha: date
    notas_atleta: str
    calentamiento: str | None
    orden_de_bloques: str | None
    wod: dict | None
    ejercicios: list[EjercicioLimpio]
    advertencias: list[str] = field(default_factory=list)


def orden_de_bloques_limpio(valor, presentes: set[str]) -> str | None:
    """El orden de bloques que propuso la IA como texto "warmup,strength,metcon": solo bloques
    válidos que de verdad están en la sesión, sin repetir. Con menos de dos no hay nada que ordenar."""
    if isinstance(valor, str):
        valor = valor.split(",")
    if not isinstance(valor, list):
        return None
    orden: list[str] = []
    for item in valor:
        clave = item.strip().lower() if isinstance(item, str) else None
        if clave in BLOQUES and clave in presentes and clave not in orden:
            orden.append(clave)
    return ",".join(orden) if len(orden) > 1 else None


def limpiar_sesion(sesion_data: dict, fecha: date, prs: dict | None, conservar_kg: bool = False) -> SesionLimpia:
    """Una sesión de la IA lista para guardar. Un ejercicio roto se descarta (con aviso) sin tumbar
    la sesión, y una sesión rota no tumba el mesociclo."""
    advertencias: list[str] = []
    ejercicios: list[EjercicioLimpio] = []
    crudos = sesion_data.get("exercises")
    for ej_data in (crudos if isinstance(crudos, list) else [])[:MAX_EJERCICIOS_POR_SESION]:
        if not isinstance(ej_data, dict):
            advertencias.append("se descartó un ejercicio que no tenía el formato esperado")
            continue
        try:
            ejercicio = limpiar_ejercicio(ej_data, prs, conservar_kg)
        except Exception as e:  # noqa: BLE001 — cualquier dato raro de la IA: descartar el ejercicio, no la sesión
            advertencias.append(f"se descartó un ejercicio ilegible ({type(e).__name__})")
            continue
        advertencias.extend(ejercicio.advertencias)
        ejercicios.append(ejercicio)

    wod = wod_limpio(sesion_data.get("wod"))
    calentamiento = _texto_largo(sesion_data.get("warmup_notes"), MAX_CALENTAMIENTO)
    presentes = {e.bloque for e in ejercicios if e.bloque}
    if wod:
        presentes.add("metcon")
    if calentamiento:
        presentes.add("warmup")

    return SesionLimpia(
        fecha=fecha,
        notas_atleta=_texto_largo(sesion_data.get("athlete_notes"), MAX_NOTAS_ATLETA) or "",
        calentamiento=calentamiento,
        orden_de_bloques=orden_de_bloques_limpio(sesion_data.get("block_order"), presentes),
        wod=wod,
        ejercicios=ejercicios,
        advertencias=advertencias,
    )


# ------------------------------------------------------------------ fechas

def sesiones_de_respuesta(respuesta: Any) -> list[dict]:
    """Las sesiones de una respuesta de la IA, en el orden en que las devolvió (aplana las semanas).
    Tolera una respuesta sin semanas o con elementos que no son objetos."""
    if not isinstance(respuesta, dict):
        return []
    semanas = respuesta.get("weeks")
    if not isinstance(semanas, list):
        semanas = [respuesta] if isinstance(respuesta.get("sessions"), list) else []
    sesiones: list[dict] = []
    for semana in semanas:
        crudas = semana.get("sessions") if isinstance(semana, dict) else None
        sesiones.extend(s for s in (crudas if isinstance(crudas, list) else []) if isinstance(s, dict))
    return sesiones


def fecha_de_texto(valor) -> str | None:
    """La fecha YYYY-MM-DD de lo que devolvió la IA, o None si no es una fecha válida."""
    if not isinstance(valor, str):
        return None
    try:
        return datetime.strptime(valor.strip(), "%Y-%m-%d").date().isoformat()
    except ValueError:
        return None


def emparejar_fechas(sesiones: list[dict], fechas_esperadas: list[str]) -> tuple[list[tuple[str, dict]], list[str]]:
    """Asigna cada sesión de la IA a una de las fechas que SE PIDIERON. Devuelve (pares ordenados
    por fecha, fechas sin sesión).

    Primero se respeta la fecha que trae la sesión si es una de las pedidas. Las que traen una fecha
    inventada, repetida o ilegible se asignan, en orden, a las fechas que quedaron libres: la IA no
    decide cuándo se entrena, lo decide el calendario del coach. Las que sobran se descartan."""
    libres = list(fechas_esperadas)
    asignadas: dict[str, dict] = {}
    sobrantes: list[dict] = []
    for sesion in sesiones:
        fecha = fecha_de_texto(sesion.get("scheduled_date"))
        if fecha in libres:
            asignadas[fecha] = sesion
            libres.remove(fecha)
        else:
            sobrantes.append(sesion)
    for sesion in sobrantes:
        if not libres:
            break
        asignadas[libres.pop(0)] = sesion
    return [(f, asignadas[f]) for f in fechas_esperadas if f in asignadas], libres
