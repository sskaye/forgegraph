"""Write examples/sample-data/: datasets for trying ForgeGraph and its skill by hand.

uv run python scripts/build_sample_data.py

Each file is a synthetic look-alike of a dataset that data-visualization tutorials use
(seaborn, ggplot2, Vega-Lite, R's datasets): the same columns, shapes and quirks, with
generated values. Only anscombe.csv holds real published numbers (Anscombe, 1973). A few
files are deliberately messy, as real exports are. examples/sample-data/README.md says what
each one holds.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
from openpyxl import Workbook

OUT = Path(__file__).parents[1] / "examples" / "sample-data"
MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def iris() -> pd.DataFrame:
    rng = np.random.default_rng(11)
    rows = []
    for species, means, sds in [
        ("setosa", (5.01, 3.43, 1.46, 0.25), (0.35, 0.38, 0.17, 0.11)),
        ("versicolor", (5.94, 2.77, 4.26, 1.33), (0.52, 0.31, 0.47, 0.20)),
        ("virginica", (6.59, 2.97, 5.55, 2.03), (0.64, 0.32, 0.55, 0.27)),
    ]:
        for _ in range(50):
            m = [max(0.1, rng.normal(mu, sd)) for mu, sd in zip(means, sds, strict=True)]
            rows.append([*(round(v, 1) for v in m), species])
    return pd.DataFrame(
        rows, columns=["sepal_length", "sepal_width", "petal_length", "petal_width", "species"]
    )


def penguins() -> pd.DataFrame:
    """With missing measurements written NA, as the palmerpenguins CSV has them."""
    rng = np.random.default_rng(12)
    rows = []
    spec = [
        ("Adelie", 152, ["Torgersen", "Biscoe", "Dream"], (38.8, 18.3, 190, 3700)),
        ("Chinstrap", 68, ["Dream"], (48.8, 18.4, 196, 3733)),
        ("Gentoo", 124, ["Biscoe"], (47.5, 15.0, 217, 5076)),
    ]
    for species, n, islands, (bl, bd, fl, mass) in spec:
        for i in range(n):
            male = i % 2 == 0
            k = 1.04 if male else 0.96
            rows.append(
                [
                    species,
                    islands[i % len(islands)],
                    round(rng.normal(bl * k, 2.5), 1),
                    round(rng.normal(bd * k, 0.9), 1),
                    int(rng.normal(fl * k, 6)),
                    int(round(rng.normal(mass * k**2, 350), -1)),
                    "male" if male else "female",
                    2007 + i % 3,
                ]
            )
    frame = pd.DataFrame(
        rows,
        columns=[
            "species", "island", "bill_length_mm", "bill_depth_mm", "flipper_length_mm",
            "body_mass_g", "sex", "year",
        ],
    ).astype(object)  # fmt: skip
    for i in (3, 271):  # two birds with no measurements
        frame.loc[i, ["bill_length_mm", "bill_depth_mm", "flipper_length_mm", "body_mass_g"]] = "NA"
    for i in (8, 9, 10, 11, 47, 178, 218, 256, 268):
        frame.loc[i, "sex"] = "NA"
    return frame


def anscombe() -> pd.DataFrame:
    """Anscombe's quartet (1973): four datasets with the same summary statistics."""
    x = [10, 8, 13, 9, 11, 14, 6, 4, 12, 7, 5]
    data = {
        "I": (x, [8.04, 6.95, 7.58, 8.81, 8.33, 9.96, 7.24, 4.26, 10.84, 4.82, 5.68]),
        "II": (x, [9.14, 8.14, 8.74, 8.77, 9.26, 8.10, 6.13, 3.10, 9.13, 7.26, 4.74]),
        "III": (x, [7.46, 6.77, 12.74, 7.11, 7.81, 8.84, 6.08, 5.39, 8.15, 6.42, 5.73]),
        "IV": (
            [8, 8, 8, 8, 8, 8, 8, 19, 8, 8, 8],
            [6.58, 5.76, 7.71, 8.84, 8.47, 7.04, 5.25, 12.50, 5.56, 7.91, 6.89],
        ),
    }
    rows = [[name, a, b] for name, (xs, ys) in data.items() for a, b in zip(xs, ys, strict=True)]
    return pd.DataFrame(rows, columns=["dataset", "x", "y"])


