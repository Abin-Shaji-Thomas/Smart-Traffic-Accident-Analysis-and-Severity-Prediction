"""Feature engineering: time features, weather grouping, road-feature count.

Author: Abin Shaji Thomas
Time features and the regex-based weather grouping are adapted from src/clean.py of
https://github.com/rit-vik/Accident-Severity-Prediction-and-Hotspot-Analysis-of-US-Road-Accidents-BDA-Project-
(MIT, Ritvik Kar, Dhruv Abhijit Desai, Mithil S) - see NOTICE.md.
Changes: the 7 project weather groups (Storm split from Rain), rush-hour flag, Day/Night,
road-feature count, duration in minutes (EDA only - it is known only after the event).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from .utils import ROAD_FEATURES

# Order matters: the first matching pattern wins.
WEATHER_PATTERNS = [
    ("Storm", r"thunder|t-storm|storm|tornado|squall|hail|funnel"),
    ("Snow", r"snow|sleet|ice|wintry|freezing"),
    ("Rain", r"rain|drizzle|shower"),
    ("Fog/Haze", r"fog|mist|haze|smoke|dust|sand"),
    ("Cloudy", r"cloud|overcast"),
    ("Clear", r"clear|fair"),
]
WET_GROUPS = {"Rain", "Snow", "Storm"}


def weather_group(cond: pd.Series) -> pd.Series:
    wc = cond.fillna("").str.lower()
    out = pd.Series("Other", index=cond.index, dtype=object)
    assigned = pd.Series(False, index=cond.index)
    for name, pat in WEATHER_PATTERNS:
        m = ~assigned & wc.str.contains(pat, regex=True)
        out[m] = name
        assigned |= m
    return out


def add_time_features(df: pd.DataFrame) -> pd.DataFrame:
    st = df["Start_Time"]
    df["Hour"] = st.dt.hour.astype("int8")
    df["DayOfWeek"] = st.dt.dayofweek.astype("int8")      # 0 = Monday ... 6 = Sunday
    df["DayName"] = st.dt.day_name()
    df["Month"] = st.dt.month.astype("int8")
    df["Year"] = st.dt.year.astype("int16")
    df["YearMonth"] = st.dt.to_period("M").astype(str)
    df["IsWeekend"] = (df["DayOfWeek"] >= 5).astype("int8")
    rush = df["Hour"].isin([7, 8, 9, 16, 17, 18])
    df["IsRushHour"] = (rush & (df["IsWeekend"] == 0)).astype("int8")
    # Day/Night from the dataset's Sunrise_Sunset; missing values filled from the hour (06-17 = Day)
    dn = df["Sunrise_Sunset"].copy() if "Sunrise_Sunset" in df else pd.Series(np.nan, index=df.index)
    dn = dn.fillna(pd.Series(np.where(df["Hour"].between(6, 17), "Day", "Night"), index=df.index))
    df["DayNight"] = dn
    if "End_Time" in df:
        df["Duration_min"] = (df["End_Time"] - st).dt.total_seconds() / 60
    return df


def add_road_feature_count(df: pd.DataFrame) -> pd.DataFrame:
    cols = [c for c in ROAD_FEATURES if c in df]
    df["RoadFeatureCount"] = df[cols].astype(int).sum(axis=1).astype("int8")
    return df
