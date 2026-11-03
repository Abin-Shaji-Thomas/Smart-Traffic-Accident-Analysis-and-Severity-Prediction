"""Module 5 - MongoDB and the Hadoop data flow (Abin Shaji Thomas)."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import pandas as pd  # noqa: E402
import plotly.express as px  # noqa: E402
import streamlit as st  # noqa: E402

import utils as U  # noqa: E402

U.setup("Big Data", "Module 5 - MongoDB document storage and a Hadoop-style MapReduce data flow, cross-checked against pandas.")
mr = U.metric_json("mongo_results.json")
cnt = U.metric_json("mapreduce_counters.json")
cross = U.metric_json("bigdata_crosscheck.json")

st.subheader("MongoDB - traffic_db.accidents")
c = st.columns(4)
c[0].metric("Documents", f"{mr['documents']:,}")
c[1].metric("Indexes", len(mr["indexes"]))
c[2].metric("Queries timed", mr["n_queries"])
c[3].metric("Load time (s)", mr["load"]["load_seconds"])
a, b = st.columns([2, 3])
with a:
    st.caption("Example document (one accident, GeoJSON location):")
    st.json(mr["example_document"], expanded=False)
    st.caption("Indexes")
    st.dataframe(pd.DataFrame([{"index": k, "keys": json.dumps(v)} for k, v in mr["index_keys"].items()]), width="stretch", hide_index=True)
with b:
    st.caption(f"Query time, median of {mr['repeat']} runs, with vs without indexes (log scale). $geoNear needs the 2dsphere index.")
    q = pd.DataFrame(mr["queries"])
    long = q.melt(id_vars="name", value_vars=["ms_with_index", "ms_without_index"], var_name="run", value_name="ms").dropna()
    long["run"] = long["run"].map({"ms_with_index": "with index", "ms_without_index": "without index"})
    st.plotly_chart(px.bar(long, x="name", y="ms", color="run", barmode="group", log_y=True, height=420,
                           color_discrete_map={"with index": "#2a78d6", "without index": "#eb6834"}, labels={"name": ""}),
                    width="stretch")
st.dataframe(q[["name", "description", "ms_with_index", "plan_with_index", "ms_without_index", "plan_without_index"]],
             width="stretch", hide_index=True)

if st.button("Run live MongoDB query (accidents per state, top 5)"):
    try:
        import os
        from dotenv import load_dotenv
        from pymongo import MongoClient
        load_dotenv(U.ROOT / ".env")
        cl = MongoClient(os.getenv("MONGO_URI", "mongodb://localhost:27017"), serverSelectionTimeoutMS=2000)
        res = list(cl["traffic_db"]["accidents"].aggregate([{"$group": {"_id": "$State", "accidents": {"$sum": 1}}},
                                                           {"$sort": {"accidents": -1}}, {"$limit": 5}]))
        st.success("Live result from the MongoDB server:")
        st.dataframe(pd.DataFrame(res).rename(columns={"_id": "State"}), hide_index=True)
    except Exception:
        st.warning("MongoDB is not reachable. Start it with `net start MongoDB` (or run "
                   "`bigdata\\mongodb\\load_to_mongo.py` first). The saved results above do not need the server.")

st.subheader("Hadoop data flow (MapReduce)")
st.caption("4 input splits -> 4 map tasks -> partition crc32(key) % 2 -> sort -> 2 reduce tasks -> output; the real Hadoop cluster setup is documented but was not executed.")
U.figure("hadoop_data_flow.png")
rows = []
for job, v in cnt["jobs"].items():
    rows.append({"job": job, "splits": v["splits"], "map input records": v["map_input_records"], "map output records": v["map_output_records"],
                 "partitions": v["partitions"], "records per partition": str(v["partition_records"]),
                 "reduce input groups": v["reduce_input_groups"], "reduce output records": v["reduce_output_records"], "seconds": v["seconds"]})
st.dataframe(pd.DataFrame(rows), width="stretch", hide_index=True)

st.subheader("Three-way cross-check: MapReduce vs pandas vs MongoDB")
st.caption(f"{cross['values_compared']} values compared; counts must be equal and averages agree to {cross['tolerance_avg']}.")
st.dataframe(pd.DataFrame(cross["jobs"]).T.reset_index(names="job"), width="stretch", hide_index=True)
with st.expander("All compared values"):
    st.dataframe(pd.DataFrame(cross["details"]), width="stretch", hide_index=True)
