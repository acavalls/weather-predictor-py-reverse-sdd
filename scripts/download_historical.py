"""Fetch historical weather data from Open-Meteo Archive API for multiple cities.

Downloads hourly data (2023-2025) for temperature, humidity, pressure,
precipitation, and wind speed. Outputs a single combined CSV file.

Usage:
    python scripts/download_historical.py
    python scripts/download_historical.py --output custom.csv
    python scripts/download_historical.py --cities Madrid London Tokyo
"""

import argparse
import logging
import time
from pathlib import Path
from typing import List, Optional, Tuple

import httpx
import pandas as pd

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

# Cities: (name, latitude, longitude)
CITIES: List[Tuple[str, float, float]] = [
    ("Madrid", 40.4168, -3.7038),
    ("London", 51.5074, -0.1278),
    ("Tokyo", 35.6762, 139.6503),
    ("New York", 40.7128, -74.0060),
    ("Sydney", -33.8688, 151.2093),
    ("São Paulo", -23.5505, -46.6333),
    ("Cairo", 30.0444, 31.2357),
    ("Mumbai", 19.0760, 72.8777),
    ("Berlin", 52.5200, 13.4050),
    ("Mexico City", 19.4326, -99.1332),
]

VARIABLES = [
    "temperature_2m",
    "relative_humidity_2m",
    "surface_pressure",
    "wind_speed_10m",
    "cloud_cover",
    "wind_direction_10m",
    "dew_point_2m",
    "precipitation",
]

START_YEAR = 2023
END_YEAR = 2025
DELAY_SECONDS = 1
MAX_RETRIES = 3
BASE_URL = "https://archive-api.open-meteo.com/v1/archive"


def fetch_year_data(
    client: httpx.Client,
    city_name: str,
    lat: float,
    lon: float,
    year: int,
) -> pd.DataFrame:
    """Fetch one year of hourly data for a city from Open-Meteo Archive API."""
    params = {
        "latitude": lat,
        "longitude": lon,
        "start_date": f"{year}-01-01",
        "end_date": f"{year}-12-31",
        "hourly": ",".join(VARIABLES),
    }

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = client.get(BASE_URL, params=params, timeout=60.0)
            response.raise_for_status()
            data = response.json()

            hourly = data.get("hourly", {})
            if not hourly or "time" not in hourly:
                logger.warning(f"No hourly data for {city_name} ({year})")
                return pd.DataFrame()

            df = pd.DataFrame(hourly)
            df["time"] = pd.to_datetime(df["time"])
            df["city"] = city_name
            df["lat"] = lat
            df["lon"] = lon
            return df

        except (httpx.RequestError, httpx.HTTPStatusError) as exc:
            logger.warning(f"Attempt {attempt}/{MAX_RETRIES} failed for {city_name} ({year}): {exc}")
            if attempt < MAX_RETRIES:
                time.sleep(2**attempt)
            else:
                logger.error(f"All retries exhausted for {city_name} ({year})")
                return pd.DataFrame()

    return pd.DataFrame()


def download_historical(
    output_path: str = "data/historical_weather.csv",
    city_filter: Optional[List[str]] = None,
) -> None:
    """Download historical weather data for all configured cities."""
    cities = CITIES
    if city_filter:
        filter_set = {c.lower() for c in city_filter}
        cities = [(name, lat, lon) for name, lat, lon in cities if name.lower() in filter_set]
        if not cities:
            logger.error(f"No cities matched filter: {city_filter}")
            return

    total_requests = len(cities) * (END_YEAR - START_YEAR + 1)
    logger.info(
        f"Starting download: {len(cities)} cities × {END_YEAR - START_YEAR + 1} years = {total_requests} requests"
    )

    all_frames: List[pd.DataFrame] = []

    with httpx.Client() as client:
        request_count = 0
        for city_name, lat, lon in cities:
            for year in range(START_YEAR, END_YEAR + 1):
                request_count += 1
                logger.info(f"[{request_count}/{total_requests}] Fetching {city_name} ({year})")

                df = fetch_year_data(client, city_name, lat, lon, year)
                if not df.empty:
                    all_frames.append(df)

                if request_count < total_requests:
                    time.sleep(DELAY_SECONDS)

    if not all_frames:
        logger.error("No data downloaded. Check network or API availability.")
        return

    combined = pd.concat(all_frames, ignore_index=True)
    combined = combined.rename(columns={"time": "datetime"})
    combined = combined[["city", "lat", "lon", "datetime"] + VARIABLES]
    combined = combined.sort_values(["city", "datetime"]).reset_index(drop=True)

    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    combined.to_csv(output, index=False)

    logger.info(f"Saved {len(combined)} rows to {output}")


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(description="Download historical weather data from Open-Meteo")
    parser.add_argument(
        "--output",
        default="data/historical_weather.csv",
        help="Output CSV path (default: data/historical_weather.csv)",
    )
    parser.add_argument(
        "--cities",
        nargs="+",
        default=None,
        help="Filter cities by name (e.g., --cities Madrid London)",
    )
    args = parser.parse_args()
    download_historical(output_path=args.output, city_filter=args.cities)


if __name__ == "__main__":
    main()