def co2() -> pd.DataFrame:
    """Monthly CO2 at a mountain observatory, the NOAA way: -99.99 marks a missing month."""
    rows = []
    for year in range(1958, 2025):
        for month in range(1, 13):
            if year == 1958 and month < 3:
                continue
            t = year - 1958 + (month - 0.5) / 12
            trend = 315 + 0.8 * t + 0.0125 * t * t
            season = 3.0 * np.sin(2 * np.pi * (month - 2) / 12) - 0.6 * np.cos(
                4 * np.pi * month / 12
            )
            value = round(trend + season + 0.15 * np.sin(7 * t), 2)
            missing = (year, month) in {(1958, 6), (1958, 10), (1964, 2), (1964, 3), (1964, 4)}
            rows.append(
                [f"{year}-{month:02d}-15", year, month, round(year + (month - 0.5) / 12, 3),
                 -99.99 if missing else value]
            )  # fmt: skip
    return pd.DataFrame(rows, columns=["date", "year", "month", "decimal_year", "co2_ppm"])


def air_passengers() -> tuple[pd.DataFrame, pd.DataFrame]:
    """Monthly airline passengers 1949-1960, in thousands: growing, with a summer peak that
    grows with it. Long (one row per month) and the classic wide table (a column per month)."""
    season = [0.89, 0.86, 0.99, 0.96, 0.96, 1.10, 1.22, 1.21, 1.06, 0.92, 0.80, 0.90]
    rng = np.random.default_rng(13)
    long_rows, wide_rows = [], []
    for y, year in enumerate(range(1949, 1961)):
        row = [year]
        for m in range(12):
            trend = 126 * np.exp(0.105 * (y + m / 12))
            value = round(float(trend * season[m] * rng.normal(1, 0.02)))
            long_rows.append([f"{year}-{m + 1:02d}", value])
            row.append(value)
        wide_rows.append(row)
    return (
        pd.DataFrame(long_rows, columns=["month", "passengers"]),
        pd.DataFrame(wide_rows, columns=["Year", *MONTHS]),
    )


def stocks() -> pd.DataFrame:
    """Monthly closing prices, long form, dates written like 'Jan 1 2000'. One symbol starts
    later than the rest."""
    rng = np.random.default_rng(14)
    rows = []
    for symbol, start, first, drift, vol in [
        ("MSFT", date(2000, 1, 1), 39.8, 0.000, 0.08),
        ("AMZN", date(2000, 1, 1), 64.6, 0.010, 0.15),
        ("IBM", date(2000, 1, 1), 100.5, 0.002, 0.06),
        ("GOOG", date(2004, 8, 1), 102.4, 0.020, 0.10),
        ("AAPL", date(2000, 1, 1), 25.9, 0.018, 0.12),
    ]:
        price, d = first, start
        while d <= date(2010, 3, 1):
            rows.append([symbol, f"{MONTHS[d.month - 1]} 1 {d.year}", round(price, 2)])
            price *= float(np.exp(rng.normal(drift, vol)))
            d = date(d.year + (d.month == 12), d.month % 12 + 1, 1)
    return pd.DataFrame(rows, columns=["symbol", "date", "price"])


COUNTRIES = {
    "Africa": ["Algeria", "Angola", "Botswana", "Cameroon", "Egypt", "Ethiopia", "Ghana",
               "Kenya", "Morocco", "Nigeria", "Senegal", "South Africa", "Tanzania", "Uganda"],
    "Americas": ["Argentina", "Bolivia", "Brazil", "Canada", "Chile", "Colombia",
                 "Costa Rica", "Cuba", "Mexico", "Peru", "United States", "Uruguay"],
    "Asia": ["Bangladesh", "China", "India", "Indonesia", "Japan", "Korea, Rep.", "Malaysia",
             "Nepal", "Pakistan", "Philippines", "Thailand", "Vietnam"],
    "Europe": ["Austria", "Belgium", "Denmark", "Finland", "France", "Germany", "Greece",
               "Italy", "Netherlands", "Norway", "Poland", "Portugal", "Spain", "Sweden",
               "United Kingdom"],
    "Oceania": ["Australia", "New Zealand"],
}  # fmt: skip


