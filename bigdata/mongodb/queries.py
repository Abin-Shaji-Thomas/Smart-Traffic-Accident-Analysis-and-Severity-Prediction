"""MongoDB queries and aggregations on traffic_db.accidents, timed with and without indexes (Abin Shaji Thomas).

Run:  .venv\\Scripts\\python.exe bigdata\\mongodb\\queries.py
Writes reports/metrics/mongo_results.json. Requires load_to_mongo.py to have been run.
"""
from __future__ import annotations

import statistics
import sys
import time
from datetime import datetime
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from load_to_mongo import COLL, DB, create_indexes, get_client  # noqa: E402
from src.utils import METRICS, save_json  # noqa: E402

REPEAT = 5
SECONDARY = ["State_1", "Severity_1", "Start_Time_1"]


def geo_center():
    """Centre of the densest hotspot cell (reports/metrics/hotspots.csv, rank 1)."""
    h = pd.read_csv(METRICS / "hotspots.csv").iloc[0]
    return h["label"], float(h["center_lng"]), float(h["center_lat"])


def build_queries():
    label, lng, lat = geo_center()
    t0, t1 = datetime(2022, 1, 1), datetime(2022, 2, 1)
    return [
        {"name": "count_by_state", "desc": "Accidents per state ($group + $sort)", "type": "agg",
         "pipeline": [{"$group": {"_id": "$State", "accidents": {"$sum": 1}}}, {"$sort": {"accidents": -1}}]},
        {"name": "avg_severity_by_weather", "desc": "Average severity and count per weather group", "type": "agg",
         "pipeline": [{"$group": {"_id": "$WeatherGroup", "avg_severity": {"$avg": "$Severity"}, "accidents": {"$sum": 1}}},
                      {"$sort": {"avg_severity": -1}}]},
        {"name": "top_cities", "desc": "Top 10 cities ($group on City+State, $sort, $limit)", "type": "agg",
         "pipeline": [{"$group": {"_id": {"City": "$City", "State": "$State"}, "accidents": {"$sum": 1}}},
                      {"$sort": {"accidents": -1}}, {"$limit": 10}]},
        {"name": "hourly_distribution", "desc": "Accidents per hour of day", "type": "agg",
         "pipeline": [{"$group": {"_id": "$Hour", "accidents": {"$sum": 1}}}, {"$sort": {"_id": 1}}]},
        {"name": "severity_counts", "desc": "Accidents per severity level", "type": "agg",
         "pipeline": [{"$group": {"_id": "$Severity", "accidents": {"$sum": 1}}}, {"$sort": {"_id": 1}}]},
        {"name": "geo_near_hotspot", "desc": f"$geoNear: accidents within 10 km of the top hotspot ({label}), by severity",
         "type": "agg", "needs_index": "location_2dsphere",
         "pipeline": [{"$geoNear": {"near": {"type": "Point", "coordinates": [lng, lat]}, "distanceField": "dist_m",
                                    "maxDistance": 10_000, "spherical": True}},
                      {"$group": {"_id": "$Severity", "accidents": {"$sum": 1}, "avg_dist_km": {"$avg": {"$divide": ["$dist_m", 1000]}}}},
                      {"$sort": {"_id": 1}}]},
        {"name": "time_range_jan_2022", "desc": "Accidents with Start_Time in January 2022 (range filter)", "type": "count",
         "filter": {"Start_Time": {"$gte": t0, "$lt": t1}}},
        {"name": "ca_severity_4", "desc": "Severity-4 accidents in California (equality filter)", "type": "count",
         "filter": {"State": "CA", "Severity": 4}},
        {"name": "top_states_severe", "desc": "Top 5 states by severe (3-4) accidents ($match + $group + $sort + $limit)", "type": "agg",
         "pipeline": [{"$match": {"Severity": {"$gte": 3}}}, {"$group": {"_id": "$State", "severe": {"$sum": 1}}},
                      {"$sort": {"severe": -1}}, {"$limit": 5}]},
        {"name": "latest_ny", "desc": "5 most recent accidents in NY (find + sort + limit + projection)", "type": "find",
         "filter": {"State": "NY"}, "sort": [("Start_Time", -1)], "limit": 5,
         "projection": {"_id": 1, "City": 1, "Severity": 1, "Start_Time": 1}},
    ]


def run(coll, q):
    if q["type"] == "agg":
        return list(coll.aggregate(q["pipeline"], allowDiskUse=True))
    if q["type"] == "count":
        return coll.count_documents(q["filter"])
    return list(coll.find(q["filter"], q["projection"]).sort(q["sort"]).limit(q["limit"]))


def timed(coll, q):
    run(coll, q)  # warm-up
    times = []
    for _ in range(REPEAT):
        t = time.perf_counter(); res = run(coll, q); times.append(1000 * (time.perf_counter() - t))
    return res, round(statistics.median(times), 2)


def plan_stage(coll, q):
    """Winning plan stage of the query (IXSCAN = index used, COLLSCAN = full scan)."""
    if q["type"] == "agg":
        exp = coll.database.command("explain", {"aggregate": coll.name, "pipeline": q["pipeline"], "cursor": {}},
                                    verbosity="queryPlanner")
    else:
        exp = coll.database.command("explain", {"find": coll.name, "filter": q["filter"]}, verbosity="queryPlanner")
    text = str(exp)
    for stage in ("GEO_NEAR_2DSPHERE", "IXSCAN", "COUNT_SCAN", "COLLSCAN"):
        if stage in text:
            return stage
    return "OTHER"


def jsonable(x):
    if isinstance(x, list):
        return [jsonable(i) for i in x]
    if isinstance(x, dict):
        return {k: jsonable(v) for k, v in x.items()}
    if isinstance(x, datetime):
        return x.isoformat()
    if isinstance(x, float):
        return round(x, 6)
    return x


def main() -> dict:
    client = get_client()
    coll = client[DB][COLL]
    queries = build_queries()
    out = {"database": DB, "collection": COLL, "documents": coll.count_documents({}),
           "indexes": sorted(coll.index_information()), "repeat": REPEAT, "queries": []}
    with_idx = {}
    for q in queries:
        res, ms = timed(coll, q)
        with_idx[q["name"]] = (res, ms, plan_stage(coll, q))
    coll.drop_index("location_2dsphere")
    for name in SECONDARY:
        coll.drop_index(name)
    for q in queries:
        res, ms, stage = with_idx[q["name"]]
        row = {"name": q["name"], "description": q["desc"], "ms_with_index": ms, "plan_with_index": stage}
        if q.get("needs_index"):
            row["ms_without_index"] = None
            row["plan_without_index"] = f"not possible: $geoNear requires the {q['needs_index']} index"
        else:
            _, ms0 = timed(coll, q)
            row["ms_without_index"] = ms0
            row["plan_without_index"] = plan_stage(coll, q)
        row["result"] = jsonable(res if not isinstance(res, list) or len(res) <= 60 else res[:60])
        out["queries"].append(row)
        print(f"{q['name']:24s} with index {row['ms_with_index']:>9} ms ({stage:17s})  without {row['ms_without_index']} ms")
    create_indexes(coll)
    out["indexes_restored"] = sorted(coll.index_information())
    out["n_queries"] = len(out["queries"])
    save_json(out, METRICS / "mongo_results.json")
    return out


if __name__ == "__main__":
    main()
