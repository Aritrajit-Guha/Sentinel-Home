# Geocoding via OpenStreetMap Nominatim
import httpx

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"

def geocode(address: str):
    params = {"q": address, "format": "json"}
    response = httpx.get(
        NOMINATIM_URL,
        params=params,
        headers={"User-Agent": "SentinelHome beginner demo"},
        timeout=15.0,
    )
    response.raise_for_status()
    return response.json()
