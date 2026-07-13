# Polish Weather Data Analysis (IMGW)

Scrapes 25 years of daily weather data from Poland's IMGW, stores it in SQLite,
cleans it, and analyses long-term temperature trends.

**Skills:** web scraping · SQL · ETL · data analysis · visualization

## Pipeline

Run the three stages in order:

```bash
python fetch_data.py        # scrape IMGW  -> imgw.db (raw table)
python cleaning_data.py     # clean + index -> imgw.db (clean table)
jupyter notebook data_analysis.ipynb
```

- **`fetch_data.py`** — scrapes IMGW's yearly `_k.zip` archives with BeautifulSoup,
  unzips them in memory, lands raw rows in SQLite.
- **`cleaning_data.py`** — applies IMGW status codes (8 → missing, 9 → zero for
  precipitation/snow), builds a date column, writes an indexed `measurements_clean` table.
- **`data_analysis.ipynb`** — SQL aggregations (`GROUP BY`, `HAVING`, subqueries)
  feeding a heatmap, boxplots, a temperature–precipitation correlation, and per-station
  temperature trends.

## Key findings

- Every station warmed: +0.05 to +0.07 °C/year (2001–2023), ~0.6 °C/decade —
  from per-station regression on the balanced panel, not a cross-station average.
- Temperature and precipitation follow the seasonal cycle (Pearson r = 0.91).
- The station network shrinks over time and colder stations drop out, so a naive
  all-station average drifts upward on its own. The analysis uses a *balanced panel*
  (stations present in every year) to remove this composition artifact.

## Setup

```bash
python -m venv .venv
source .venv/bin/activate     # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

The `imgw.db` database is generated locally — run the first two scripts before the notebook.

## Data source & license

Data from the [IMGW-PIB public data portal](https://danepubliczne.imgw.pl/), used under
the Polish Act of 11 August 2021 on Open Data and the Re-use of Public Sector Information.
Free for private, non-commercial use, subject to attribution:

> Źródłem pochodzenia danych jest Instytut Meteorologii i Gospodarki Wodnej
> – Państwowy Instytut Badawczy.
>
> Dane Instytutu Meteorologii i Gospodarki Wodnej – Państwowego Instytutu
> Badawczego zostały przetworzone.
