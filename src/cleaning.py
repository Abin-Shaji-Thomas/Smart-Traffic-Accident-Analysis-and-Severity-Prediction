"""Memory-safe loading, sampling and cleaning of the US Accidents CSV with pandas.

Author: Abin Shaji Thomas
Adapted from src/ingest.py and src/clean.py of
https://github.com/rit-vik/Accident-Severity-Prediction-and-Hotspot-Analysis-of-US-Road-Accidents-BDA-Project-
(MIT, Ritvik Kar, Dhruv Abhijit Desai, Mithil S) - see NOTICE.md.
Upstream ran these steps with PySpark on HDFS; here they are re-expressed in pandas with
chunked reading. Reused from upstream: duplicate-ID removal, the plausible-range limits for
weather values, and the 'Precipitation missing -> 0' idea (tested, see notebook 01).
Added: stratified chunked sampling, GPS audit/recovery, State+month imputation, winsorizing.
"""
from __future__ import annotations

import time

import numpy as np
import pandas as pd

from .utils import RANDOM_STATE, ROAD_FEATURES, US_LAT, US_LNG, WEATHER_NUM

CHUNKSIZE = 500_000
GRID_DEG = 0.1  # hotspot grid cell size in degrees (about 11 km north-south)

# Physically plausible ranges (from upstream clean.py). Values outside become NaN and are imputed.
PLAUSIBLE = {
    "Temperature(F)": (-60, 130),
    "Humidity(%)": (0, 100),
    "Pressure(in)": (20, 35),
    "Visibility(mi)": (0, 100),
    "Wind_Speed(mph)": (0, 200),
    "Precipitation(in)": (0, 20),
}


# --------------------------------------------------------------------------------------
# Pass 1: full-file profile (data dictionary, % missing, full-data counts, hotspot grid)
# --------------------------------------------------------------------------------------
def profile_full_file(path, chunksize: int = CHUNKSIZE) -> dict:
    """Read the whole CSV in chunks and collect statistics without holding it in memory."""
    t0 = time.time()
    total = 0
    nulls = None
    dtypes = None
    sev = pd.Series(dtype="int64")
    state = pd.Series(dtype="int64")
    year = pd.Series(dtype="int64")
    grid_parts = []
    for chunk in pd.read_csv(path, chunksize=chunksize, low_memory=False):
        total += len(chunk)
        n = chunk.isna().sum()
        nulls = n if nulls is None else nulls.add(n, fill_value=0)
        if dtypes is None:
            dtypes = chunk.dtypes.astype(str)
        sev = sev.add(chunk["Severity"].value_counts(), fill_value=0)
        state = state.add(chunk["State"].value_counts(), fill_value=0)
        yr = pd.to_datetime(chunk["Start_Time"], format="mixed", errors="coerce").dt.year
        year = year.add(yr.value_counts(), fill_value=0)
        g = chunk[["Start_Lat", "Start_Lng", "City", "State", "Severity"]].dropna(subset=["Start_Lat", "Start_Lng"])
        g = g.assign(cell_lat=(np.floor(g["Start_Lat"] / GRID_DEG) * GRID_DEG).round(1),
                     cell_lng=(np.floor(g["Start_Lng"] / GRID_DEG) * GRID_DEG).round(1),
                     severe=(g["Severity"] >= 3).astype(int))
        grid_parts.append(g.groupby(["cell_lat", "cell_lng", "City", "State"], dropna=False)
                          .agg(n=("Severity", "size"), sev_sum=("Severity", "sum"),
                               severe=("severe", "sum")).reset_index())
    grid = (pd.concat(grid_parts).groupby(["cell_lat", "cell_lng", "City", "State"], dropna=False)
            .sum().reset_index())
    return {
        "total_rows": int(total),
        "nulls": nulls.astype(int),
        "dtypes": dtypes,
        "severity_counts": sev.astype(int).sort_index(),
        "state_counts": state.astype(int).sort_values(ascending=False),
        "year_counts": year.astype(int).sort_index(),
        "grid": grid,
        "seconds": round(time.time() - t0, 1),
    }