def gapminder() -> pd.DataFrame:
    """Countries every five years: life expectancy, population and GDP per capita."""
    rng = np.random.default_rng(15)
    start = {"Africa": 900, "Americas": 3500, "Asia": 1200, "Europe": 6500, "Oceania": 10000}
    rows = []
    for continent, names in COUNTRIES.items():
        for name in names:
            gdp = start[continent] * float(np.exp(rng.normal(0, 0.5)))
            growth = rng.normal(0.022, 0.012)
            pop = float(np.exp(rng.normal(16.3, 1.2)))
            for i, year in enumerate(range(1952, 2008, 5)):
                g = gdp * np.exp(growth * 5 * i)
                life = 20 + 11.5 * np.log10(g) + 0.18 * i + rng.normal(0, 1.5)
                rows.append(
                    [name, continent, year, round(min(life, 83.0), 1),
                     int(pop * 1.018 ** (5 * i)), round(g, 1)]
                )  # fmt: skip
    return pd.DataFrame(
        rows, columns=["country", "continent", "year", "lifeExp", "pop", "gdpPercap"]
    )


def diamonds(n: int = 15000) -> pd.DataFrame:
    """Many points: price against carat spans orders of magnitude."""
    rng = np.random.default_rng(16)
    cuts = ["Fair", "Good", "Very Good", "Premium", "Ideal"]
    colors = list("DEFGHIJ")
    clarities = ["I1", "SI2", "SI1", "VS2", "VS1", "VVS2", "VVS1", "IF"]
    carat = np.clip(rng.lognormal(-0.45, 0.55, n), 0.2, 4.5).round(2)
    cut = rng.choice(cuts, n, p=[0.03, 0.09, 0.22, 0.26, 0.40])
    color = rng.choice(colors, n)
    clarity = rng.choice(clarities, n, p=[0.02, 0.17, 0.24, 0.23, 0.15, 0.09, 0.07, 0.03])
    k = (
        np.array([cuts.index(c) for c in cut]) * 0.03
        - np.array([colors.index(c) for c in color]) * 0.06
        + np.array([clarities.index(c) for c in clarity]) * 0.08
    )
    price = np.exp(8.4 + 1.75 * np.log(carat) + k + rng.normal(0, 0.18, n)).round()
    return pd.DataFrame(
        {
            "carat": carat,
            "cut": cut,
            "color": color,
            "clarity": clarity,
            "depth": rng.normal(61.7, 1.4, n).round(1),
            "table": rng.normal(57.4, 2.2, n).round(),
            "price": price.astype(int),
        }
    )


def weather(path: Path) -> None:
    """Daily weather for four years, in an Excel workbook with real dates and a notes sheet."""
    rng = np.random.default_rng(17)
    wb = Workbook()
    about = wb.active
    assert about is not None
    about.title = "About"
    about.append(["Daily weather, synthetic, for trying ForgeGraph."])
    about.append(["Temperatures in °C, precipitation in mm, wind in m/s."])
    sheet = wb.create_sheet("Daily")
    sheet.append(["date", "precipitation", "temp_max", "temp_min", "wind", "weather"])
    d = date(2012, 1, 1)
    while d <= date(2015, 12, 31):
        doy = d.timetuple().tm_yday
        mean = 11 - 8 * np.cos(2 * np.pi * (doy - 15) / 365)
        wet = rng.random() < 0.55 - 0.3 * np.sin(2 * np.pi * (doy - 100) / 365)
        rain = round(float(rng.gamma(1.2, 4.0)), 1) if wet else 0.0
        tmax = round(mean + 4 + rng.normal(0, 2.5), 1)
        tmin = round(mean - 4 + rng.normal(0, 2.0), 1)
        kind = "rain" if rain > 2 else "drizzle" if rain > 0 else "sun"
        sheet.append([d, rain, tmax, tmin, round(float(rng.gamma(3, 1.1)), 1), kind])
        d += timedelta(days=1)
    for row in sheet.iter_rows(min_row=2, max_col=1):
        row[0].number_format = "yyyy-mm-dd"
    wb.save(path)


