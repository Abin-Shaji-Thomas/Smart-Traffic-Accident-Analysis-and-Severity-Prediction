"""Shared helpers for the Streamlit app: page setup, cached loaders, colours, prediction (Abin Shaji Thomas).

The app only READS saved files (data/processed, reports/metrics, reports/figures, reports/maps, models).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src import features as F  # noqa: E402
from src import modeling as M  # noqa: E402
from src.utils import CLEAN_PARQUET, DATA_PROCESSED, FIGURES, MAPS, METRICS, MODELS, WEATHER_GROUPS  # noqa: E402
from src.viz import SEVERITY, WEATHER_COLORS  # noqa: E402

SEV_COLORS = {str(k): v for k, v in SEVERITY.items()}          # same colour per severity on every page
SEV_COLORS.update({f"Severity {k}": v for k, v in SEVERITY.items()})
GITHUB = "https://github.com/Abin-Shaji-Thomas/Smart-Traffic-Accident-Analysis-and-Severity-Prediction"
TEAM = [("Abin Shaji Thomas", "URK24CS6007"), ("Jinto Joseph", "URK24CS1210"), ("BÉAL Elouan", "ISK26CS1005")]
SUPERVISOR = "Dr. Anusha Bamini A M, Assistant Professor, Division of Computer Science and Engineering"
COURSE = "Data Science Ecosystem (25CS305) - end-semester project (Project 3)"
INSTITUTE = "Karunya Institute of Technology and Sciences"
MODEL_PATH = MODELS / "best_model.joblib"

# command that creates each kind of file (shown when a file is missing)
HOW_TO = {
    "accidents_clean.parquet": r".venv\Scripts\python.exe -m nbconvert --to notebook --execute --inplace notebooks\01_data_science_concepts.ipynb",
    "full_hotspot_grid.parquet": r".venv\Scripts\python.exe -m nbconvert --to notebook --execute --inplace notebooks\01_data_science_concepts.ipynb",
    "best_model.joblib": r".venv\Scripts\python.exe -m src.train_final",
    "mongo_results.json": r".venv\Scripts\python.exe bigdata\mongodb\queries.py",
    "mapreduce_counters.json": r".venv\Scripts\python.exe bigdata\hadoop_mapreduce\run_pipeline.py",
    "bigdata_crosscheck.json": r".venv\Scripts\python.exe -m src.bigdata_check",
    "dataset_profile.json": r".venv\Scripts\python.exe scripts\profile_dataset.py",
}


def setup(title: str, subtitle: str) -> None:
    st.set_page_config(page_title=title, layout="wide")
    st.markdown("<style>h1{font-size:2.0rem !important} .block-container{padding-top:2rem}</style>", unsafe_allow_html=True)
    st.title(title)
    st.caption(subtitle)


def require(path: Path) -> Path:
    """Stop the page with a clear message if a required file is missing."""
    if not path.exists():
        cmd = HOW_TO.get(path.name)
        if cmd is None:
            nb = {"figures": "the notebook that saves it", "metrics": "the notebook that saves it"}.get(path.parent.name, "the notebooks")
            cmd = f"run {nb} (see README)"
        st.warning(f"Missing file `{path.relative_to(ROOT)}`. Create it with:")
        st.code(cmd, language="powershell")
        st.stop()
    return path


@st.cache_data(show_spinner=False)
def _read_json(path: str, mtime: float):
    return json.loads(Path(path).read_text(encoding="utf-8"))


@st.cache_data(show_spinner=False)
def _read_csv(path: str, mtime: float, index_col):
    return pd.read_csv(path, index_col=index_col)


@st.cache_data(show_spinner="Loading data ...")
def _read_parquet(path: str, mtime: float, columns: tuple | None):
    return pd.read_parquet(path, columns=list(columns) if columns else None)


def metric_json(name: str) -> dict:
    p = require(METRICS / name)
    return _read_json(str(p), p.stat().st_mtime)


def metric_csv(name: str, index_col=None) -> pd.DataFrame:
    p = require(METRICS / name)
    return _read_csv(str(p), p.stat().st_mtime, index_col)


def clean_data(columns=None) -> pd.DataFrame:
    p = require(CLEAN_PARQUET)
    return _read_parquet(str(p), p.stat().st_mtime, tuple(columns) if columns else None)


def hotspot_grid() -> pd.DataFrame:
    p = require(DATA_PROCESSED / "full_hotspot_grid.parquet")
    return _read_parquet(str(p), p.stat().st_mtime, None)


def figure(name: str, caption: str | None = None) -> None:
    p = require(FIGURES / name)
    st.image(str(p), caption=caption, width="stretch")


@st.cache_resource(show_spinner="Loading model ...")
def _load_model(path: str, mtime: float):
    import joblib
    return joblib.load(path)


def model():
    p = require(MODEL_PATH)
    return _load_model(str(p), p.stat().st_mtime)


# ---------------------------------------------------------------- prediction
def build_row(values: dict, when: pd.Timestamp) -> pd.DataFrame:
    """One input row with exactly the model's feature columns; time features come from src.features."""
    row = pd.DataFrame([{**values, "Start_Time": pd.Timestamp(when)}])
    row = F.add_time_features(row)
    row = F.add_road_feature_count(row)
    return row[M.feature_columns(with_distance=False)]


def predict_proba(pipe, row: pd.DataFrame) -> pd.Series:
    p = pipe.predict_proba(row)[0]
    return pd.Series(p, index=[int(c) for c in pipe.classes_])


def default_inputs(df: pd.DataFrame) -> dict:
    """Most common category / median value of every model input in the training data."""
    vals = {}
    for c in M.NUM_FEATURES:
        if c in df:
            vals[c] = float(df[c].median())
    for c in M.BOOL_FEATURES:
        vals[c] = False
    for c in M.CAT_FEATURES + [M.CITY]:
        if c in df:
            vals[c] = df[c].mode().iloc[0]
    return vals
