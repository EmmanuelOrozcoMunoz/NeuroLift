"""Calculadora de 'Fit Level' para CrossFit: halterofilia, gimnasia y metcon.

IMPORTANTE — estos estándares son aproximados (tablas propias, no un estándar oficial único
de la industria). Diferencian por sexo (bounds_male / bounds_female) y aplican un ajuste por
edad inspirado en las tablas de "masters" de halterofilia/powerlifting (más laxo pasados los
35 años). Aun así, siguen siendo una referencia orientativa, no una medición competitiva.

Metodología:
- Halterofilia: se mide como razón levantamiento/peso_corporal (más alto = mejor).
- Gimnasia: repeticiones absolutas de movimientos de peso corporal (más alto = mejor).
- Metcon: tiempo en benchmarks clásicos (más bajo = mejor), salvo Cindy (AMRAP, más alto = mejor).

Cada métrica se puntúa en una escala 1-4 (Principiante/Intermedio/Avanzado/Elite). El nivel
de categoría es el promedio (redondeado) de sus métricas con dato; el nivel general es el
promedio de las categorías que tengan al menos una métrica registrada.
"""

LEVEL_LABELS = {1: "Principiante", 2: "Intermedio", 3: "Avanzado", 4: "Elite"}


def _score_higher_better(value: float, bounds: list[float]) -> int:
    """bounds = [max_principiante, max_intermedio, max_avanzado] (ascendente)."""
    if value < bounds[0]:
        return 1
    if value < bounds[1]:
        return 2
    if value < bounds[2]:
        return 3
    return 4


def _score_lower_better(value: float, bounds: list[float]) -> int:
    """bounds = [max_elite, max_avanzado, max_intermedio] (ascendente, en segundos)."""
    if value <= bounds[0]:
        return 4
    if value <= bounds[1]:
        return 3
    if value <= bounds[2]:
        return 2
    return 1


def _age_multiplier(age: int | None) -> float:
    """Cuánto se 'relajan' los estándares por edad (1.0 = sin ajuste, edades <=35).
    Inspirado en las tablas de masters de halterofilia/powerlifting: la fuerza y capacidad
    relativa esperada baja con la edad, así que un mismo desempeño vale un poco más."""
    if age is None or age <= 35:
        return 1.0
    if age <= 45:
        return 0.9
    if age <= 55:
        return 0.8
    if age <= 65:
        return 0.7
    return 0.6


def _bounds_for(meta: dict, sex: str | None) -> list[float]:
    """Si no se especifica sexo, se promedian ambas tablas como aproximación neutra
    (para no dejar sin resultado a quien todavía no llenó ese dato)."""
    if sex == "male":
        return meta["bounds_male"]
    if sex == "female":
        return meta["bounds_female"]
    return [(m + f) / 2 for m, f in zip(meta["bounds_male"], meta["bounds_female"])]