def fmri() -> pd.DataFrame:
    """Repeated measures: a response over time for 14 subjects, two events, two regions."""
    rng = np.random.default_rng(18)
    t = np.arange(19)
    shape = (t / 5) ** 2 * np.exp(-((t / 5) ** 2) + 1)
    rows = []
    for s in range(14):
        gain = rng.normal(1, 0.25)
        for event, amp in (("stim", 0.22), ("cue", 0.06)):
            for region, scale in (("parietal", 1.0), ("frontal", 0.6)):
                for ti in t:
                    v = amp * scale * gain * shape[ti] - 0.03 + rng.normal(0, 0.02)
                    rows.append([f"s{s}", int(ti), event, region, round(float(v), 4)])
    return pd.DataFrame(rows, columns=["subject", "timepoint", "event", "region", "signal"])


def enzyme() -> pd.DataFrame:
    """Reaction rate against substrate concentration, treated and untreated (Michaelis-Menten)."""
    rng = np.random.default_rng(19)
    rows = []
    for state, vmax, km in (("treated", 212.7, 0.064), ("untreated", 160.3, 0.048)):
        for c in (0.02, 0.06, 0.11, 0.22, 0.56, 1.10):
            for _ in range(2):
                rows.append([c, round(vmax * c / (km + c) * rng.normal(1, 0.04)), state])
    return pd.DataFrame(rows, columns=["conc_ppm", "rate_counts_per_min", "state"])


def dose_response() -> pd.DataFrame:
    """Three compounds over a dilution series that starts at 0: a log x axis can't show 0."""
    rng = np.random.default_rng(20)
    rows = []
    for compound, ec50, top in (
        ("Compound A", 0.8, 98),
        ("Compound B", 4.0, 92),
        ("Compound C", 25, 80),
    ):
        for dose in (0, 0.01, 0.03, 0.1, 0.3, 1, 3, 10, 30, 100):
            for rep in (1, 2, 3):
                resp = 2 + (top - 2) * dose / (dose + ec50) + rng.normal(0, 2.5)
                rows.append([compound, rep, dose, round(float(resp), 1)])
    return pd.DataFrame(rows, columns=["compound", "replicate", "dose_uM", "response_pct"])


def assay_summary() -> pd.DataFrame:
    """dose_response summarised: each compound and dose's mean response and its SD."""
    stats = dose_response().groupby(["compound", "dose_uM"], sort=False)["response_pct"]
    out = stats.agg(mean_response_pct="mean", sd_pct="std").reset_index()
    return out.round({"mean_response_pct": 1, "sd_pct": 2})


def fuel_cells() -> tuple[pd.DataFrame, pd.DataFrame]:
    """Three fuel cells on a 200-hour durability test at 1 A/cm², logged every 2 hours: cell
    voltage and high-frequency resistance (HFR), with a gap where cell C's logger dropped out;
    and each cell's polarization curve, measured once after the test. The cell that degrades
    fastest also has the worst curve."""
    rng = np.random.default_rng(24)
    log, curves = [], []
    for cell, v0, decay, hfr0, drift in (
        ("Cell A", 0.718, 0.00040, 62.0, 0.020),
        ("Cell B", 0.716, 0.00078, 64.0, 0.045),
        ("Cell C", 0.721, 0.00121, 61.0, 0.080),
    ):
        for hour in range(0, 201, 2):
            if cell == "Cell C" and 96 <= hour <= 104:
                continue
            voltage = v0 - decay * hour + rng.normal(0, 0.0025)
            hfr = hfr0 + drift * hour + rng.normal(0, 0.6)
            log.append([hour, cell, round(float(voltage), 4), round(float(hfr), 1)])
        loss = 0.11 + 0.9 * decay * 100  # ohmic and mass-transport loss after the test
        for j in np.round(np.arange(0, 1.61, 0.05), 2):
            voltage = 0.95 - 0.048 * np.log1p(12 * j) - loss * j - 0.02 * j**3
            curves.append([cell, float(j), round(float(voltage + rng.normal(0, 0.002)), 4)])
    return (
        pd.DataFrame(log, columns=["hours", "cell", "voltage_v", "hfr_mohm_cm2"]),
        pd.DataFrame(curves, columns=["cell", "current_density_a_cm2", "voltage_v"]),
    )


