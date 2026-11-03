"""Home page of the project dashboard (Abin Shaji Thomas). Run:  streamlit run app/Home.py"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import streamlit as st  # noqa: E402

import utils as U  # noqa: E402

U.setup("Smart Traffic Accident Analysis and Severity Prediction",
        f"{U.COURSE} · {U.INSTITUTE}")

prof = U.metric_json("dataset_profile.json")
log = U.metric_json("cleaning_log.json")
best = U.metric_json("best_model.json")
hot = U.metric_csv("hotspots.csv")
cross = U.metric_json("bigdata_crosscheck.json")

left, right = st.columns([3, 2])
with left:
    st.subheader("Objective")
    st.write("Find where and when US road accidents cluster, which weather, time and road conditions go with "
             "high traffic impact (Severity 3-4), and how well Severity 1-4 can be predicted from what is known "
             "when an accident is reported. Severity in this dataset measures delay on traffic, not injury.")
with right:
    st.subheader("Team")
    st.table({"Member": [n for n, _ in U.TEAM], "Register no.": [r for _, r in U.TEAM]})
    st.markdown(f"**Supervisor:** {U.SUPERVISOR}")

st.subheader("Headline numbers")
k = st.columns(5)
k[0].metric("Accident records", f"{prof['rows']:,}")
k[1].metric("Cleaned sample analysed", f"{log['rows_clean']:,}")
k[2].metric("Top hotspot cell", hot.iloc[0]["label"], f"{hot.iloc[0]['accidents']:,} accidents", delta_color="off", delta_arrow="off")
k[3].metric(f"Best model: {best['best_model']}", f"macro-F1 {best['test']['macro_f1']:.3f}",
            f"baseline {best['baseline_majority']['macro_f1']:.3f}", delta_color="off", delta_arrow="off")
k[4].metric("MapReduce = pandas = MongoDB", "PASS" if cross["all_pass"] else "FAIL",
            f"{cross['values_compared']} values compared", delta_color="off", delta_arrow="off")

st.subheader("The five modules")
mods = [("1 · Data Science Concepts", "Problem, data dictionary, chunked sampling, cleaning, missing GPS and weather handling, features.", "Dataset_and_Cleaning"),
        ("2 · Exploratory Data Analysis", "Weather influence, road infrastructure, hotspots, correlation, time patterns.", "EDA"),
        ("3 · Data Visualization", "Accident maps, density and hour x weekday heatmaps, time series, dashboard.", "Maps_and_Hotspots"),
        ("4 · Machine Learning", "Decision Tree, Random Forest, Logistic Regression, HistGradientBoosting; live predictor.", "Machine_Learning"),
        ("5 · Big Data Analytics", "MongoDB document store with geo index; Hadoop-style MapReduce data flow; cross-check.", "Big_Data")]
cols = st.columns(5)
for c, (t, d, page) in zip(cols, mods):
    with c.container(border=True):
        st.markdown(f"**{t}**")
        st.caption(d)

st.subheader("Data flow")
U.figure("data_flow.png")

st.subheader("Dataset")
st.markdown(f"**US Accidents (2016 - 2023)**, Moosavi et al. - [Kaggle: sobhanmoosavi/us-accidents](https://www.kaggle.com/datasets/sobhanmoosavi/us-accidents) · "
            f"licence **CC BY-NC-SA 4.0**, used for non-commercial academic purposes · file `{prof['file']}`, "
            f"{prof['rows']:,} rows x {prof['columns']} columns, {prof['start_time_min'][:10]} to {prof['start_time_max'][:10]}, "
            f"{prof['n_states']} states.")
st.markdown(f"Source code: [{U.GITHUB}]({U.GITHUB})")