def hotspot_table(grid: pd.DataFrame, top: int = 10) -> pd.DataFrame:
    """Top grid cells by accident count, labelled with the most frequent City, State in the cell."""
    cells = (grid.groupby(["cell_lat", "cell_lng"])
             .agg(accidents=("n", "sum"), sev_sum=("sev_sum", "sum"), severe=("severe", "sum"))
             .reset_index())
    cells["avg_severity"] = (cells["sev_sum"] / cells["accidents"]).round(3)
    cells["severe_pct"] = (100 * cells["severe"] / cells["accidents"]).round(1)
    top_cells = cells.sort_values("accidents", ascending=False).head(top).copy()
    lab = (grid.dropna(subset=["City"]).sort_values("n", ascending=False)
           .drop_duplicates(["cell_lat", "cell_lng"])[["cell_lat", "cell_lng", "City", "State"]])
    top_cells = top_cells.merge(lab, on=["cell_lat", "cell_lng"], how="left")
    top_cells["label"] = top_cells["City"] + ", " + top_cells["State"]
    top_cells["center_lat"] = (top_cells["cell_lat"] + GRID_DEG / 2).round(2)
    top_cells["center_lng"] = (top_cells["cell_lng"] + GRID_DEG / 2).round(2)
    top_cells.insert(0, "rank", range(1, len(top_cells) + 1))
    return top_cells[["rank", "label", "City", "State", "center_lat", "center_lng",
                      "accidents", "avg_severity", "severe_pct"]]


# --------------------------------------------------------------------------------------
# Pass 2: stratified chunked sample
# --------------------------------------------------------------------------------------
def stratified_chunk_sample(path, frac: float, usecols, chunksize: int = CHUNKSIZE,
                            seed: int = RANDOM_STATE) -> pd.DataFrame:
    """Take the same fraction from every Severity level of every chunk (proportional stratified sample)."""
    rng = np.random.RandomState(seed)
    parts = []
    for chunk in pd.read_csv(path, chunksize=chunksize, usecols=usecols, low_memory=False):
        parts.append(chunk.groupby("Severity", group_keys=False).sample(frac=frac, random_state=rng))
    return pd.concat(parts, ignore_index=True)


# --------------------------------------------------------------------------------------
# Cleaning steps (each returns the frame plus a small report dict)
# --------------------------------------------------------------------------------------
def parse_times(df: pd.DataFrame) -> pd.DataFrame:
    for c in ("Start_Time", "End_Time", "Weather_Timestamp"):
        if c in df:
            df[c] = pd.to_datetime(df[c], format="mixed", errors="coerce")
    return df


