"""Module 1 - dataset profile and cleaning (Abin Shaji Thomas)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import pandas as pd  # noqa: E402
import plotly.express as px  # noqa: E402
import streamlit as st  # noqa: E402

import utils as U  # noqa: E402

U.setup("Dataset & Cleaning", "Module 1 - how the 2.8 GB raw file becomes the cleaned analysis sample.")
prof = U.metric_json("dataset_profile.json")
stats = U.metric_json("dataset_stats.json")
log = U.metric_json("cleaning_log.json")
gps = U.metric_json("gps_missing.json")

st.subheader("Dataset profile (full raw file)")
c = st.columns(5)
c[0].metric("Rows", f"{prof['rows']:,}")
c[1].metric("Columns", prof["columns"])
c[2].metric("First record", prof["start_time_min"][:10])
c[3].metric("Last record", prof["start_time_max"][:10])
c[4].metric("States", prof["n_states"])
st.caption(f"Read in chunks of {stats['chunksize']:,} rows. A stratified sample of {stats['sample_rows']:,} rows "
           f"(fraction {stats['sample_fraction']:.4f}, same fraction per Severity level, random_state={stats['random_state']}) is used for analysis.")

st.subheader("Missing values before and after cleaning")
mv = U.metric_csv("missing_values_before_after.csv")
st.caption("Full-file % missing, and missing counts in the sample before and after cleaning (dropped columns have no 'after' value).")
fig = px.bar(mv.sort_values("full_file_pct_missing"), x="full_file_pct_missing", y="column", orientation="h",
             color="status_after_cleaning", labels={"full_file_pct_missing": "% missing in the full file", "column": ""},
             color_discrete_sequence=["#2a78d6", "#eb6834", "#898781"], height=520)
st.plotly_chart(fig, width="stretch")
st.dataframe(mv, width="stretch", hide_index=True)

a, b = st.columns(2)
with a:
    st.subheader("Duplicates and impossible values")
    d = log["duplicates"]
    st.metric("Rows before cleaning", f"{d['rows_before']:,}")
    st.metric("Duplicate rows removed", f"{d['duplicate_ids'] + d['duplicate_content']:,}",
              f"{d['duplicate_ids']} duplicate IDs, {d['duplicate_content']} duplicate contents", delta_color="off", delta_arrow="off")
    st.metric("Clean rows", f"{log['rows_clean']:,}")
    st.caption("Physically impossible weather values set to missing (then imputed):")
    st.dataframe(pd.Series(log["impossible_values_set_to_nan"], name="values").to_frame(), width="stretch")
with b:
    st.subheader("Missing GPS handling")
    st.metric("Start GPS missing / outside the US", f"{gps['before']['Start']['missing']:,} / {gps['before']['Start']['out_of_us_bounds']:,}")
    st.metric("Start GPS recovered (City+State median) / rows dropped",
              f"{gps['start_recovered_city_state_median']:,} / {gps['start_dropped_unrecoverable']:,}")
    st.metric("End GPS imputed from Start", f"{gps['end_imputed_from_start']:,}",
              f"{100 * gps['end_imputed_from_start'] / gps['rows_after']:.1f}% of rows", delta_color="off", delta_arrow="off")
    st.caption("Rule: out-of-bounds coordinates count as missing; missing Start GPS -> median of the same City + State, "
               "otherwise the row is dropped; missing End GPS -> copied from Start (accident treated as a point).")

st.subheader("Weather imputation")
st.caption("Numeric weather -> State + Month median; categorical -> State + Month mode; precipitation -> 0 only in dry weather groups (rule tested below).")
w1, w2 = st.columns(2)
w1.dataframe(U.metric_csv("weather_imputation.csv"), width="stretch", hide_index=True)
w2.dataframe(U.metric_csv("precipitation_rule_test.csv"), width="stretch", hide_index=True)

st.subheader("Columns dropped and why")
st.dataframe(pd.DataFrame(log["dropped_columns"].items(), columns=["column", "reason (computed in notebook 01)"]),
             width="stretch", hide_index=True)

st.subheader("Outlier handling (winsorizing at the 0.5th / 99.5th percentiles)")
st.dataframe(U.metric_csv("outliers_winsorize.csv"), width="stretch", hide_index=True)

st.subheader("Sample of the cleaned data")
st.dataframe(U.clean_data().head(200), width="stretch", height=320)
