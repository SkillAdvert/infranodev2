from __future__ import annotations

from typing import Any, Dict, Optional

TNUOS_ZONES_HARDCODED = {
    "GZ1": {
        "name": "North Scotland",
        "tariff": 15.32,
        "bounds": {"min_lat": 57.5, "max_lat": 61.0, "min_lng": -6.0, "max_lng": -1.5},
    },
    "GZ2": {
        "name": "South Scotland",
        "tariff": 14.87,
        "bounds": {"min_lat": 55.0, "max_lat": 57.5, "min_lng": -4.0, "max_lng": -1.5},
    },
    "GZ3": {
        "name": "Borders",
        "tariff": 13.45,
        "bounds": {"min_lat": 54.5, "max_lat": 56.0, "min_lng": -4.0, "max_lng": -1.5},
    },
    "GZ4": {
        "name": "Central Scotland",
        "tariff": 12.98,
        "bounds": {"min_lat": 55.5, "max_lat": 56.5, "min_lng": -5.0, "max_lng": -3.0},
    },
    "GZ5": {
        "name": "Argyll",
        "tariff": 11.67,
        "bounds": {"min_lat": 55.0, "max_lat": 57.0, "min_lng": -6.0, "max_lng": -4.0},
    },
    "GZ6": {
        "name": "Dumfries",
        "tariff": 10.34,
        "bounds": {"min_lat": 54.5, "max_lat": 55.5, "min_lng": -4.5, "max_lng": -2.5},
    },
    "GZ7": {
        "name": "Ayr",
        "tariff": 9.87,
        "bounds": {"min_lat": 54.8, "max_lat": 55.5, "min_lng": -5.0, "max_lng": -3.5},
    },
    "GZ8": {
        "name": "Central Belt",
        "tariff": 8.92,
        "bounds": {"min_lat": 55.2, "max_lat": 56.0, "min_lng": -4.5, "max_lng": -3.0},
    },
    "GZ9": {
        "name": "Lothian",
        "tariff": 7.56,
        "bounds": {"min_lat": 55.5, "max_lat": 56.2, "min_lng": -3.5, "max_lng": -2.0},
    },
    "GZ10": {
        "name": "Southern Scotland",
        "tariff": 6.23,
        "bounds": {"min_lat": 54.8, "max_lat": 55.5, "min_lng": -3.5, "max_lng": -1.5},
    },
    "GZ11": {
        "name": "North East England",
        "tariff": 5.67,
        "bounds": {"min_lat": 54.0, "max_lat": 55.5, "min_lng": -3.0, "max_lng": -0.5},
    },
    "GZ12": {
        "name": "Yorkshire",
        "tariff": 4.89,
        "bounds": {"min_lat": 53.0, "max_lat": 54.5, "min_lng": -3.0, "max_lng": -0.5},
    },
    "GZ13": {
        "name": "Humber",
        "tariff": 4.12,
        "bounds": {"min_lat": 52.5, "max_lat": 53.5, "min_lng": -2.0, "max_lng": 0.5},
    },
    "GZ14": {
        "name": "North West England",
        "tariff": 3.78,
        "bounds": {"min_lat": 52.5, "max_lat": 54.5, "min_lng": -3.5, "max_lng": -1.5},
    },
    "GZ15": {
        "name": "East Midlands",
        "tariff": 2.95,
        "bounds": {"min_lat": 51.5, "max_lat": 53.0, "min_lng": -2.5, "max_lng": 0.0},
    },
    "GZ16": {
        "name": "West Midlands",
        "tariff": 2.34,
        "bounds": {"min_lat": 51.5, "max_lat": 52.7, "min_lng": -3.0, "max_lng": -1.5},
    },
    "GZ17": {
        "name": "East England",
        "tariff": 1.87,
        "bounds": {"min_lat": 51.5, "max_lat": 52.5, "min_lng": -0.5, "max_lng": 1.5},
    },
    "GZ18": {
        "name": "South Wales",
        "tariff": 1.45,
        "bounds": {"min_lat": 51.2, "max_lat": 52.0, "min_lng": -3.5, "max_lng": -2.0},
    },
    "GZ19": {
        "name": "North Wales",
        "tariff": 0.98,
        "bounds": {"min_lat": 52.3, "max_lat": 53.5, "min_lng": -3.8, "max_lng": -2.8},
    },
    "GZ20": {
        "name": "Pembroke",
        "tariff": 0.67,
        "bounds": {"min_lat": 51.6, "max_lat": 52.1, "min_lng": -5.5, "max_lng": -4.8},
    },
    "GZ21": {
        "name": "South West England",
        "tariff": -0.12,
        "bounds": {"min_lat": 50.5, "max_lat": 51.5, "min_lng": -4.5, "max_lng": -2.0},
    },
    "GZ22": {
        "name": "Cornwall",
        "tariff": -0.45,
        "bounds": {"min_lat": 49.9, "max_lat": 50.7, "min_lng": -5.5, "max_lng": -4.5},
    },
    "GZ23": {
        "name": "London",
        "tariff": -0.78,
        "bounds": {"min_lat": 51.2, "max_lat": 51.8, "min_lng": -0.5, "max_lng": 0.5},
    },
    "GZ24": {
        "name": "South East England",
        "tariff": -1.23,
        "bounds": {"min_lat": 50.5, "max_lat": 51.5, "min_lng": -2.0, "max_lng": 1.5},
    },
    "GZ25": {
        "name": "Kent",
        "tariff": -1.56,
        "bounds": {"min_lat": 50.8, "max_lat": 51.5, "min_lng": 0.2, "max_lng": 1.8},
    },
    "GZ26": {
        "name": "Southern England",
        "tariff": -1.89,
        "bounds": {"min_lat": 50.5, "max_lat": 51.2, "min_lng": -2.5, "max_lng": 0.0},
    },
    "GZ27": {
        "name": "Solent",
        "tariff": -2.34,
        "bounds": {"min_lat": 50.6, "max_lat": 51.0, "min_lng": -2.0, "max_lng": -1.0},
    },
}

