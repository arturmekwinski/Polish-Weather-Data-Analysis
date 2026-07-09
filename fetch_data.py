"""Download IMGW daily climate data and load it into SQLite."""
import io
import sqlite3
import zipfile
from urllib.parse import urljoin

import pandas as pd
import requests
from bs4 import BeautifulSoup

BASE_URL = ("https://danepubliczne.imgw.pl/data/dane_pomiarowo_obserwacyjne/"
            "dane_meteorologiczne/dobowe/klimat/")

# IMGW CSVs ship without a header row, so column names are supplied manually.
# Order matches the k_d_ file layout documented in IMGW's k_d_format.txt.
COLUMNS = ["station_code", "station_name", "year", "month", "day",
           "tmax", "status_tmax", "tmin", "status_tmin", "tmean", "status_tmean",
           "tmin_ground", "status_tmin_ground", "precipitation", "status_precipitation",
           "precipitation_type", "snow_cover", "status_snow_cover"]

# Measurement columns to coerce to numbers; the rest stay as text/flags.
NUMERIC = ["tmax", "tmin", "tmean", "tmin_ground", "precipitation", "snow_cover"]

# One shared session: reuses the TCP connection across requests and sends a
# descriptive User-Agent instead of the default python-requests one.
session = requests.Session()

def list_zip_urls(year):
    """Scrape a year's directory page and return the URLs of its _k.zip archives."""
    response = session.get(f"{BASE_URL}{year}/", timeout=30)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "lxml")
    # Only _k.zip holds the daily climate data; urljoin turns hrefs into absolute URLs.
    return [urljoin(response.url, a["href"]) for a in soup.find_all("a", href=True)
            if a["href"].endswith("_k.zip")]


def download_year(year):
    """Download and parse every climate CSV for a single year into one DataFrame."""
    dfs = []
    for zip_url in list_zip_urls(year):
        try:
            response = session.get(zip_url, timeout=30)
            response.raise_for_status()
            # Unzip in memory (BytesIO) — no temp files touch disk.
            with zipfile.ZipFile(io.BytesIO(response.content)) as zf:
                for name in zf.namelist():
                    # skip k_d_t_ files: different schema (temp/humidity/wind/cloud, not precip)
                    if name.endswith(".csv") and "k_d_t" not in name:
                        # windows-1250: IMGW's encoding for Polish station names.
                        dfs.append(pd.read_csv(zf.open(name), encoding="windows-1250",
                                               header=None, names=COLUMNS))
        # Skip a corrupt or unreachable archive instead of killing the whole run.
        except (zipfile.BadZipFile, requests.RequestException) as e:
            print(f"Skipped {zip_url}: {e}")
    print(f"Year {year}: {sum(len(d) for d in dfs)} rows")
    # Empty fallback keeps the schema stable if a year yields nothing.
    return pd.concat(dfs, ignore_index=True) if dfs else pd.DataFrame(columns=COLUMNS)


def download_all(years):
    """Fetch all requested years and return a single typed DataFrame."""
    df = pd.concat([download_year(y) for y in years], ignore_index=True)
    # errors="coerce" turns any unparseable value into NaN rather than raising.
    for col in NUMERIC:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    return df


if __name__ == "__main__":
    df = download_all(range(2001, 2026))

    conn = sqlite3.connect("imgw.db")
    # Raw landing table; cleaning_data.py reads it and writes measurements_clean.
    df.to_sql("measurements", conn, if_exists="replace", index=False)
    conn.close()

    print("Saved database to: imgw.db")