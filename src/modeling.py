"""Severity classification with scikit-learn: feature pipeline, models, evaluation.

Author: Abin Shaji Thomas
Adapted from src/ml.py and src/ml2.py of
https://github.com/rit-vik/Accident-Severity-Prediction-and-Hotspot-Analysis-of-US-Road-Accidents-BDA-Project-
(MIT, Ritvik Kar, Dhruv Abhijit Desai, Mithil S) - see NOTICE.md.
Reused from upstream: the feature list (location, weather, time, road flags, State, weather group, Day/Night,
wind direction), the leakage rule (no duration/Distance/year), the majority baseline and the inverse-vs-sqrt
class-weighting comparison. Re-expressed in scikit-learn (upstream used Spark MLlib StringIndexer/OneHotEncoder/
VectorAssembler). Added: Decision Tree and HistGradientBoosting, City frequency + top-N encoding, stratified split,
randomized search, ROC-AUC, cross-validation, permutation importance.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, TransformerMixin
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import HistGradientBoostingClassifier, RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.tree import DecisionTreeClassifier
from sklearn.metrics import (accuracy_score, balanced_accuracy_score, confusion_matrix, f1_score,
                             precision_recall_fscore_support, roc_auc_score)
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from .utils import RANDOM_STATE, ROAD_FEATURES

NUM_FEATURES = ["Start_Lat", "Start_Lng", "Temperature(F)", "Humidity(%)", "Pressure(in)", "Visibility(mi)",
                "Wind_Speed(mph)", "Precipitation(in)", "Hour", "DayOfWeek", "Month", "IsWeekend", "IsRushHour",
                "RoadFeatureCount"]
BOOL_FEATURES = [c for c in ROAD_FEATURES if c != "Turning_Loop"]   # Turning_Loop is constant (dropped in Module 1)
CAT_FEATURES = ["State", "WeatherGroup", "DayNight", "Wind_Direction"]
CITY = "City"
DISTANCE = "Distance(mi)"
LABELS = [1, 2, 3, 4]
MODEL_NAMES = ["Decision Tree", "Random Forest", "Logistic Regression", "HistGradientBoosting"]
SCALED = {"Logistic Regression"}   # only the linear model needs standardised inputs


class CityEncoder(BaseEstimator, TransformerMixin):
    """Frequency encoding plus one-hot of the top-N cities (others -> 'Other'). Fitted on training data only."""

    def __init__(self, top_n: int = 30):
        self.top_n = top_n

    def fit(self, X, y=None):
        s = pd.Series(np.asarray(X).ravel())
        vc = s.value_counts(normalize=True)
        self.freq_ = vc.to_dict()
        self.top_ = list(vc.index[: self.top_n])
        return self

    def transform(self, X):
        s = pd.Series(np.asarray(X).ravel())
        freq = s.map(self.freq_).fillna(0.0).to_numpy()[:, None]
        onehot = np.column_stack([(s == c).to_numpy() for c in self.top_]).astype(float)
        return np.hstack([freq, onehot])

    def get_feature_names_out(self, input_features=None):
        return np.array(["City_freq"] + [f"City_{c}" for c in self.top_])


def feature_columns(with_distance: bool) -> list[str]:
    return NUM_FEATURES + ([DISTANCE] if with_distance else []) + BOOL_FEATURES + CAT_FEATURES + [CITY]


def make_preprocessor(with_distance: bool, scale: bool) -> ColumnTransformer:
    num = NUM_FEATURES + ([DISTANCE] if with_distance else [])
    return ColumnTransformer([
        ("num", StandardScaler() if scale else "passthrough", num),
        ("bool", "passthrough", BOOL_FEATURES),
        ("cat", OneHotEncoder(handle_unknown="ignore", min_frequency=50, sparse_output=False), CAT_FEATURES),
        ("city", CityEncoder(top_n=30), [CITY]),
    ], verbose_feature_names_out=False)


def make_pipeline(model, with_distance: bool, scale: bool) -> Pipeline:
    return Pipeline([("prep", make_preprocessor(with_distance, scale)), ("model", model)])


def make_model(name: str, params: dict | None = None):
    """Unfitted estimator with class_weight='balanced' and random_state=42 (where supported)."""
    params = dict(params or {})
    if name == "Decision Tree":
        return DecisionTreeClassifier(class_weight="balanced", random_state=RANDOM_STATE, **params)
    if name == "Random Forest":
        return RandomForestClassifier(class_weight="balanced", n_jobs=-1, random_state=RANDOM_STATE, **params)
    if name == "Logistic Regression":
        return LogisticRegression(class_weight="balanced", max_iter=1000, **params)
    if name == "HistGradientBoosting":
        return HistGradientBoostingClassifier(class_weight="balanced", random_state=RANDOM_STATE, **params)
    raise ValueError(name)


def build_pipeline(name: str, params: dict | None = None, with_distance: bool = False) -> Pipeline:
    return make_pipeline(make_model(name, params), with_distance, scale=name in SCALED)


def slug(name: str) -> str:
    return name.lower().replace(" ", "_")


def sqrt_balanced_weights(y) -> np.ndarray:
    """Square root of the 'balanced' (inverse-frequency) class weight, per sample (upstream ml2.py 'sqrt' scheme)."""
    y = np.asarray(y)
    classes, counts = np.unique(y, return_counts=True)
    w = {c: np.sqrt(len(y) / (len(classes) * n)) for c, n in zip(classes, counts)}
    return np.array([w[v] for v in y])


def evaluate(y_true, y_pred, y_proba=None) -> dict:
    p, r, f, s = precision_recall_fscore_support(y_true, y_pred, labels=LABELS, zero_division=0)
    out = {"accuracy": accuracy_score(y_true, y_pred),
           "balanced_accuracy": balanced_accuracy_score(y_true, y_pred),
           "macro_f1": f1_score(y_true, y_pred, average="macro"),
           "weighted_f1": f1_score(y_true, y_pred, average="weighted")}
    if y_proba is not None:
        out["roc_auc_ovr_macro"] = roc_auc_score(y_true, y_proba, multi_class="ovr", average="macro", labels=LABELS)
    for i, lab in enumerate(LABELS):
        out[f"precision_sev{lab}"] = p[i]; out[f"recall_sev{lab}"] = r[i]; out[f"f1_sev{lab}"] = f[i]
    return {k: round(float(v), 4) for k, v in out.items()}


def normalized_confusion(y_true, y_pred) -> pd.DataFrame:
    cm = confusion_matrix(y_true, y_pred, labels=LABELS, normalize="true")
    return pd.DataFrame(cm, index=[f"Sev{l}" for l in LABELS], columns=[f"Pred{l}" for l in LABELS])