def drop_duplicates(df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    n0 = len(df)
    df = df.drop_duplicates(subset="ID")
    n1 = len(df)
    content = [c for c in df.columns if c != "ID"]
    df = df.drop_duplicates(subset=content)
    return df, {"rows_before": n0, "duplicate_ids": n0 - n1, "duplicate_content": n1 - len(df),
                "rows_after": len(df)}


def standardize_strings(df: pd.DataFrame) -> pd.DataFrame:
    for c in df.select_dtypes(include=["object", "string"]).columns:
        df[c] = df[c].str.strip()
        df.loc[df[c] == "", c] = np.nan
    df["State"] = df["State"].str.upper()
    if "City" in df:
        df["City"] = df["City"].str.title()
    if "Wind_Direction" in df:
        wd = df["Wind_Direction"].str.upper()
        wd = wd.replace({"CALM": "CALM", "VARIABLE": "VAR", "NORTH": "N", "SOUTH": "S",
                         "EAST": "E", "WEST": "W"})
        df["Wind_Direction"] = wd
    for c in ROAD_FEATURES:
        if c in df and df[c].dtype != bool:
            df[c] = df[c].astype(str).str.lower().map({"true": True, "false": False})
    return df


def plausible_range_to_nan(df: pd.DataFrame) -> dict:
    report = {}
    for c, (lo, hi) in PLAUSIBLE.items():
        bad = df[c].notna() & ~df[c].between(lo, hi)
        report[c] = int(bad.sum())
        df.loc[bad, c] = np.nan
    return report


def audit_gps(df: pd.DataFrame) -> dict:
    out = {}
    for lat, lng in (("Start_Lat", "Start_Lng"), ("End_Lat", "End_Lng")):
        missing = df[lat].isna() | df[lng].isna()
        oob = ~missing & ~(df[lat].between(*US_LAT) & df[lng].between(*US_LNG))
        out[lat.split("_")[0]] = {"missing": int(missing.sum()), "out_of_us_bounds": int(oob.sum())}
    return out


def handle_missing_gps(df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """Treat out-of-bounds coordinates as missing; recover Start GPS from the City+State median,
    otherwise drop the row; impute End GPS from Start GPS (assumes a point location)."""
    rep = {"before": audit_gps(df)}
    for lat, lng in (("Start_Lat", "Start_Lng"), ("End_Lat", "End_Lng")):
        oob = df[lat].notna() & df[lng].notna() & ~(df[lat].between(*US_LAT) & df[lng].between(*US_LNG))
        df.loc[oob, [lat, lng]] = np.nan
    miss = df["Start_Lat"].isna() | df["Start_Lng"].isna()
    med = df.loc[~miss].groupby(["City", "State"])[["Start_Lat", "Start_Lng"]].median()
    if miss.any():
        fill = df.loc[miss, ["City", "State"]].join(med, on=["City", "State"])
        df.loc[miss, "Start_Lat"] = fill["Start_Lat"].values
        df.loc[miss, "Start_Lng"] = fill["Start_Lng"].values
    still = df["Start_Lat"].isna() | df["Start_Lng"].isna()
    rep["start_recovered_city_state_median"] = int(miss.sum() - still.sum())
    rep["start_dropped_unrecoverable"] = int(still.sum())
    df = df.loc[~still].copy()
    end_miss = df["End_Lat"].isna() | df["End_Lng"].isna()
    df["End_GPS_Imputed"] = end_miss
    df.loc[end_miss, "End_Lat"] = df.loc[end_miss, "Start_Lat"]
    df.loc[end_miss, "End_Lng"] = df.loc[end_miss, "Start_Lng"]
    rep["end_imputed_from_start"] = int(end_miss.sum())
    rep["after"] = audit_gps(df)
    rep["rows_after"] = len(df)
    return df, rep


def winsorize(df: pd.DataFrame, cols, method: str = "iqr", k: float = 1.5,
              q: tuple = (0.005, 0.995)) -> pd.DataFrame:
    """Clip columns at IQR fences (method='iqr') or at quantiles (method='quantile'); return before/after stats."""
    rows = []
    for c in cols:
        s = df[c]
        if method == "iqr":
            q1, q3 = s.quantile([0.25, 0.75])
            lo, hi = q1 - k * (q3 - q1), q3 + k * (q3 - q1)
        else:
            lo, hi = s.quantile(list(q))
        n_clip = int(((s < lo) | (s > hi)).sum())
        before = s.describe()
        df[c] = s.clip(lo, hi)
        after = df[c].describe()
        rows.append({"column": c, "method": method, "lower": round(float(lo), 3), "upper": round(float(hi), 3),
                     "n_clipped": n_clip, "mean_before": round(before["mean"], 3), "mean_after": round(after["mean"], 3),
                     "std_before": round(before["std"], 3), "std_after": round(after["std"], 3),
                     "max_before": round(before["max"], 3), "max_after": round(after["max"], 3)})
    return pd.DataFrame(rows)


def impute_weather_categorical(df: pd.DataFrame) -> pd.DataFrame:
    """Weather_Condition and Wind_Direction -> State+Month mode (fallback: global mode)."""
    rows = []
    keys = [df["State"], df["Start_Time"].dt.month]
    for c in ("Weather_Condition", "Wind_Direction"):
        n_before = int(df[c].isna().sum())
        mode = df.groupby(keys)[c].transform(lambda s: s.mode().iloc[0] if s.notna().any() else np.nan)
        df[c] = df[c].fillna(mode).fillna(df[c].mode().iloc[0])
        rows.append({"column": c, "missing_before": n_before, "missing_after": int(df[c].isna().sum()),
                     "method": "State+Month mode"})
    return pd.DataFrame(rows)


def impute_weather_numeric(df: pd.DataFrame, dry_mask: pd.Series | None = None) -> pd.DataFrame:
    """Numeric weather -> State+Month median (fallback: global median).
    Precipitation(in): 0 where dry_mask is True (non-precipitating weather group), else State+Month median."""
    rows = []
    keys = [df["State"], df["Start_Time"].dt.month]
    for c in WEATHER_NUM:
        n_before = int(df[c].isna().sum())
        method = "State+Month median"
        if c == "Precipitation(in)" and dry_mask is not None:
            df.loc[df[c].isna() & dry_mask, c] = 0.0
            method = "0 if dry weather group, else State+Month median"
        df[c] = df[c].fillna(df.groupby(keys)[c].transform("median"))
        df[c] = df[c].fillna(df[c].median())
        rows.append({"column": c, "missing_before": n_before, "missing_after": int(df[c].isna().sum()),
                     "method": method})
    return pd.DataFrame(rows)
