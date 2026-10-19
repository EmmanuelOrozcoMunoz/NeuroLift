"""Evalúa la generación con IA contra casos fijos, con la IA REAL.

    python -m backend.evals.run_ia                       # todos los casos (gasta tokens)
    python -m backend.evals.run_ia --caso crossfit_sin_marcas
    python -m backend.evals.run_ia --archivo respuesta.json --fechas 2026-01-05,2026-01-07 \\
        --disciplina CrossFit --marcas "Back Squat=100,Deadlift=150"      # sin gastar nada

Necesita GEMINI_API_KEY en el entorno (o en el .env) y GASTA TOKENS de verdad: cada caso es una
generación completa. No toca la base de datos ni guarda nada. Para cada caso imprime los tokens
gastados, los hallazgos de backend/services/ai_evaluacion.py y cuántos componentes de la sesión usó
la IA (calentamiento en texto, orden de bloques, notas, rampas, WOD). Termina con código 1 si algún
caso tiene hallazgos de nivel "error", para poder usarlo como compuerta.

Se corre ANTES y DESPUÉS de cambiar un prompt o un esquema: la comparación es lo que dice si el
cambio ayudó. Los números de un solo caso varían de una corrida a otra (la IA no es determinista):
conviene repetir cada caso unas veces antes de sacar conclusiones.
"""
import argparse
import json
import sys
from dataclasses import dataclass, field
from datetime import date

from backend.services.ai_evaluacion import Hallazgo, evaluar_respuesta, resumen, uso_de_componentes
from backend.services.ai_mesocycles import especificar_chunks, fechas_de_entrenamiento
from backend.services.ai_salida import sesiones_de_respuesta
from backend.services.prs import normalize_exercise_name

INICIO = date(2026, 1, 5)  # un lunes, para que los días de la semana de los casos sean estables


@dataclass
class Caso:
    nombre: str
    disciplina: str
    semanas: int
    dias: list[int]
    marcas: dict[str, float]  # nombre -> kg
    peticion: str = ""
    enfoque_por_dia: dict[int, str] | None = None
    duracion_minutos: int | None = None
    notas: str = ""
    sesiones_por_semana: int = field(init=False)

    def __post_init__(self):
        self.sesiones_por_semana = len(self.dias)


CASOS = [
    Caso("crossfit_con_marcas", "CrossFit", 4, [0, 2, 4],
         {"Back Squat": 120, "Front Squat": 95, "Deadlift": 160, "Snatch": 70, "Clean & Jerk": 90},
         "Mejorar el arranque y el motor aeróbico.", duracion_minutos=60),
    Caso("crossfit_sin_marcas", "CrossFit", 3, [1, 3], {}, "Atleta nuevo, sin marcas registradas."),
    Caso("fuerza_con_enfoque_por_dia", "Powerlifting", 4, [0, 3],
         {"Back Squat": 140, "Bench Press": 100, "Deadlift": 180},
         "Subir la sentadilla.", {0: "Sentadilla pesada", 3: "Press de banca y peso muerto"}),
    Caso("hipertrofia", "Hipertrofia", 4, [0, 1, 3, 4], {"Back Squat": 100, "Bench Press": 80},
         "Hipertrofia de tren superior.", duracion_minutos=75),
    Caso("mesociclo_largo_tres_tandas", "CrossFit", 8, [0, 2, 4],
         {"Back Squat": 120, "Snatch": 70, "Clean & Jerk": 90}, "Preparar una competencia en 8 semanas."),
]


def _contexto(caso: Caso) -> str:
    marcas = ", ".join(f"{n}: {kg}kg" for n, kg in caso.marcas.items()) or "Sin marcas registradas."
    return f"Peso corporal: 80kg. Marcas (1RM): {marcas}. Peticiones: {caso.peticion}"


def _imprimir(hallazgos: list[Hallazgo], prefijo: str = "   ") -> None:
    for h in hallazgos:
        print(f"{prefijo}[{h.nivel.upper():5}] {h.regla}: {h.detalle}")


