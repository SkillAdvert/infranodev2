"""Data transformation functions for TEC and project data."""

from __future__ import annotations

from typing import Any, Dict, Optional, Tuple

from infrastructure import _coerce_float
from models import TecConnectionFeature, TecConnectionGeometry, TecConnectionProperties


def _extract_coordinates(row: Dict[str, Any]) -> Tuple[Optional[float], Optional[float]]:
    """Return latitude/longitude from heterogeneous Supabase payloads."""

    latitude: Optional[float] = None
    longitude: Optional[float] = None

    latitude_keys = [
        "latitude",
        "lat",
        "Latitude",
        "Latitude_deg",
    ]
    longitude_keys = [
        "longitude",
        "lon",
        "lng",
        "Longitude",
        "Longitude_deg",
    ]

    for key in latitude_keys:
        if key in row:
            latitude = _coerce_float(row.get(key))
            if latitude is not None:
                break

    for key in longitude_keys:
        if key in row:
            longitude = _coerce_float(row.get(key))
            if longitude is not None:
                break

    if (latitude is None or longitude is None) and isinstance(row.get("location"), dict):
        location_data = row.get("location")
        latitude = latitude or _coerce_float(
            location_data.get("lat") or location_data.get("latitude")
        )
        longitude = longitude or _coerce_float(
            location_data.get("lon")
            or location_data.get("lng")
            or location_data.get("longitude")
        )

    if (latitude is None or longitude is None) and isinstance(row.get("coordinates"), (list, tuple)):
        coords = row.get("coordinates")
        if len(coords) >= 2:
            longitude = longitude or _coerce_float(coords[0])
            latitude = latitude or _coerce_float(coords[1])

    return latitude, longitude


def transform_tec_to_project_schema(tec_row: Dict[str, Any]) -> Dict[str, Any]:
    """Transform a TEC connections database row to unified project schema.

    TEC table has different field names than renewable_projects, so we map them:
    - project_name → site_name
    - development_status → development_status_short
    - Coordinates might be NULL (we'll handle that separately)
    """

    latitude, longitude = _extract_coordinates(tec_row)

    return {
        "id": tec_row.get("id"),
        "ref_id": str(tec_row.get("id", "")),
        "site_name": tec_row.get("project_name") or "Untitled Project",
        "project_name": tec_row.get("project_name"),
        "capacity_mw": _coerce_float(tec_row.get("capacity_mw")) or 0.0,
        "technology_type": tec_row.get("technology_type") or "Unknown",
        "development_status_short": tec_row.get("development_status") or "Scoping",
        "development_status": tec_row.get("development_status"),
        "constraint_status": tec_row.get("constraint_status"),
        "connection_site": tec_row.get("connection_site"),
        "substation_name": tec_row.get("substation_name"),
        "voltage_kv": _coerce_float(tec_row.get("voltage")),
        "latitude": latitude,
        "longitude": longitude,
        "county": None,
        "country": "UK",
        "operator": tec_row.get("operator") or tec_row.get("customer_name"),
        "_source_table": "tec_connections",
    }


def transform_tec_row_to_feature(row: Dict[str, Any]) -> Optional[TecConnectionFeature]:
    """Transform a Supabase TEC row into a GeoJSON feature."""

    try:
        lat, lon = _extract_coordinates(row)

        if lat is None or lon is None:
            print(f"⚠️ Skip TEC '{row.get('project_name')}' - no coords")
            return None

        capacity_mw = _coerce_float(row.get("capacity_mw"))
        voltage = _coerce_float(row.get("voltage"))
        technology_type = row.get("technology_type")
        operator = row.get("operator") or row.get("customer_name")
        customer_name = row.get("customer_name") or row.get("operator")

        return TecConnectionFeature(
            id=str(row.get("id")),
            geometry=TecConnectionGeometry(coordinates=[lon, lat]),
            properties=TecConnectionProperties(
                id=row.get("id"),
                project_name=row.get("project_name") or "Untitled",
                operator=operator,
                customer_name=customer_name,
                capacity_mw=capacity_mw,
                mw_delta=capacity_mw,
                technology_type=technology_type,
                plant_type=technology_type,
                project_status=row.get("development_status"),
                latitude=lat,
                longitude=lon,
                connection_site=row.get("connection_site"),
                substation_name=row.get("substation_name"),
                voltage=voltage,
                constraint_status=row.get("constraint_status"),
                created_at=row.get("created_at"),
            ),
        )
    except Exception as exc:  # pragma: no cover - diagnostic logging only
        print(f"❌ Transform error row {row.get('id')}: {exc}")
        return None
