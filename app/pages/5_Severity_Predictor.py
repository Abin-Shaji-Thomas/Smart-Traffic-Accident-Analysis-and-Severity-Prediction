"""Severity predictor using the saved best model (Abin Shaji Thomas)."""
import datetime as dt
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import pandas as pd  # noqa: E402
import plotly.express as px  # noqa: E402
import streamlit as st  # noqa: E402

import utils as U  # noqa: E402
from src import modeling as M  # noqa: E402

U.setup("Severity Predictor", "Enter what is known when an accident is reported; the saved model returns the probability of each severity level.")
best = U.metric_json("best_model.json")
pipe = U.model()
df = U.clean_data(M.feature_columns(with_distance=False) + ["Start_Time"])
d = U.default_inputs(df)

st.subheader("Location")
c = st.columns(4)
states = df["State"].value_counts().index.tolist()
state = c[0].selectbox("State", states, index=states.index(d["State"]))
cities = df.loc[df["State"] == state, "City"].value_counts().index.tolist()
city = c[1].selectbox("City (training cities of this state)", cities)
sub = df[(df["State"] == state) & (df["City"] == city)]
with st.form("predict"):
    c = st.columns(2)
    lat = c[0].number_input("Latitude", float(df["Start_Lat"].min()), float(df["Start_Lat"].max()), float(sub["Start_Lat"].median()), format="%.4f")
    lng = c[1].number_input("Longitude", float(df["Start_Lng"].min()), float(df["Start_Lng"].max()), float(sub["Start_Lng"].median()), format="%.4f")

    st.subheader("Time")
    c = st.columns(2)
    day = c[0].date_input("Date", dt.date(2022, 6, 15), min_value=df["Start_Time"].min().date(), max_value=df["Start_Time"].max().date())
    tim = c[1].time_input("Time", dt.time(17, 30))

    st.subheader("Weather")
    c = st.columns(4)
    groups = [g for g in U.WEATHER_GROUPS if g in set(df["WeatherGroup"])]
    wg = c[0].selectbox("Weather group", groups, index=groups.index(d["WeatherGroup"]))
    winds = df["Wind_Direction"].value_counts().index.tolist()
    wd = c[1].selectbox("Wind direction", winds, index=winds.index(d["Wind_Direction"]))
    num, nc = {}, st.columns(6)
    for i, col in enumerate(["Temperature(F)", "Humidity(%)", "Pressure(in)", "Visibility(mi)", "Wind_Speed(mph)", "Precipitation(in)"]):
        num[col] = nc[i].number_input(col, float(df[col].min()), float(df[col].max()), float(df[col].median()))

    st.subheader("Road features near the accident")
    flags = {}
    fc = st.columns(6)
    for i, col in enumerate(M.BOOL_FEATURES):
        flags[col] = fc[i % 6].checkbox(col.replace("_", " "), value=False)
    st.form_submit_button("Predict severity", type="primary")

values = {**d, "State": state, "City": city, "Start_Lat": lat, "Start_Lng": lng, "WeatherGroup": wg, "Wind_Direction": wd, **num, **flags}
row = U.build_row(values, pd.Timestamp.combine(day, tim))
proba = U.predict_proba(pipe, row)
pred = int(proba.idxmax())

a, b = st.columns([1, 2])
with a:
    st.metric("Predicted severity", pred)
    st.caption(f"Derived time features: hour {int(row['Hour'].iloc[0])}, weekday {int(row['DayOfWeek'].iloc[0])} (0 = Mon), "
               f"month {int(row['Month'].iloc[0])}, weekend {int(row['IsWeekend'].iloc[0])}, rush hour {int(row['IsRushHour'].iloc[0])}, "
               f"{row['DayNight'].iloc[0]}; road features present: {int(row['RoadFeatureCount'].iloc[0])}.")
with b:
    pdf = pd.DataFrame({"Severity": [str(k) for k in proba.index], "probability": proba.values})
    st.plotly_chart(px.bar(pdf, x="Severity", y="probability", color="Severity", color_discrete_map=U.SEV_COLORS,
                           range_y=[0, 1], height=320, text_auto=".2f").update_xaxes(type="category"), width="stretch")
st.caption(f"Model: {best['best_model']} (without Distance), test macro-F1 {best['test']['macro_f1']:.3f}, accuracy "
           f"{best['test']['accuracy']:.3f}. Balanced class weights make the model lean towards rare severities, so "
           "probabilities are a ranking aid, not calibrated risks.")
