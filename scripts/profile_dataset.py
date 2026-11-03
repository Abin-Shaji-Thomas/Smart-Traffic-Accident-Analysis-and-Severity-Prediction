r"""Profile the raw CSV in chunks: rows, columns, Start_Time range, number of states (Abin Shaji Thomas).

Writes reports/metrics/dataset_profile.json - the single source for the dataset date range.
Run:  .venv\Scripts\python.exe scripts\profile_dataset.py
"""
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.utils import DATA_RAW, METRICS, save_json  # noqa: E402

columns = list(pd.read_csv(DATA_RAW, nrows=0).columns)
rows, tmin, tmax, states = 0, None, None, set()
for chunk in pd.read_csv(DATA_RAW, usecols=["Start_Time", "State"], chunksize=500_000):
    rows += len(chunk)
    t = pd.to_datetime(chunk["Start_Time"], format="mixed", errors="coerce")
    tmin = t.min() if tmin is None else min(tmin, t.min())
    tmax = t.max() if tmax is None else max(tmax, t.max())
    states.update(chunk["State"].dropna().unique())
profile = {"file": DATA_RAW.name, "size_gb": round(DATA_RAW.stat().st_size / 1e9, 2), "rows": rows,
           "columns": len(columns), "start_time_min": str(tmin), "start_time_max": str(tmax),
           "n_states": len(states), "states": sorted(states)}
save_json(profile, METRICS / "dataset_profile.json")
print({k: v for k, v in profile.items() if k != "states"})
