# Geocoding via OpenStreetMap Nominatim
import httpx

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"

async def geocode(address: str):
    params = {"q": address, "format": "json"}
    async with httpx.AsyncClient() as client:
        r = await client.get(NOMINATIM_URL, params=params, headers={"User-Agent": "SentinelHome"})
        return r.json()
