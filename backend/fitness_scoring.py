"""Calculadora de 'Fit Level' para CrossFit: halterofilia, gimnasia y metcon.

IMPORTANTE — estos estándares son aproximados y genéricos (no diferenciados por sexo,
edad ni categoría de peso corporal). Sirven como referencia orientativa, no como una
medición oficial o competitiva. Si se necesita mayor precisión, lo natural sería pedir
el sexo del atleta y usar tablas separadas.

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


# Cada entrada: (categoría, tipo, bounds, [requiere_peso_corporal])
# tipo: "ratio_higher" (valor/peso_corporal, más alto mejor), "reps_higher" (valor absoluto,
#        más alto mejor), "time_lower" (segundos, más bajo mejor)
METRICS = {
    # --- Halterofilia (razón kg levantados / peso corporal) ---
    "snatch_kg":      {"category": "halterofilia", "type": "ratio_higher", "bounds": [0.5, 0.75, 1.0], "label": "Snatch (1RM kg)"},
    "clean_jerk_kg":  {"category": "halterofilia", "type": "ratio_higher", "bounds": [0.65, 0.95, 1.25], "label": "Clean & Jerk (1RM kg)"},
    "back_squat_kg":  {"category": "halterofilia", "type": "ratio_higher", "bounds": [1.0, 1.5, 2.0], "label": "Back Squat (1RM kg)"},
    "deadlift_kg":    {"category": "halterofilia", "type": "ratio_higher", "bounds": [1.25, 1.75, 2.25], "label": "Deadlift (1RM kg)"},

    # --- Gimnasia (repeticiones absolutas) ---
    "pull_ups_max":   {"category": "gimnasia", "type": "reps_higher", "bounds": [5, 10, 20], "label": "Dominadas estrictas (máx)"},
    "push_ups_max":   {"category": "gimnasia", "type": "reps_higher", "bounds": [15, 30, 50], "label": "Push-ups (máx)"},
    "muscle_ups_max": {"category": "gimnasia", "type": "reps_higher", "bounds": [1, 3, 8], "label": "Muscle-ups (máx)"},
    "hspu_max":       {"category": "gimnasia", "type": "reps_higher", "bounds": [1, 5, 15], "label": "Handstand push-ups (máx)"},

    # --- Metcon (tiempo en segundos, salvo Cindy que es AMRAP de reps) ---
    "fran_seconds":    {"category": "metcon", "type": "time_lower", "bounds": [180, 300, 480], "label": "Fran (tiempo)"},
    "grace_seconds":   {"category": "metcon", "type": "time_lower", "bounds": [150, 240, 360], "label": "Grace (tiempo)"},
    "cindy_total_reps": {"category": "metcon", "type": "reps_higher", "bounds": [360, 540, 750], "label": "Cindy (reps totales en 20min)"},
    "row_2k_seconds":  {"category": "metcon", "type": "time_lower", "bounds": [405, 449, 510], "label": "2000m Remo (tiempo)"},
}

CATEGORIES = ["halterofilia", "gimnasia", "metcon"]
CATEGORY_ICONS = {"halterofilia": "🏋️", "gimnasia": "🤸", "metcon": "🔥"}


def score_metric(metric_key: str, value: float, body_weight: float | None) -> int | None:
    meta = METRICS[metric_key]
    if meta["type"] == "ratio_higher":
        if not body_weight:
            return None  # no se puede calcular la razón sin peso corporal
        return _score_higher_better(value / body_weight, meta["bounds"])
    if meta["type"] == "reps_higher":
        return _score_higher_better(value, meta["bounds"])
    if meta["type"] == "time_lower":
        return _score_lower_better(value, meta["bounds"])
    raise ValueError(f"Tipo de métrica desconocido: {meta['type']}")


def compute_fitness_level(values: dict[str, float], body_weight: float | None) -> dict:
    """values: {metric_key: value} solo con las métricas que el atleta ya registró."""
    metric_scores: dict[str, int] = {}
    for metric_key, value in values.items():
        if metric_key not in METRICS:
            continue
        score = score_metric(metric_key, value, body_weight)
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
