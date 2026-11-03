"""Module 2 - exploratory data analysis with filters (Abin Shaji Thomas)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import pandas as pd  # noqa: E402
import plotly.express as px  # noqa: E402
import streamlit as st  # noqa: E402

import utils as U  # noqa: E402

U.setup("Exploratory Data Analysis", "Module 2 - weather influence, road infrastructure, correlation and time patterns (cleaned sample).")
df = U.clean_data(["Severity", "State", "Year", "WeatherGroup", "Hour", "DayOfWeek", "Month", "Start_Time"])

with st.sidebar:
    st.header("Filters")
    states = st.multiselect("State", sorted(df["State"].unique()))
    years = st.multiselect("Year", sorted(df["Year"].unique()))
    weather = st.multiselect("Weather group", [g for g in U.WEATHER_GROUPS if g in set(df["WeatherGroup"])])
    sev = st.multiselect("Severity", [1, 2, 3, 4])
f = df
for col, sel in (("State", states), ("Year", years), ("WeatherGroup", weather), ("Severity", sev)):
    if sel:
        f = f[f[col].isin(sel)]
if f.empty:
    st.info("No accidents match these filters.")
    st.stop()
f = f.assign(Sev=f["Severity"].astype(str), Severe=(f["Severity"] >= 3))
st.caption(f"{len(f):,} of {len(df):,} cleaned-sample accidents selected.")

c1, c2 = st.columns(2)
with c1:
    st.subheader("Severity distribution")
    st.caption("Share of accidents per severity level - note the strong imbalance towards Severity 2.")
    s = f["Sev"].value_counts().sort_index().rename_axis("Severity").reset_index(name="accidents")
    st.plotly_chart(px.bar(s, x="Severity", y="accidents", color="Severity", color_discrete_map=U.SEV_COLORS, height=340)
                    .update_xaxes(type="category"), width="stretch")
with c2:
    st.subheader("Accidents by hour of day")
    st.caption("Counts per hour, split by severity.")
    h = f.groupby(["Hour", "Sev"]).size().reset_index(name="accidents")
    st.plotly_chart(px.bar(h, x="Hour", y="accidents", color="Sev", color_discrete_map=U.SEV_COLORS, height=340,
                           labels={"Sev": "Severity"}), width="stretch")

c3, c4 = st.columns(2)
days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
with c3:
    st.subheader("Accidents by weekday")
    st.caption("Weekends have far fewer recorded accidents.")
    w = f.groupby("DayOfWeek").size().reindex(range(7), fill_value=0)
    st.plotly_chart(px.bar(x=days, y=w.values, labels={"x": "", "y": "accidents"}, height=320,
                           color_discrete_sequence=["#2a78d6"]), width="stretch")
with c4:
    st.subheader("Accidents by month")
    st.caption("Counts per calendar month (all years combined).")
    m = f.groupby("Month").size().reindex(range(1, 13), fill_value=0)
    st.plotly_chart(px.bar(x=m.index, y=m.values, labels={"x": "month", "y": "accidents"}, height=320,
                           color_discrete_sequence=["#2a78d6"]), width="stretch")

st.subheader("Monthly time series with 3-month rolling mean")
st.caption("Sample counts per month; the rolling mean smooths short-term noise.")
ts = f.set_index("Start_Time").resample("MS").size().rename("accidents").to_frame()
ts["3-month rolling mean"] = ts["accidents"].rolling(3, center=True).mean()
st.plotly_chart(px.line(ts, y=["accidents", "3-month rolling mean"], height=340,
                        color_discrete_sequence=["#c3c2b7", "#2a78d6"], labels={"value": "accidents per month", "Start_Time": "month"})
                .update_layout(legend_title=""), width="stretch")

st.subheader("Weather influence: share of severe (3-4) accidents by weather group")
st.caption("Bars follow the filters; the test result below is for the whole cleaned sample.")
ws = f.groupby("WeatherGroup")["Severe"].agg(["mean", "size"]).reset_index()
ws["severe_pct"] = 100 * ws["mean"]
st.plotly_chart(px.bar(ws, x="WeatherGroup", y="severe_pct", color="WeatherGroup", color_discrete_map=U.WEATHER_COLORS,
                       hover_data={"size": True}, labels={"severe_pct": "% severe", "WeatherGroup": ""}, height=340,
                       category_orders={"WeatherGroup": U.WEATHER_GROUPS}), width="stretch")
t = U.metric_json("weather_tests.json")["chi2_weathergroup_severity"]
ins = U.metric_json("eda_insights.json")
pval = "< 1e-300" if t["p_value"] == 0 else f"= {t['p_value']:.3g}"
st.info(f"Chi-square (weather group x severity): chi2 = {t['chi2']:,.0f}, dof = {t['dof']}, p {pval}, "
        f"Cramér's V = {t['cramers_v']:.3f} - significant but weak. {ins['weather'].split(' The link')[0]}")

st.subheader("Road infrastructure vs severity")
st.caption("Severe share when each road feature is present vs absent (whole cleaned sample).")
inf = U.metric_csv("infrastructure_severity.csv")
long = inf.melt(id_vars="feature", value_vars=["severe_pct_true", "severe_pct_false"], var_name="feature present", value_name="% severe")
long["feature present"] = long["feature present"].map({"severe_pct_true": "present", "severe_pct_false": "absent"})
st.plotly_chart(px.bar(long, y="feature", x="% severe", color="feature present", barmode="group", orientation="h", height=460,
                       color_discrete_map={"present": "#eb6834", "absent": "#c3c2b7"}), width="stretch")
st.caption(ins["infrastructure"])

st.subheader("Correlation heatmap (Spearman)")
st.caption("Rank correlation between numeric variables (whole cleaned sample); Year's link to Severity is a data-collection artefact.")
sp = U.metric_csv("correlation_spearman.csv", index_col=0)
st.plotly_chart(px.imshow(sp.round(2), text_auto=True, color_continuous_scale=["#1c5cab", "#f0efec", "#c2410c"], zmin=-1, zmax=1,
                          height=640, aspect="auto"), width="stretch")
