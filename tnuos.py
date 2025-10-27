"""TNUoS (Transmission Network Use of System) tariff functions."""

from __future__ import annotations

import math
from typing import Any, Dict, List, Optional

from config import PERSONA_WEIGHTS, TNUOS_ZONES_HARDCODED, PersonaType


def find_tnuos_zone(latitude: float, longitude: float) -> Optional[Dict[str, Any]]:
    """Find TNUoS zone for given coordinates using hard-coded bounding boxes.

    Args:
        latitude: Latitude coordinate
        longitude: Longitude coordinate

    Returns:
        Dictionary with zone_id, zone_name, and generation_tariff_pounds_per_kw,
        or None if no zone found
    """
    for zone_id, zone_data in TNUOS_ZONES_HARDCODED.items():
        bounds = zone_data["bounds"]

        if (
            bounds["min_lat"] <= latitude <= bounds["max_lat"]
            and bounds["min_lng"] <= longitude <= bounds["max_lng"]
        ):
            return {
                "zone_id": zone_id,
                "zone_name": zone_data["name"],
                "generation_tariff_pounds_per_kw": zone_data["tariff"],
            }

    return None


def calculate_tnuos_score_from_tariff(tariff: float) -> float:
    """Convert TNUoS tariff (£/kW) to 0-100 investment score.

    Lower tariffs (more negative or less positive) are better for investment.

    Args:
        tariff: TNUoS tariff in £/kW

    Returns:
        Score from 0-100, where 100 is best (lowest tariff)
    """
    min_tariff = -3.0
    max_tariff = 16.0

    if tariff <= min_tariff:
        return 100.0
    if tariff >= max_tariff:
        return 0.0

    normalized = (tariff - min_tariff) / (max_tariff - min_tariff)
    return 100.0 * (1.0 - normalized)


async def enrich_and_rescore_top_25_with_tnuos(
    features: List[Dict[str, Any]],
    persona: Optional[PersonaType] = None,
) -> List[Dict[str, Any]]:
    """Enrich top 25 projects with TNUoS data and adjust scores.

    Args:
        features: List of GeoJSON features representing projects
        persona: User persona for weighting (hyperscaler, colocation, edge_computing)

    Returns:
        List of features with top 25 enriched and re-sorted
    """
    if not features:
        return features

    features_sorted = sorted(
        features,
        key=lambda feature: feature.get("properties", {}).get("investment_rating", 0),
        reverse=True,
    )

    top_25 = features_sorted[:25]
    remaining = features_sorted[25:]

    print("📊 Enriching top 25 projects with TNUoS zones...")

    enriched_count = 0

    for feature in top_25:
        properties = feature.setdefault("properties", {})

        try:
            coordinates = feature.get("geometry", {}).get("coordinates", [])
            if len(coordinates) < 2:
                properties["tnuos_enriched"] = False
                continue

            longitude, latitude = coordinates[0], coordinates[1]
            zone = find_tnuos_zone(latitude, longitude)

            if not zone:
                properties["tnuos_enriched"] = False
                continue

            properties["tnuos_zone_id"] = zone["zone_id"]
            properties["tnuos_zone_name"] = zone["zone_name"]
            tariff_value = zone["generation_tariff_pounds_per_kw"]
            properties["tnuos_tariff_pounds_per_kw"] = tariff_value

            tnuos_score = calculate_tnuos_score_from_tariff(tariff_value)
            properties["tnuos_score"] = round(tnuos_score, 1)

            old_rating = float(properties.get("investment_rating", 0.0))
            component_scores = dict(properties.get("component_scores") or {})
            component_scores["tnuos_transmission_costs"] = tnuos_score

            weights = dict(
                PERSONA_WEIGHTS.get(persona or "hyperscaler", PERSONA_WEIGHTS["hyperscaler"])
            )
            if "tnuos_transmission_costs" not in weights:
                fallback_weight = 0.1
                existing_total = sum(weights.values()) or 1.0
                weights = {
                    key: (value / existing_total) * (1.0 - fallback_weight)
                    for key, value in weights.items()
                }
                weights["tnuos_transmission_costs"] = fallback_weight

            total_weight = sum(weights.values()) or 1.0
            if not math.isclose(total_weight, 1.0, rel_tol=1e-6):
                weights = {key: value / total_weight for key, value in weights.items()}

            weighted_score = sum(
                (component_scores.get(key, 0.0) or 0.0) * weight
                for key, weight in weights.items()
            )

            weighted_score = max(0.0, min(100.0, weighted_score))
            new_rating = round(weighted_score / 10.0, 1)

            properties["component_scores"] = {
                key: round(value, 1) for key, value in component_scores.items()
            }

            weighted_contributions = dict(properties.get("weighted_contributions") or {})
            weighted_contributions = {
                key: round((component_scores.get(key, 0.0) or 0.0) * weights.get(key, 0.0), 1)
                for key in component_scores
            }

            properties["weighted_contributions"] = weighted_contributions
            properties["investment_rating"] = new_rating
            properties["internal_total_score"] = round(weighted_score, 1)
            properties["tnuos_enriched"] = True
            properties["rating_change"] = round(new_rating - old_rating, 1)

            if abs(new_rating - old_rating) > 0.2:
                site_name = properties.get("site_name", "Project")
                print(
                    f"  • {site_name}: {old_rating:.1f} → {new_rating:.1f} ({zone['zone_name']})"
                )

            enriched_count += 1
        except Exception as exc:  # pragma: no cover - defensive guard
            print(f"⚠️  Error processing project: {exc}")
            properties["tnuos_enriched"] = False

    print(f"✓ Enriched {enriched_count}/{len(top_25)} projects")

    for feature in remaining:
        feature.setdefault("properties", {})["tnuos_enriched"] = False

    resorted_top_25 = sorted(
        top_25,
        key=lambda feature: feature.get("properties", {}).get("investment_rating", 0),
        reverse=True,
    )

    return resorted_top_25 + remaining
