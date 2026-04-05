"""Weather data from Open-Meteo (free, no API key)."""
import httpx
import logging

logger = logging.getLogger(__name__)

GEOCODE_URL = "https://geocoding-api.open-meteo.com/v1/search"
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"
AIR_URL = "https://air-quality-api.open-meteo.com/v1/air-quality"

WMO_CODES = {
    0: "Clear sky", 1: "Mainly clear", 2: "Partly cloudy", 3: "Overcast",
    45: "Foggy", 48: "Rime fog", 51: "Light drizzle", 53: "Moderate drizzle",
    55: "Dense drizzle", 61: "Slight rain", 63: "Moderate rain", 65: "Heavy rain",
    71: "Slight snow", 73: "Moderate snow", 75: "Heavy snow", 80: "Rain showers",
    81: "Moderate rain showers", 82: "Violent rain showers",
    95: "Thunderstorm", 96: "Thunderstorm with hail", 99: "Thunderstorm with heavy hail",
}


async def geocode(location: str) -> dict:
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(GEOCODE_URL, params={"name": location, "count": 1})
        resp.raise_for_status()
        results = resp.json().get("results", [])
        if not results:
            raise ValueError(f"Location not found: {location}")
        r = results[0]
        return {"name": r["name"], "country": r.get("country", ""), "latitude": r["latitude"], "longitude": r["longitude"]}


async def fetch_current_weather(location: str) -> dict:
    geo = await geocode(location)
    params = {"latitude": geo["latitude"], "longitude": geo["longitude"],
              "current": "temperature_2m,relative_humidity_2m,apparent_temperature,precipitation,wind_speed_10m,weather_code",
              "timezone": "auto"}
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(FORECAST_URL, params=params)
        resp.raise_for_status()
    c = resp.json().get("current", {})
    return {"location": geo, "current": {
        "temperature_c": c.get("temperature_2m"), "feels_like_c": c.get("apparent_temperature"),
        "humidity_pct": c.get("relative_humidity_2m"), "precipitation_mm": c.get("precipitation"),
        "wind_speed_kmh": c.get("wind_speed_10m"), "weather_code": c.get("weather_code"),
        "description": WMO_CODES.get(c.get("weather_code", 0), "Unknown"), "time": c.get("time"),
    }}


async def fetch_forecast(location: str, days: int = 7) -> dict:
    geo = await geocode(location)
    params = {"latitude": geo["latitude"], "longitude": geo["longitude"],
              "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum,weather_code,sunrise,sunset",
              "timezone": "auto", "forecast_days": min(days, 16)}
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(FORECAST_URL, params=params)
        resp.raise_for_status()
    d = resp.json().get("daily", {})
    forecast = []
    for i, date in enumerate(d.get("time", [])):
        forecast.append({"date": date, "temp_max_c": d["temperature_2m_max"][i], "temp_min_c": d["temperature_2m_min"][i],
                         "precipitation_mm": d["precipitation_sum"][i], "weather_code": d["weather_code"][i],
                         "description": WMO_CODES.get(d["weather_code"][i], "Unknown"),
                         "sunrise": d["sunrise"][i], "sunset": d["sunset"][i]})
    return {"location": geo, "days": len(forecast), "forecast": forecast}


async def fetch_historical_weather(location: str, start_date: str, end_date: str) -> dict:
    geo = await geocode(location)
    params = {"latitude": geo["latitude"], "longitude": geo["longitude"], "start_date": start_date, "end_date": end_date,
              "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum,weather_code", "timezone": "auto"}
    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.get(ARCHIVE_URL, params=params)
        resp.raise_for_status()
    d = resp.json().get("daily", {})
    history = []
    for i, date in enumerate(d.get("time", [])):
        history.append({"date": date, "temp_max_c": d["temperature_2m_max"][i], "temp_min_c": d["temperature_2m_min"][i],
                         "precipitation_mm": d["precipitation_sum"][i], "description": WMO_CODES.get(d["weather_code"][i], "Unknown")})
    return {"location": geo, "days": len(history), "history": history}


async def fetch_air_quality(location: str) -> dict:
    geo = await geocode(location)
    params = {"latitude": geo["latitude"], "longitude": geo["longitude"],
              "current": "european_aqi,us_aqi,pm10,pm2_5,nitrogen_dioxide,ozone"}
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(AIR_URL, params=params)
        resp.raise_for_status()
    c = resp.json().get("current", {})
    aqi = c.get("us_aqi", 0)
    cat = "Good" if aqi <= 50 else "Moderate" if aqi <= 100 else "Unhealthy for Sensitive" if aqi <= 150 else "Unhealthy" if aqi <= 200 else "Very Unhealthy" if aqi <= 300 else "Hazardous"
    return {"location": geo, "air_quality": {"us_aqi": aqi, "category": cat, "european_aqi": c.get("european_aqi"),
            "pm10": c.get("pm10"), "pm2_5": c.get("pm2_5"), "nitrogen_dioxide": c.get("nitrogen_dioxide"), "ozone": c.get("ozone")}}
