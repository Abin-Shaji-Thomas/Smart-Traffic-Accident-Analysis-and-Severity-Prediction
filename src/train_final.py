"""Rebuild the final severity model deterministically (Abin Shaji Thomas).

Reads the best model name and tuned parameters from reports/metrics/best_model.json, recreates the same
stratified 80/20 split (random_state=42), fits ONE sklearn Pipeline (preprocessing + model) on the training
part and saves it to models/best_model.joblib (compress=3). Notebook 04 calls the same function.

Run:  .venv\\Scripts\\python.exe -m src.train_final
"""
from __future__ import annotations

import joblib
import pandas as pd
from sklearn.model_selection import train_test_split

from . import modeling as M
from .utils import CLEAN_PARQUET, METRICS, MODELS, RANDOM_STATE, load_json

MODEL_PATH = MODELS / "best_model.joblib"


def split(df: pd.DataFrame, with_distance: bool = False):
    X = df[M.feature_columns(with_distance)]
    y = df["Severity"]
    return train_test_split(X, y, test_size=0.2, stratify=y, random_state=RANDOM_STATE)


def train_and_save(name: str, params: dict, df: pd.DataFrame | None = None):
    df = pd.read_parquet(CLEAN_PARQUET) if df is None else df
    X_train, _, y_train, _ = split(df, with_distance=False)
    pipe = M.build_pipeline(name, params, with_distance=False).fit(X_train, y_train)
    MODELS.mkdir(parents=True, exist_ok=True)
    joblib.dump(pipe, MODEL_PATH, compress=3)
    return pipe, MODEL_PATH.stat().st_size / 1e6


if __name__ == "__main__":
    best = load_json(METRICS / "best_model.json")
    _, mb = train_and_save(best["best_model"], best["params"])
    print(f"Saved {MODEL_PATH} ({mb:.1f} MB) - {best['best_model']} {best['params']}")