LCOE_CONFIG = {
    "baseline_pounds_per_mwh": 60.0,
    "gamma_slope": 0.04,
    "min_lcoe": 45.0,
    "max_lcoe": 100.0,
    "zone_specific_rates": {},
}


def find_tnuos_zone(latitude: float, longitude: float) -> Optional[Dict[str, Any]]:
    """Find TNUoS zone for given coordinates using hard-coded bounding boxes."""

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
    """Convert TNUoS tariff (£/kW) to 0-100 investment score."""

    min_tariff = -3.0
    max_tariff = 16.0

    if tariff <= min_tariff:
        return 100.0
    if tariff >= max_tariff:
        return 0.0

    normalized = (tariff - min_tariff) / (max_tariff - min_tariff)
    return 100.0 * (1.0 - normalized)


def calculate_tnuos_score(project_lat: float, project_lng: float) -> float:
    lat_normalized = (project_lat - 49.5) / (60.0 - 49.5)
    estimated_tariff = -2.0 + (17.0 * lat_normalized)
    min_tariff = -3.0
    max_tariff = 16.0
    if estimated_tariff <= min_tariff:
        percentile_score = 100.0
    elif estimated_tariff >= max_tariff:
        percentile_score = 0.0
    else:
        normalized_position = (estimated_tariff - min_tariff) / (max_tariff - min_tariff)
        percentile_score = 100.0 * (1.0 - normalized_position)
    return min(100.0, max(0.0, percentile_score))


__all__ = [
    "TNUOS_ZONES_HARDCODED",
    "LCOE_CONFIG",
    "find_tnuos_zone",
    "calculate_tnuos_score_from_tariff",
    "calculate_tnuos_score",
]
