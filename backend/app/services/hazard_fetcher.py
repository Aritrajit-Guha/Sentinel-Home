"""Public hazard-data clients and household-level hazard normalization."""

from math import asin, cos, radians, sin, sqrt

import httpx

USGS_URL = "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/significant_week.geojson"
OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"

def fetch_earthquake_data():
    response = httpx.get(USGS_URL, timeout=15.0)
    response.raise_for_status()
    return response.json()


def fetch_weather_data(lat: float, lon: float):
    params = {"latitude": lat, "longitude": lon, "current_weather": True}
    response = httpx.get(OPEN_METEO_URL, params=params, timeout=15.0)
    response.raise_for_status()
    return response.json()


def distance_km(latitude_a: float, longitude_a: float, latitude_b: float, longitude_b: float) -> float:
    """Return the great-circle distance between two coordinates."""
    earth_radius_km = 6371.0
    lat_a, lat_b = radians(latitude_a), radians(latitude_b)
    delta_lat = radians(latitude_b - latitude_a)
    delta_lon = radians(longitude_b - longitude_a)

    haversine = (
        sin(delta_lat / 2) ** 2
        + cos(lat_a) * cos(lat_b) * sin(delta_lon / 2) ** 2
    )
    return 2 * earth_radius_km * asin(sqrt(haversine))


def nearby_earthquakes(
    latitude: float,
    longitude: float,
    *,
    radius_km: float = 500.0,
    earthquake_data: dict | None = None,
) -> list[dict]:
    """Return normalized USGS events within ``radius_km`` of a household.

    ``earthquake_data`` is injectable so this transformation can be tested
    without making a network request.
    """
    if radius_km <= 0:
        raise ValueError("radius_km must be greater than zero")

    payload = earthquake_data if earthquake_data is not None else fetch_earthquake_data()
    nearby = []

    for feature in payload.get("features", []):
        geometry = feature.get("geometry") or {}
        coordinates = geometry.get("coordinates") or []
        if len(coordinates) < 2 or coordinates[0] is None or coordinates[1] is None:
            continue

        event_longitude, event_latitude = float(coordinates[0]), float(coordinates[1])
        distance = distance_km(latitude, longitude, event_latitude, event_longitude)
        if distance > radius_km:
            continue

        properties = feature.get("properties") or {}
        nearby.append({
            "id": feature.get("id"),
            "magnitude": properties.get("mag"),
            "place": properties.get("place"),
            "time": properties.get("time"),
            "url": properties.get("url"),
            "latitude": event_latitude,
            "longitude": event_longitude,
            "depth_km": coordinates[2] if len(coordinates) > 2 else None,
            "distance_km": round(distance, 2),
        })

    return sorted(nearby, key=lambda event: event["distance_km"])
