"""Three-way cross-check: MapReduce output vs pandas vs MongoDB aggregation (Abin Shaji Thomas).

* pandas   - group-by on data/processed/accidents_clean.parquet
* MapReduce - bigdata/hadoop_mapreduce/output/<job>.tsv written by run_pipeline.py
* MongoDB  - aggregation results saved in reports/metrics/mongo_results.json by bigdata/mongodb/queries.py
Counts must be equal; averages must agree to 1e-6.
"""
from __future__ import annotations

import pandas as pd

from .utils import CLEAN_PARQUET, METRICS, ROOT, load_json, save_json

MR_OUT = ROOT / "bigdata" / "hadoop_mapreduce" / "output"
JOBS = {"state": ("accidents per state", "count_by_state"),
        "weather": ("average severity per weather group", "avg_severity_by_weather"),
        "hour": ("accidents per hour", "hourly_distribution")}


def _pandas(df: pd.DataFrame, job: str) -> pd.Series:
    if job == "state":
        return df.groupby("State").size().astype(float)
    if job == "weather":
        return df.groupby("WeatherGroup")["Severity"].mean()
    return df.groupby(df["Hour"].map(lambda h: f"{int(h):02d}")).size().astype(float)


def _mapreduce(job: str) -> pd.Series:
    t = pd.read_csv(MR_OUT / f"{job}.tsv", sep="\t", header=None, dtype={0: str})
    return pd.Series(t[3].values if job == "weather" else t[1].values, index=t[0].values, dtype=float)


def _mongo(results: dict, job: str) -> pd.Series:
    rows = next(q for q in results["queries"] if q["name"] == JOBS[job][1])["result"]
    if job == "weather":
        return pd.Series({r["_id"]: r["avg_severity"] for r in rows}, dtype=float)
    if job == "hour":
        return pd.Series({f"{int(r['_id']):02d}": r["accidents"] for r in rows}, dtype=float)
    return pd.Series({r["_id"]: r["accidents"] for r in rows}, dtype=float)


def crosscheck(save: bool = True) -> tuple[dict, pd.DataFrame]:
    df = pd.read_parquet(CLEAN_PARQUET, columns=["State", "WeatherGroup", "Hour", "Severity"])
    mongo = load_json(METRICS / "mongo_results.json")
    tables, summary = [], {}
    for job, (title, _) in JOBS.items():
        t = pd.DataFrame({"pandas": _pandas(df, job), "mapreduce": _mapreduce(job), "mongodb": _mongo(mongo, job)})
        tol = 1e-6 if job == "weather" else 0
        t["match"] = (t["pandas"].sub(t["mapreduce"]).abs() <= tol) & (t["pandas"].sub(t["mongodb"]).abs() <= tol)
        t = t.rename_axis("key").reset_index()
        t.insert(0, "job", title)
        tables.append(t)
        summary[job] = {"title": title, "keys_pandas": int(t["pandas"].notna().sum()),
                        "keys_mapreduce": int(t["mapreduce"].notna().sum()), "keys_mongodb": int(t["mongodb"].notna().sum()),
                        "mismatches": int((~t["match"]).sum()), "status": "PASS" if bool(t["match"].all()) else "FAIL"}
    detail = pd.concat(tables, ignore_index=True)
    out = {"jobs": summary, "all_pass": all(v["status"] == "PASS" for v in summary.values()),
           "values_compared": len(detail), "tolerance_avg": 1e-6,
           "details": detail.assign(pandas=detail["pandas"].round(6), mapreduce=detail["mapreduce"].round(6),
                                    mongodb=detail["mongodb"].round(6)).to_dict(orient="records")}
    if save:
        save_json(out, METRICS / "bigdata_crosscheck.json")
    return out, detail


if __name__ == "__main__":
    res, _ = crosscheck()
    for job, v in res["jobs"].items():
        print(f"{v['title']:36s} {v['status']}  (mismatches: {v['mismatches']})")