def geyser() -> pd.DataFrame:
    """Eruption length and the wait before it: two clusters."""
    rng = np.random.default_rng(21)
    rows = []
    for _ in range(272):
        long = rng.random() < 0.64
        dur = rng.normal(4.3, 0.4) if long else rng.normal(2.0, 0.3)
        wait = rng.normal(80, 5.5) if long else rng.normal(54.5, 5.8)
        rows.append([round(float(dur), 3), int(wait), "long" if long else "short"])
    return pd.DataFrame(rows, columns=["duration", "waiting", "kind"])


def tips() -> pd.DataFrame:
    """Restaurant bills and tips: mostly categories, which an xy graph can only color by."""
    rng = np.random.default_rng(22)
    rows = []
    for _ in range(244):
        size = int(rng.choice([1, 2, 3, 4, 5, 6], p=[0.02, 0.64, 0.15, 0.15, 0.02, 0.02]))
        bill = round(float(np.clip(rng.normal(8 + 5 * size, 5), 3, 51)), 2)
        tip = round(float(np.clip(bill * rng.normal(0.16, 0.05), 1, 10)), 2)
        day = str(rng.choice(["Thur", "Fri", "Sat", "Sun"], p=[0.25, 0.08, 0.36, 0.31]))
        time = "Lunch" if day in ("Thur", "Fri") and rng.random() < 0.8 else "Dinner"
        rows.append(
            [bill, tip, rng.choice(["Female", "Male"]), rng.choice(["No", "Yes"]), day, time, size]
        )
    return pd.DataFrame(rows, columns=["total_bill", "tip", "sex", "smoker", "day", "time", "size"])


def growth() -> pd.DataFrame:
    """Body weight over time for 50 animals on four diets; a few stop early."""
    rng = np.random.default_rng(23)
    rows = []
    for animal in range(1, 51):
        diet = 1 + (animal - 1) * 4 // 50
        rate = 0.15 + 0.012 * diet + rng.normal(0, 0.012)
        stop = 21 if rng.random() > 0.08 else int(rng.choice([8, 12, 16]))
        for day in range(0, stop + 1, 2):
            weight = 41 * np.exp(rate * day * (1 - day / 80)) * rng.normal(1, 0.02)
            rows.append([animal, diet, day, int(weight)])
    return pd.DataFrame(rows, columns=["animal", "diet", "day", "weight_g"])


def seaice() -> pd.DataFrame:
    """Daily sea-ice extent with missing days, left empty."""
    rng = np.random.default_rng(24)
    rows = []
    d = date(2015, 1, 1)
    while d <= date(2019, 12, 31):
        doy = d.timetuple().tm_yday
        extent = 11.5 + 3.8 * np.cos(2 * np.pi * (doy - 70) / 365) - 0.05 * (d.year - 2015)
        gap = date(2017, 3, 2) <= d <= date(2017, 3, 30) or rng.random() < 0.01
        rows.append([d.isoformat(), "" if gap else round(float(extent + rng.normal(0, 0.06)), 3)])
        d += timedelta(days=1)
    return pd.DataFrame(rows, columns=["Date", "Extent (million km²)"])


def economics() -> pd.DataFrame:
    """Monthly economic series side by side, each in its own units."""
    rng = np.random.default_rng(25)
    rows = []
    unemploy, psav = 2900.0, 12.0
    for i in range(12 * 48):
        y, m = 1967 + i // 12, i % 12 + 1
        unemploy = max(2000.0, unemploy * float(np.exp(rng.normal(0.002, 0.03))))
        psav = float(np.clip(psav + rng.normal(-0.01, 0.4), 2, 17))
        pce = round(507 * np.exp(0.065 * i / 12), 1)
        pop = int(198712 * 1.0095 ** (i / 12))
        uempmed = round(float(np.clip(4.5 + unemploy / 1500 + rng.normal(0, 0.4), 4, 25)), 1)
        rows.append([f"{y}-{m:02d}-01", pce, pop, round(psav, 1), uempmed, int(unemploy)])
    return pd.DataFrame(rows, columns=["date", "pce", "pop", "psavert", "uempmed", "unemploy"])


