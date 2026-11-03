"""Module 2/3 - maps and hotspots (Abin Shaji Thomas)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import plotly.express as px  # noqa: E402
import streamlit as st  # noqa: E402

import utils as U  # noqa: E402

U.setup("Maps & Hotspots", "Where accidents concentrate - all records on a 0.1-degree grid, plus cluster results.")
grid = U.hotspot_grid()

state = st.selectbox("State", ["All states"] + sorted(grid["State"].dropna().unique()))
g = grid if state == "All states" else grid[grid["State"] == state]
cells = g.groupby(["cell_lat", "cell_lng"], as_index=False).agg(accidents=("n", "sum"), severe=("severe", "sum"))
cells["lat"], cells["lng"] = cells["cell_lat"] + 0.05, cells["cell_lng"] + 0.05
cells["severe %"] = (100 * cells["severe"] / cells["accidents"]).round(1)
cells["log10 accidents"] = np.log10(cells["accidents"])

st.subheader("Accident density map")
st.caption(f"{cells['accidents'].sum():,} accidents in {len(cells):,} grid cells (about 11 km); colour = log10 of accidents per cell. Zoom and hover for details.")
center = {"lat": float(cells["lat"].mean()), "lon": float(cells["lng"].mean())}
fig = px.scatter_map(cells, lat="lat", lon="lng", color="log10 accidents", size=None, hover_data={"accidents": ":,", "severe %": True,
                     "lat": False, "lng": False, "log10 accidents": False}, color_continuous_scale=["#cde2fb", "#3987e5", "#0d366b", "#eb6834"],
                     zoom=3 if state == "All states" else 5, center=center, height=560, map_style="carto-positron")
fig.update_traces(marker={"size": 5, "opacity": 0.8})
fig.update_layout(margin={"l": 0, "r": 0, "t": 0, "b": 0})
st.plotly_chart(fig, width="stretch")

a, b = st.columns([3, 2])
with a:
    st.subheader("Top 10 hotspot cells (all records)")
    st.caption("Densest 0.1-degree cells, labelled with their most frequent city.")
    st.dataframe(U.metric_csv("hotspots.csv"), width="stretch", hide_index=True)
with b:
    db = U.metric_json("dbscan_summary.json")
    st.subheader("DBSCAN dense clusters")
    st.caption(f"Haversine DBSCAN on a {db['subsample_rows']:,}-row subsample, eps {db['eps_km']} km, min_samples {db['min_samples']}.")
    m1, m2 = st.columns(2)
    m1.metric("Clusters found", db["n_clusters"])
    m2.metric("Points outside clusters", f"{db['noise_pct']}%")
    st.dataframe(pd.DataFrame(db["top_clusters"]), width="stretch", hide_index=True, height=240)

st.subheader("When do accidents happen? Hour x weekday")
st.caption("Cleaned-sample accidents per hour and weekday; darker = more accidents.")
hw = U.metric_csv("hour_weekday_counts.csv", index_col=0)
st.plotly_chart(px.imshow(hw, color_continuous_scale=["#f4f8fd", "#86b6ef", "#1c5cab", "#0d366b"], aspect="auto", height=360,
                          labels={"x": "hour", "y": "", "color": "accidents"}), width="stretch")
