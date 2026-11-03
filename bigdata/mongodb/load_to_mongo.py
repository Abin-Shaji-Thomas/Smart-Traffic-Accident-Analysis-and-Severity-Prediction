"""Load the cleaned accident sample into MongoDB (Abin Shaji Thomas).

Target: database `traffic_db`, collection `accidents`.
* one document per accident, `_id` = dataset ID
* GeoJSON `location` {type: "Point", coordinates: [lng, lat]} with a 2dsphere index
* secondary indexes on State, Severity and Start_Time
* insert_many in batches of 10,000

Connection: MONGO_URI from a `.env` file at the repository root (never committed), default
mongodb://localhost:27017.
Run:  .venv\\Scripts\\python.exe bigdata\\mongodb\\load_to_mongo.py
"""
from __future__ import annotations

import os
import sys
import time
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv
from pymongo import ASCENDING, GEOSPHERE, MongoClient

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from src.utils import CLEAN_PARQUET, safe_name  # noqa: E402

BATCH = 10_000
DB, COLL = "traffic_db", "accidents"
KEEP = ["ID", "Source", "Severity", "Start_Time", "End_Time", "Start_Lat", "Start_Lng", "Distance(mi)", "City",
        "State", "Temperature(F)", "Humidity(%)", "Pressure(in)", "Visibility(mi)", "Wind_Direction",
        "Wind_Speed(mph)", "Precipitation(in)", "Weather_Condition", "WeatherGroup", "Hour", "DayOfWeek", "Month",
        "Year", "IsWeekend", "IsRushHour", "DayNight", "RoadFeatureCount", "Duration_min",
        "Junction", "Traffic_Signal", "Crossing", "Stop", "Railway", "Station"]


def get_client() -> MongoClient:
    load_dotenv(ROOT / ".env")
    uri = os.getenv("MONGO_URI", "mongodb://localhost:27017")
    client = MongoClient(uri, serverSelectionTimeoutMS=5000)
    client.admin.command("ping")
    return client


def to_documents(df: pd.DataFrame) -> list[dict]:
    d = df[KEEP].copy()
    d.columns = [safe_name(c) for c in d.columns]
    d = d.rename(columns={"ID": "_id"})
    d["location"] = [{"type": "Point", "coordinates": [float(lng), float(lat)]}
                     for lat, lng in zip(d["Start_Lat"], d["Start_Lng"])]
    d["Start_Time"] = d["Start_Time"].dt.to_pydatetime()
    d["End_Time"] = d["End_Time"].dt.to_pydatetime()
    records = d.to_dict(orient="records")
    for r in records:  # NaN -> missing field (document model: absent instead of null)
        for k in [k for k, v in r.items() if isinstance(v, float) and v != v]:
            del r[k]
    return records


def create_indexes(coll) -> list[str]:
    return [coll.create_index([("location", GEOSPHERE)], name="location_2dsphere"),
            coll.create_index([("State", ASCENDING)], name="State_1"),
            coll.create_index([("Severity", ASCENDING)], name="Severity_1"),
            coll.create_index([("Start_Time", ASCENDING)], name="Start_Time_1")]


def main() -> dict:
    client = get_client()
    coll = client[DB][COLL]
    coll.drop()
    df = pd.read_parquet(CLEAN_PARQUET)
    docs = to_documents(df)
    t0 = time.time()
    for i in range(0, len(docs), BATCH):
        coll.insert_many(docs[i:i + BATCH], ordered=False)
    load_s = time.time() - t0
    idx = create_indexes(coll)
    stats = client[DB].command("collstats", COLL)
    info = {"database": DB, "collection": COLL, "documents": coll.count_documents({}), "batch_size": BATCH,
            "batches": (len(docs) + BATCH - 1) // BATCH, "load_seconds": round(load_s, 1), "indexes": idx,
            "storage_size_mb": round(stats["storageSize"] / 1e6, 1), "avg_doc_bytes": int(stats["avgObjSize"]),
            "server_version": client.server_info()["version"]}
    print(info)
    return info


if __name__ == "__main__":
    main()