def lab_export(path: Path) -> None:
    """An instrument export: a summary sheet first; on the data sheet, title rows above the
    header, a units row under it, '-' and 'n/a' for missing readings, and an average row and
    an end note under the data."""
    rng = np.random.default_rng(26)
    wb = Workbook()
    summary = wb.active
    assert summary is not None
    summary.title = "Summary"
    summary.append(["Conductivity run 14"])
    summary.append(["Samples", 40])
    summary.append(["See the Data sheet for readings."])
    sheet = wb.create_sheet("Data")
    sheet.append(["Conductivity run 14 — export"])
    sheet.append(["Instrument: CM-200", None, "Operator: QA"])
    sheet.append(["Exported 2026-03-02 14:05"])
    sheet.append([])
    sheet.append(["Sample ID", "Time", "Temperature", "Conductivity"])
    sheet.append([None, "(min)", "(°C)", "(mS/cm)"])
    temps, conds = [], []
    for i in range(40):
        t = round(20 + 0.6 * i + rng.normal(0, 0.2), 1)
        c = round(1.20 + 0.021 * (t - 20) + rng.normal(0, 0.01), 3)
        temp: object = t
        cond: object = c
        if i == 12:
            cond = "-"
        if i == 27:
            temp = "n/a"
        sheet.append([f"S-{i + 1:03d}", i * 3, temp, cond])
        temps.append(t)
        conds.append(c)
    sheet.append([])
    sheet.append(
        ["Average", None, round(float(np.mean(temps)), 1), round(float(np.mean(conds)), 3)]
    )
    sheet.append(["End of report"])
    wb.save(path)


def lab_runs(path: Path) -> None:
    """A lab's instrument run log, as a LIMS exports it: title rows above the header, one row
    per run (start and finish times, instrument, operator, method, samples, status), a few
    statuses typed differently ("completed", "Completed "), runs still going at the end, and
    a total under the data. HPLC-02 is down for maintenance for two weeks in August; GC-MS-01
    takes on a new method in September. An Instruments sheet follows."""
    rng = np.random.default_rng(31)
    instruments = {"HPLC-01": 4.4, "HPLC-02": 3.6, "GC-MS-01": 2.2, "ICP-OES-01": 1.8}
    methods = {
        "HPLC-01": ["Assay-A", "Impurities-B"],
        "HPLC-02": ["Assay-A", "Dissolution-C"],
        "GC-MS-01": ["Residual solvents", "Volatiles screen"],
        "ICP-OES-01": ["Metals panel"],
    }
    operators = ["AK", "BT", "CR", "DM", "EL"]
    start, end = date(2026, 7, 6), date(2026, 10, 16)
    rows = []
    day = start
    while day <= end:
        if day.weekday() < 5:
            for name, per_day in instruments.items():
                rate = per_day
                if name == "HPLC-02" and date(2026, 8, 17) <= day <= date(2026, 8, 28):
                    rate = 0.0  # maintenance
                if name == "GC-MS-01" and day >= date(2026, 9, 1):
                    rate *= 1.6  # the new method
                for _ in range(int(rng.poisson(rate))):
                    started = datetime(day.year, day.month, day.day, 7) + timedelta(
                        minutes=int(rng.integers(0, 600))
                    )
                    rows.append((started, name))
        day += timedelta(days=1)
    rows.sort()
    wb = Workbook()
    sheet = wb.active
    assert sheet is not None
    sheet.title = "Runs"
    sheet.append(["Instrument run log"])
    sheet.append([f"Exported {end.isoformat()} 18:02 from LIMS, all instruments"])
    sheet.append([])
    sheet.append(
        ["Run ID", "Started", "Finished", "Instrument", "Operator", "Method", "Samples",
         "Status", "Notes"]
    )  # fmt: skip
    last = datetime(end.year, end.month, end.day, 16)
    for i, (started, name) in enumerate(rows):
        status = str(rng.choice(["Completed", "Failed", "Aborted"], p=[0.9, 0.06, 0.04]))
        if started > last:
            status = "In progress"
        elif status == "Completed" and rng.random() < 0.03:
            status = str(rng.choice(["completed", "Completed "]))
        minutes = int(rng.integers(25, 180))
        finished = started + timedelta(minutes=minutes) if status != "In progress" else None
        note = {"Failed": "pressure fault", "Aborted": "stopped by operator"}.get(status, "")
        sheet.append(
            [
                f"R-{26000 + i}",
                started,
                finished,
                name,
                str(rng.choice(operators)),
                str(rng.choice(methods[name])),
                int(rng.integers(4, 40)),
                status,
                note or None,
            ]
        )
    sheet.append([])
    sheet.append([f"Total runs: {len(rows)}"])
    info = wb.create_sheet("Instruments")
    info.append(["Instrument", "Type", "Location"])
    for name, kind, where in (
        ("HPLC-01", "HPLC", "Lab 2"),
        ("HPLC-02", "HPLC", "Lab 2"),
        ("GC-MS-01", "GC-MS", "Lab 3"),
        ("ICP-OES-01", "ICP-OES", "Lab 3"),
    ):
        info.append([name, kind, where])
    wb.save(path)


