"""Shared paths, constants and small helpers for the project.

Author: Abin Shaji Thomas
The `classification_metrics` helper is adapted from `metrics()` in src/ml2.py of
https://github.com/rit-vik/Accident-Severity-Prediction-and-Hotspot-Analysis-of-US-Road-Accidents-BDA-Project-
(MIT, Ritvik Kar, Dhruv Abhijit Desai, Mithil S) - see NOTICE.md.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import numpy as np

RANDOM_STATE = 42

ROOT = Path(__file__).resolve().parents[1]
DATA_RAW = ROOT / "data" / "raw" / "US_Accidents_March23.csv"
DATA_PROCESSED = ROOT / "data" / "processed"
DATA_SAMPLE = ROOT / "data" / "sample"
FIGURES = ROOT / "reports" / "figures"
MAPS = ROOT / "reports" / "maps"
METRICS = ROOT / "reports" / "metrics"
MODELS = ROOT / "models"

SAMPLE_PARQUET = DATA_PROCESSED / "accidents_sample.parquet"
CLEAN_PARQUET = DATA_PROCESSED / "accidents_clean.parquet"

# Bounding box of the contiguous United States (the dataset covers the lower 48 states + DC)
US_LAT = (24.39, 49.39)
US_LNG = (-124.85, -66.88)

ROAD_FEATURES = ["Amenity", "Bump", "Crossing", "Give_Way", "Junction", "No_Exit", "Railway",
                 "Roundabout", "Station", "Stop", "Traffic_Calming", "Traffic_Signal", "Turning_Loop"]

WEATHER_NUM = ["Temperature(F)", "Humidity(%)", "Pressure(in)", "Visibility(mi)",
               "Wind_Speed(mph)", "Precipitation(in)"]

WEATHER_GROUPS = ["Clear", "Cloudy", "Rain", "Snow", "Fog/Haze", "Storm", "Other"]


def ensure_dirs() -> None:
    for p in (DATA_PROCESSED, DATA_SAMPLE, FIGURES, MAPS, METRICS, MODELS):
        p.mkdir(parents=True, exist_ok=True)


def save_json(obj, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2, default=_json_default)


def load_json(path: Path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _json_default(o):
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (np.floating,)):
        return float(o)
    if isinstance(o, np.ndarray):
        return o.tolist()
    return str(o)


def safe_name(col: str) -> str:
    """Column name without spaces/brackets (from upstream ingest.py), e.g. 'Temperature(F)' -> 'Temperature_F'."""
    return re.sub(r"[^0-9a-zA-Z]+", "_", col).strip("_")


def classification_metrics(cm: np.ndarray) -> dict:
    """Metrics from a confusion matrix (rows = actual, cols = predicted). Adapted from upstream ml2.py."""
    cm = np.asarray(cm, dtype=float)
    tp = np.diag(cm)
    support = cm.sum(axis=1)
    predicted = cm.sum(axis=0)
    recall = tp / np.maximum(support, 1)
    precision = tp / np.maximum(predicted, 1)
    f1 = 2 * precision * recall / np.maximum(precision + recall, 1e-12)
    out = {"accuracy": tp.sum() / cm.sum(),
           "weighted_f1": (f1 * support).sum() / support.sum(),
           "macro_f1": f1.mean(),
           "balanced_acc": recall.mean()}
    out.update({f"recall_sev{i + 1}": recall[i] for i in range(len(tp))})
    out.update({f"precision_sev{i + 1}": precision[i] for i in range(len(tp))})
    return {k: round(float(v), 4) for k, v in out.items()}
