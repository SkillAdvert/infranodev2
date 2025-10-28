from __future__ import annotations

import math
from typing import Any, Dict, List, Sequence


def calculate_persona_topsis_score(
    component_scores: Sequence[Dict[str, float]],
    weights: Dict[str, float],
) -> Dict[str, Any]:
    """Apply TOPSIS using persona weights, supporting positive and negative impacts."""

    if not component_scores:
        return {
            "scores": [],
            "ideal_solution": {},
            "anti_ideal_solution": {},
        }

    component_keys = list(component_scores[0].keys())
    denominators: Dict[str, float] = {}
    for key in component_keys:
        sum_squares = sum((scores.get(key, 0.0) or 0.0) ** 2 for scores in component_scores)
        denominators[key] = math.sqrt(sum_squares) or 1e-9

    weighted_vectors: List[Dict[str, Dict[str, float]]] = []
    for scores in component_scores:
        normalized: Dict[str, float] = {}
        weighted: Dict[str, float] = {}
        for key in component_keys:
            raw_value = scores.get(key, 0.0) or 0.0
            denominator = denominators[key]
            normalized_value = raw_value / denominator if denominator else 0.0
            weight = weights.get(key, 0.0)
            weighted_value = normalized_value * weight
            normalized[key] = normalized_value
            weighted[key] = weighted_value
        weighted_vectors.append(
            {
                "normalized_scores": normalized,
                "weighted_normalized_scores": weighted,
            }
        )

    ideal_solution: Dict[str, float] = {}
    anti_ideal_solution: Dict[str, float] = {}
    for key in component_keys:
        values = [vector["weighted_normalized_scores"][key] for vector in weighted_vectors]
        ideal_solution[key] = max(values)
        anti_ideal_solution[key] = min(values)

    results: List[Dict[str, Any]] = []
    for vector in weighted_vectors:
        weighted = vector["weighted_normalized_scores"]
        distance_to_ideal = math.sqrt(
            sum((weighted[key] - ideal_solution[key]) ** 2 for key in component_keys)
        )
        distance_to_anti_ideal = math.sqrt(
            sum((weighted[key] - anti_ideal_solution[key]) ** 2 for key in component_keys)
        )
        closeness = 0.0
        denominator = distance_to_ideal + distance_to_anti_ideal
        if denominator > 0:
            closeness = distance_to_anti_ideal / denominator
        elif distance_to_ideal == 0 and distance_to_anti_ideal == 0:
            closeness = 1.0
        results.append(
            {
                "normalized_scores": vector["normalized_scores"],
                "weighted_normalized_scores": weighted,
                "distance_to_ideal": distance_to_ideal,
                "distance_to_anti_ideal": distance_to_anti_ideal,
                "closeness_coefficient": closeness,
            }
        )

    return {
        "scores": results,
        "ideal_solution": ideal_solution,
        "anti_ideal_solution": anti_ideal_solution,
    }