def evaluar_caso(caso: Caso) -> tuple[list[Hallazgo], dict[str, int], dict[str, int]]:
    """Genera el mesociclo del caso con la IA real, tanda por tanda, y lo evalúa."""
    from backend.ai_agent import generate_mesocycle_chunk  # se importa aquí: exige GEMINI_API_KEY

    fechas = fechas_de_entrenamiento(INICIO, caso.semanas, caso.dias)
    specs = especificar_chunks(fechas, caso.semanas, caso.sesiones_por_semana, caso.enfoque_por_dia)
    prs = {normalize_exercise_name(n): kg for n, kg in caso.marcas.items()}
    hallazgos: list[Hallazgo] = []
    componentes: dict[str, int] = {}
    uso = {"llamadas": 0, "tokens_prompt": 0, "tokens_salida": 0, "tokens_pensamiento": 0}
    todas: list[dict] = []

    for inicio, fin, fechas_chunk, guia in specs:
        respuesta = generate_mesocycle_chunk(
            athlete_name="Atleta de prueba", discipline=caso.disciplina, experience_notes=_contexto(caso),
            start_week=inicio, end_week=fin, session_dates=fechas_chunk,
            session_duration_minutes=caso.duracion_minutos, literatura_cientifica="", day_focus_text=guia,
        )
        if respuesta.get("error"):
            hallazgos.append(Hallazgo("error", "la_ia_fallo", f"semanas {inicio}-{fin}: {respuesta['error']}"))
            continue
        for clave, valor in (respuesta.get("_uso") or {}).items():
            if clave in uso:
                uso[clave] += valor
        uso["llamadas"] += 1
        hallazgos += evaluar_respuesta(
            respuesta, fechas=fechas_chunk, prs=prs, disciplina=caso.disciplina, day_focus=caso.enfoque_por_dia,
        )
        todas += sesiones_de_respuesta(respuesta)
        for clave, valor in uso_de_componentes(respuesta).items():
            componentes[clave] = componentes.get(clave, 0) + valor

    # La continuidad entre tandas se evalúa sobre el mesociclo completo, no tanda por tanda
    if len(specs) > 1 and todas:
        completo = {"weeks": [{"sessions": todas}]}
        hallazgos += [
            h for h in evaluar_respuesta(completo, fechas=fechas, prs=prs, disciplina=caso.disciplina)
            if h.regla in ("progresion_decreciente", "sin_progresion")
        ]
    return hallazgos, componentes, uso


def _marcas_de_texto(texto: str) -> dict[str, float]:
    marcas = {}
    for par in filter(None, (texto or "").split(",")):
        nombre, _, kg = par.partition("=")
        marcas[normalize_exercise_name(nombre)] = float(kg)
    return marcas


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--caso", help="nombre de un caso (por defecto, todos)")
    parser.add_argument("--archivo", help="evalúa un JSON ya guardado en vez de llamar a la IA")
    parser.add_argument("--fechas", help="con --archivo: las fechas pedidas, separadas por coma")
    parser.add_argument("--disciplina", default="CrossFit")
    parser.add_argument("--marcas", default="", help='con --archivo: "Back Squat=100,Deadlift=150"')
    args = parser.parse_args(argv)

    if args.archivo:
        with open(args.archivo, encoding="utf-8") as f:
            respuesta = json.load(f)
        fechas = [x.strip() for x in (args.fechas or "").split(",") if x.strip()]
        hallazgos = evaluar_respuesta(
            respuesta, fechas=fechas, prs=_marcas_de_texto(args.marcas) if args.marcas else None, disciplina=args.disciplina,
        )
        _imprimir(hallazgos, "")
        print(resumen(hallazgos), uso_de_componentes(respuesta))
        return 1 if resumen(hallazgos)["errores"] else 0

    casos = [c for c in CASOS if not args.caso or c.nombre == args.caso]
    if not casos:
        print(f"No existe el caso {args.caso!r}. Casos: {', '.join(c.nombre for c in CASOS)}")
        return 2

    hubo_errores = False
    for caso in casos:
        print(f"\n== {caso.nombre} ({caso.disciplina}, {caso.semanas} semanas, {caso.sesiones_por_semana}/semana)")
        hallazgos, componentes, uso = evaluar_caso(caso)
        _imprimir(hallazgos)
        print(f"   {resumen(hallazgos)}")
        print(f"   componentes usados: {componentes}")
        print(f"   tokens: {uso}")
        hubo_errores = hubo_errores or resumen(hallazgos)["errores"] > 0
    return 1 if hubo_errores else 0


if __name__ == "__main__":
    sys.exit(main())
