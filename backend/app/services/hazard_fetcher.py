# Phase 2: pulls live hazard data from USGS Earthquake API and Open-Meteo
import httpx

USGS_URL = "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/significant_week.geojson"
OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"

async def fetch_earthquake_data():
    async with httpx.AsyncClient() as client:
        r = await client.get(USGS_URL)
        return r.json()

async def fetch_weather_data(lat: float, lon: float):
    params = {"latitude": lat, "longitude": lon, "current_weather": True}
    async with httpx.AsyncClient() as client:
        r = await client.get(OPEN_METEO_URL, params=params)
        return r.json()
