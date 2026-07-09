"""Clean raw IMGW data stored in SQLite and write a query-ready 'measurements_clean' table.

IMGW status codes (from k_d_format.txt / Opis.txt):
  8 = no measurement -> value is a placeholder, treat as missing (NaN)
  9 = no phenomenon  -> phenomenon did not occur; for precipitation / snow this means 0, not missing
"""
import sqlite3
import numpy as np
import pandas as pd

DB_PATH = "imgw.db"

STATUS_MISSING = 8   # no measurement
STATUS_NO_EVENT = 9  # no phenomenon

# every value column paired with its IMGW quality-flag column
VALUE_STATUS = [
    ("tmax", "status_tmax"), ("tmin", "status_tmin"), ("tmean", "status_tmean"),
    ("tmin_ground", "status_tmin_ground"), ("precipitation", "status_precipitation"),
    ("snow_cover", "status_snow_cover"),
]
# columns where "no phenomenon" (status 9) means a real zero, not missing data
PHENOMENON = [("precipitation", "status_precipitation"), ("snow_cover", "status_snow_cover")]


# Reads the raw table produced by fetch_data.py into a DataFrame.
def load_raw(conn, table="measurements"):
    return pd.read_sql(f"SELECT * FROM {table}", conn)


# Applies the status codes, builds a date column, drops helper columns and empty rows.
# measurements_clean is temperature-complete: rows missing tmin/tmax/tmean are dropped,
# so precipitation stats downstream cover only days with valid temperatures.
def clean(df):
    df["date"] = pd.to_datetime(df[["year", "month", "day"]])

    # status 8 = no measurement -> value is unknown
    missing = 0
    for value_col, status_col in VALUE_STATUS:
        mask = df[status_col] == STATUS_MISSING
        missing += int(mask.sum())
        df.loc[mask, value_col] = np.nan

    # status 9 = no phenomenon -> for precipitation / snow this is a real 0
    zeros = 0
    for value_col, status_col in PHENOMENON:
        mask = df[status_col] == STATUS_NO_EVENT
        zeros += int(mask.sum())
        df.loc[mask, value_col] = 0

    print(f"Status 8 -> NaN: {missing} | status 9 -> 0: {zeros}")

    df = df.drop(columns=[c for c in df.columns if c.startswith("status_")])
    df = df.drop(columns=["year", "month", "day"])

    before = len(df)
    df = df.dropna(subset=["tmin", "tmax", "tmean"])
    print(f"Dropped {before - len(df)} rows missing core temperatures")

    return df.sort_values("date")


# Writes the clean table and indexes it on (station_code, date) for fast queries.
def save_clean(df, conn, table="measurements_clean"):
    df.to_sql(table, conn, if_exists="replace", index=False, chunksize=10_000)
    conn.execute(
        f"CREATE INDEX IF NOT EXISTS ix_{table}_station_date "
        f"ON {table}(station_code, date)"
    )
    conn.commit()
    print(f"Wrote {len(df)} rows to '{table}' (indexed on station_code, date)")


if __name__ == "__main__":
    conn = sqlite3.connect(DB_PATH)
    raw = load_raw(conn)
    clean_df = clean(raw)
    save_clean(clean_df, conn)
    conn.close()

    assert clean_df[["tmin", "tmax", "tmean"]].isna().sum().sum() == 0
    print(f"Done: {len(raw)} -> {len(clean_df)} rows "
          f"({100 * len(clean_df) / len(raw):.1f}% kept)")