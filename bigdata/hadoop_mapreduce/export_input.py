"""Export the cleaned sample to the tab-separated MapReduce input file (Abin Shaji Thomas).

Writes bigdata/hadoop_mapreduce/input/accidents.tsv (untracked; regenerate with this script).
Columns: ID, State, WeatherGroup, Hour, Severity - the same cleaned rows used by pandas and MongoDB,
so the three engines can be compared exactly.
"""
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
src = ROOT / "data" / "processed" / "accidents_clean.parquet"
out = Path(__file__).resolve().parent / "input" / "accidents.tsv"
out.parent.mkdir(parents=True, exist_ok=True)
df = pd.read_parquet(src, columns=["ID", "State", "WeatherGroup", "Hour", "Severity"])
df.to_csv(out, sep="\t", index=False, lineterminator="\n")
print(f"Wrote {out.relative_to(ROOT)}: {len(df):,} rows")