# Cada entrada: categoría, tipo, tablas de bounds por sexo, y etiqueta legible.
# tipo: "ratio_higher" (valor/peso_corporal, más alto mejor), "reps_higher" (valor absoluto,
#        más alto mejor), "time_lower" (segundos, más bajo mejor)
METRICS = {
    # --- Halterofilia (razón kg levantados / peso corporal) ---
    "snatch_kg": {
        "category": "halterofilia", "type": "ratio_higher", "label": "Snatch (1RM kg)",
        "bounds_male": [0.5, 0.75, 1.0], "bounds_female": [0.35, 0.55, 0.75],
    },
    "clean_jerk_kg": {
        "category": "halterofilia", "type": "ratio_higher", "label": "Clean & Jerk (1RM kg)",
        "bounds_male": [0.65, 0.95, 1.25], "bounds_female": [0.45, 0.7, 0.95],
    },
    "back_squat_kg": {
        "category": "halterofilia", "type": "ratio_higher", "label": "Back Squat (1RM kg)",
        "bounds_male": [1.0, 1.5, 2.0], "bounds_female": [0.75, 1.15, 1.5],
    },
    "deadlift_kg": {
        "category": "halterofilia", "type": "ratio_higher", "label": "Deadlift (1RM kg)",
        "bounds_male": [1.25, 1.75, 2.25], "bounds_female": [0.9, 1.3, 1.7],
    },

    # --- Gimnasia (repeticiones absolutas) ---
    "pull_ups_max": {
        "category": "gimnasia", "type": "reps_higher", "label": "Dominadas estrictas (máx)",
        "bounds_male": [5, 10, 20], "bounds_female": [2, 5, 12],
    },
    "push_ups_max": {
        "category": "gimnasia", "type": "reps_higher", "label": "Push-ups (máx)",
        "bounds_male": [15, 30, 50], "bounds_female": [8, 18, 35],
    },
    "muscle_ups_max": {
        "category": "gimnasia", "type": "reps_higher", "label": "Muscle-ups (máx)",
        "bounds_male": [1, 3, 8], "bounds_female": [1, 2, 5],
    },
    "hspu_max": {
        "category": "gimnasia", "type": "reps_higher", "label": "Handstand push-ups (máx)",
        "bounds_male": [1, 5, 15], "bounds_female": [1, 3, 10],
    },

    # --- Metcon (tiempo en segundos, salvo Cindy que es AMRAP de reps) ---
    "fran_seconds": {
        "category": "metcon", "type": "time_lower", "label": "Fran (tiempo)",
        "bounds_male": [180, 300, 480], "bounds_female": [200, 340, 540],
    },
    "grace_seconds": {
        "category": "metcon", "type": "time_lower", "label": "Grace (tiempo)",
        "bounds_male": [150, 240, 360], "bounds_female": [170, 270, 400],
    },
    "cindy_total_reps": {
        "category": "metcon", "type": "reps_higher", "label": "Cindy (reps totales en 20min)",
        "bounds_male": [360, 540, 750], "bounds_female": [280, 420, 600],
    },
    "row_2k_seconds": {
        "category": "metcon", "type": "time_lower", "label": "2000m Remo (tiempo)",
        "bounds_male": [405, 449, 510], "bounds_female": [450, 500, 570],
    },
}

CATEGORIES = ["halterofilia", "gimnasia", "metcon"]
CATEGORY_ICONS = {"halterofilia": "🏋️", "gimnasia": "🤸", "metcon": "🔥"}


def score_metric(
    metric_key: str, value: float, body_weight: float | None, sex: str | None = None, age: int | None = None
) -> int | None:
    meta = METRICS[metric_key]
    bounds = _bounds_for(meta, sex)
    mult = _age_multiplier(age)

    if meta["type"] == "ratio_higher":
        if not body_weight:
            return None  # no se puede calcular la razón sin peso corporal
        bounds_ajustados = [b * mult for b in bounds]
        return _score_higher_better(value / body_weight, bounds_ajustados)
    if meta["type"] == "reps_higher":
        bounds_ajustados = [b * mult for b in bounds]
        return _score_higher_better(value, bounds_ajustados)
    if meta["type"] == "time_lower":
        # Más tiempo permitido a mayor ajuste por edad (mult < 1 => bounds más grandes => más laxo).
        bounds_ajustados = [b / mult for b in bounds]
        return _score_lower_better(value, bounds_ajustados)
    raise ValueError(f"Tipo de métrica desconocido: {meta['type']}")


def compute_fitness_level(
    values: dict[str, float], body_weight: float | None, sex: str | None = None, age: int | None = None
) -> dict:
    """values: {metric_key: value} solo con las métricas que el atleta ya registró."""
    metric_scores: dict[str, int] = {}
    for metric_key, value in values.items():
        if metric_key not in METRICS:
            continue
        score = score_metric(metric_key, value, body_weight, sex, age)
        if score is not None:
            metric_scores[metric_key] = score

    category_scores: dict[str, float] = {}
    category_levels: dict[str, str] = {}
    for categoria in CATEGORIES:
        scores_categoria = [
            s for k, s in metric_scores.items() if METRICS[k]["category"] == categoria
        ]
        if scores_categoria:
            promedio = sum(scores_categoria) / len(scores_categoria)
            category_scores[categoria] = round(promedio, 2)
            category_levels[categoria] = LEVEL_LABELS[round(promedio)]

    if category_scores:
        overall_score = round(sum(category_scores.values()) / len(category_scores), 2)
        overall_level = LEVEL_LABELS[round(overall_score)]
    else:
        overall_score = None
        overall_level = None

    return {
        "metric_scores": metric_scores,
        "category_scores": category_scores,
        "category_levels": category_levels,
        "overall_score": overall_score,
        "overall_level": overall_level,
    }