def european_csv(path: Path) -> None:
    """A CSV the way European settings save one: semicolons between fields, decimal commas,
    day-first dates, Windows-1252 text."""
    rng = np.random.default_rng(27)
    lines = ["Zeitpunkt;Temperatur (°C);Luftfeuchte (%)"]
    for i in range(48):
        temp = 18 + 4 * np.sin(2 * np.pi * i / 24) + rng.normal(0, 0.3)
        hum = 55 - 10 * np.sin(2 * np.pi * i / 24) + rng.normal(0, 1)
        stamp = f"{i // 24 + 1:02d}.03.2026 {i % 24:02d}:00"
        lines.append(
            f"{stamp};{temp:.1f};{hum:.1f}".replace(".", ",").replace(",03,2026", ".03.2026")
        )
    path.write_bytes(("\n".join(lines) + "\n").encode("windows-1252"))


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    iris().to_csv(OUT / "iris.csv", index=False)
    penguins().to_csv(OUT / "penguins.csv", index=False)
    anscombe().to_csv(OUT / "anscombe.csv", index=False)
    co2().to_csv(OUT / "co2_monthly.csv", index=False)
    long, wide = air_passengers()
    long.to_csv(OUT / "air_passengers.csv", index=False)
    wide.to_csv(OUT / "air_passengers_by_month.csv", index=False)
    stocks().to_csv(OUT / "stocks.csv", index=False)
    gapminder().to_csv(OUT / "gapminder.csv", index=False)
    diamonds().to_csv(OUT / "diamonds.csv", index=False)
    weather(OUT / "weather.xlsx")
    fmri().to_csv(OUT / "fmri.csv", index=False)
    enzyme().to_csv(OUT / "enzyme_kinetics.csv", index=False)
    dose_response().to_csv(OUT / "dose_response.csv", index=False)
    assay_summary().to_csv(OUT / "assay_summary.csv", index=False)
    durability, polarization = fuel_cells()
    durability.to_csv(OUT / "cell_durability.csv", index=False)
    polarization.to_csv(OUT / "cell_polarization.csv", index=False)
    geyser().to_csv(OUT / "geyser.csv", index=False)
    tips().to_csv(OUT / "tips.csv", index=False)
    growth().to_csv(OUT / "growth.csv", index=False)
    seaice().to_csv(OUT / "seaice.csv", index=False)
    economics().to_csv(OUT / "economics.csv", index=False)
    lab_export(OUT / "lab_export.xlsx")
    lab_runs(OUT / "lab_runs.xlsx")
    european_csv(OUT / "sensor_log_eu.csv")
    print(f"wrote {len([p for p in OUT.iterdir() if p.suffix != '.md'])} data files to {OUT}")


if __name__ == "__main__":
    main()
