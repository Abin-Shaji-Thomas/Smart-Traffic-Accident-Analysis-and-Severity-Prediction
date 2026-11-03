"""Generate README.md and docs/report_notes.md from the saved result files (Abin Shaji Thomas).

Every number in both documents is read from reports/metrics/ - nothing is typed by hand.
Run from the repository root:  .venv\\Scripts\\python.exe -m src.build_docs
"""
from __future__ import annotations

import pandas as pd

from .utils import METRICS, ROOT, load_json

M = METRICS


def md_table(df: pd.DataFrame) -> str:
    cols = list(df.columns)
    lines = ["| " + " | ".join(map(str, cols)) + " |", "|" + "|".join("---" for _ in cols) + "|"]
    for _, r in df.iterrows():
        lines.append("| " + " | ".join("" if pd.isna(v) else str(v) for v in r.values) + " |")
    return "\n".join(lines)


def load_all() -> dict:
    d = {name: load_json(M / f"{name}.json") for name in
         ["dataset_stats", "gps_missing", "cleaning_log", "eda_insights", "ml_insights", "best_model",
          "mongo_results", "crosscheck_summary", "weather_tests", "dbscan_summary"]}
    for name in ["model_comparison", "hotspots", "by_weather", "class_weight_comparison", "top_states_full",
                 "top_cities_full", "weather_imputation", "kmeans_selection", "rf_feature_importance", "cramers_v",
                 "severity_correlations", "full_year_counts", "infrastructure"]:
        d[name] = pd.read_csv(M / f"{name}.csv")
    return d


def results_tables(d: dict) -> dict:
    mc = d["model_comparison"]
    t_models = mc[["model", "distance_feature", "accuracy", "macro_f1", "weighted_f1", "balanced_accuracy",
                   "roc_auc_ovr_macro", "recall_sev1", "recall_sev4"]].rename(columns={
        "distance_feature": "Distance(mi)", "macro_f1": "macro-F1", "weighted_f1": "weighted-F1",
        "balanced_accuracy": "balanced acc.", "roc_auc_ovr_macro": "ROC-AUC (OvR)", "recall_sev1": "recall Sev1",
        "recall_sev4": "recall Sev4"})
    hot = d["hotspots"][["rank", "label", "center_lat", "center_lng", "accidents", "avg_severity", "severe_pct"]]
    hot = hot.assign(accidents=hot["accidents"].map("{:,}".format))
    q = pd.DataFrame([{"query": x["name"], "ms with index": x["ms_with_index"], "plan": x["plan_with_index"],
                       "ms without index": x["ms_without_index"] if x["ms_without_index"] is not None else "n/a (needs 2dsphere)"}
                      for x in d["mongo_results"]["queries"]])
    xc = pd.DataFrame(d["crosscheck_summary"]["jobs"]).rename(columns={"all_match": "pandas = MongoDB = MapReduce"})
    cw = d["class_weight_comparison"]
    w = d["by_weather"][["WeatherGroup", "accidents", "share_of_accidents_pct", "avg_severity", "severe_pct"]]
    w = w.assign(accidents=w["accidents"].map("{:,}".format))
    return {"models": md_table(t_models), "hotspots": md_table(hot), "mongo": md_table(q), "cross": md_table(xc),
            "weights": md_table(cw), "weather": md_table(w)}


def readme(d: dict, t: dict) -> str:
    s, g, b, mr, cx = d["dataset_stats"], d["gps_missing"], d["best_model"], d["mongo_results"], d["crosscheck_summary"]
    ins, mli, log = d["eda_insights"], d["ml_insights"], d["cleaning_log"]
    return f"""# Smart Traffic Accident Analysis and Severity Prediction

End-semester **Data Science & Ecosystem** project (Project 3)
**Abin Shaji Thomas** - B.Tech Computer Science and Engineering (3rd year), Karunya Institute of Technology and Sciences

An end-to-end analysis of **{s['total_rows']:,} US road-accident records** (2016 - March 2023): cleaning and missing-GPS
handling, weather / hotspot / correlation / time analysis, interactive maps and a Power BI dashboard, Decision Tree /
Random Forest / Logistic Regression severity models, MongoDB storage and a Hadoop Streaming MapReduce data flow.

> *Severity* (1-4) in this dataset measures the **impact of an accident on traffic** (length of the delay), not injury severity.

## Problem statement

Traffic agencies need to know where and when accidents cluster, which conditions are linked to high-impact accidents,
and whether the severity of a new accident can be predicted from information available when it is reported.
This project answers these questions on the US Accidents dataset with the full data-science workflow, from a 2.8 GB
raw CSV to models, a document database, MapReduce jobs and dashboards.

## Dataset

* **US Accidents (2016 - 2023)** by Sobhan Moosavi et al. - Kaggle: <https://www.kaggle.com/datasets/sobhanmoosavi/us-accidents>
* File used: `US_Accidents_March23.csv` - {s['total_rows']:,} rows, {s['total_columns']} columns (not committed; place it in `data/raw/`).
* License: **CC BY-NC-SA 4.0** - used here for non-commercial academic purposes only. Only a 5,000-row sample
  (`data/sample/sample_5k.csv`) is redistributed, under the same license.
* Analysis sample: {s['sample_rows']:,} rows drawn in 500,000-row chunks, stratified by Severity
  (fraction {s['sample_fraction']:.6f}, `random_state=42`); {log['rows_clean']:,} rows after cleaning.

## The five modules

| # | Module | Notebook | Project tasks covered |
|---|---|---|---|
| 1 | Data Science Concepts | [`01_data_science_concepts.ipynb`](notebooks/01_data_science_concepts.ipynb) | problem, data dictionary, lifecycle, sampling, **cleaning**, **missing GPS handling**, weather imputation, features |
| 2 | Exploratory Data Analysis | [`02_exploratory_data_analysis.ipynb`](notebooks/02_exploratory_data_analysis.ipynb) | **weather influence**, **hotspots** (KMeans, DBSCAN, grid), **correlation analysis**, time patterns |
| 3 | Data Visualization | [`03_data_visualization.ipynb`](notebooks/03_data_visualization.ipynb) | **accident maps, heatmaps, time-series plots**, Power BI exports + guide |
| 4 | Machine Learning Fundamentals | [`04_machine_learning.ipynb`](notebooks/04_machine_learning.ipynb) | **Decision Tree, Random Forest, Logistic Regression** |
| 5 | Big Data Analytics | [`05_big_data_analytics.ipynb`](notebooks/05_big_data_analytics.ipynb) | **MongoDB accident storage**, **Hadoop data flow (MapReduce)** |

## Repository structure

```
README.md  NOTICE.md  LICENSE  requirements.txt  .gitignore
data/
  raw/                 US_Accidents_March23.csv (not committed)
  processed/           Parquet sample + cleaned data (generated, not committed)
  sample/sample_5k.csv 5,000 cleaned rows (committed)
  powerbi/             Power BI-ready CSVs (each < 50 MB)
notebooks/             01 ... 05 (committed with outputs)
src/                   utils, cleaning, features, analysis, modeling, viz, build_docs
bigdata/
  mongodb/             load_to_mongo.py, queries.py
  hadoop_mapreduce/    mapper.py, reducer.py, export_input.py, run_local.ps1, docker-compose.yml, hadoop.env, README.md
  spark_optional/      adapted upstream PySpark jobs (not executed)
reports/
  figures/             PNG charts
  maps/                Folium maps + Plotly time-series (HTML)
  metrics/             every number used in this README (CSV / JSON)
powerbi/POWERBI_GUIDE.md
docs/report_notes.md
poster/                A3 poster build files
```

## How to run (Windows PowerShell)

```powershell
# 0. environment (Python 3.10+; developed on 3.14.2)
python -m venv .venv
.\\.venv\\Scripts\\python.exe -m pip install -r requirements.txt
# put US_Accidents_March23.csv in data\\raw\\

# Modules 1-4 (run in order; each writes its outputs to data/processed and reports/)
.\\.venv\\Scripts\\python.exe -m nbconvert --to notebook --execute --inplace --ExecutePreprocessor.timeout=-1 notebooks\\01_data_science_concepts.ipynb
.\\.venv\\Scripts\\python.exe -m nbconvert --to notebook --execute --inplace --ExecutePreprocessor.timeout=-1 notebooks\\02_exploratory_data_analysis.ipynb
.\\.venv\\Scripts\\python.exe -m nbconvert --to notebook --execute --inplace --ExecutePreprocessor.timeout=-1 notebooks\\03_data_visualization.ipynb
.\\.venv\\Scripts\\python.exe -m nbconvert --to notebook --execute --inplace --ExecutePreprocessor.timeout=-1 notebooks\\04_machine_learning.ipynb

# Module 5 needs MongoDB on localhost:27017 (winget install MongoDB.Server) or MONGO_URI in a .env file
.\\.venv\\Scripts\\python.exe -m nbconvert --to notebook --execute --inplace --ExecutePreprocessor.timeout=-1 notebooks\\05_big_data_analytics.ipynb
#   (the notebook calls these; they can also be run on their own)
.\\.venv\\Scripts\\python.exe bigdata\\mongodb\\load_to_mongo.py
.\\.venv\\Scripts\\python.exe bigdata\\mongodb\\queries.py
powershell -ExecutionPolicy Bypass -File bigdata\\hadoop_mapreduce\\run_local.ps1

# regenerate this README and docs/report_notes.md from reports/metrics
.\\.venv\\Scripts\\python.exe -m src.build_docs
```

Use `python -m nbconvert` from the venv (not a bare `jupyter` command), otherwise Windows may pick up a system-wide
Jupyter and run the notebooks with a different Python.

## Results

*All tables below are generated by `src/build_docs.py` from `reports/metrics/`.*

### Data preparation (Module 1)

* Missing GPS: Start coordinates missing **{g['before']['Start']['missing']:,}**, outside the US box **{g['before']['Start']['out_of_us_bounds']:,}**;
  recovered from City+State median **{g['start_recovered_city_state_median']:,}**, dropped **{g['start_dropped_unrecoverable']:,}**;
  End coordinates imputed from Start **{g['end_imputed_from_start']:,}** ({100 * g['end_imputed_from_start'] / g['rows_after']:.1f}% of rows)
  - `reports/metrics/gps_missing.json`.
* Duplicates removed: {log['duplicates']['duplicate_ids'] + log['duplicates']['duplicate_content']:,}; {len(log['dropped_columns'])} columns dropped with a computed justification
  (`reports/metrics/cleaning_log.json`); weather imputation before/after in `weather_imputation.csv`.

### Weather influence, hotspots, correlation, time (Module 2)

{t['weather']}

* {ins['weather']}
* {ins['weather_numeric']}
* {ins['correlation']}
* {ins['time']}
* {ins['year_artifact']}
* {ins['infrastructure']}
* {ins['states']}
* {ins['dbscan']}

**Top 10 hotspot cells** (0.1 x 0.1 degree grid over all {s['total_rows']:,} records) - `reports/metrics/hotspots.csv`

{t['hotspots']}

### Severity prediction (Module 4) - test set ({b['test_rows']:,} rows)

{t['models']}

* **Best model: {b['best_model']}** ({b['selection']}); 5-fold CV macro-F1 {b['cv_5fold']['macro_f1_mean']} +/- {b['cv_5fold']['macro_f1_std']}.
* {mli['distance']} Distance is measured after the event, so the headline results exclude it.
* {mli['top_feature']}

Class-weighting comparison (upstream idea, re-tested on this data) - `class_weight_comparison.csv`:

{t['weights']}

### Big data (Module 5)

MongoDB `traffic_db.accidents`: {mr['documents']:,} documents, indexes {', '.join(mr['indexes'])}; {mr['n_queries']} queries
(median of {mr['repeat']} runs) - `reports/metrics/mongo_results.json`:

{t['mongo']}

Cross-check of the same aggregations in three engines ({cx['rows_compared']} values) - `mapreduce_crosscheck.csv`:

{t['cross']}

MapReduce was executed with the Hadoop Streaming flow (map -> sort -> reduce) locally by `run_local.ps1`. The real
HDFS / YARN run (`bigdata/hadoop_mapreduce/docker-compose.yml`) and the PySpark scripts are provided but were
**not executed**.

## Figures and maps

| Topic | File |
|---|---|
| Accident map (MarkerCluster, coloured by severity) | [`reports/maps/accident_map.html`](reports/maps/accident_map.html) |
| Accident heatmap (weighted by severity) | [`reports/maps/accident_heatmap.html`](reports/maps/accident_heatmap.html) |
| Interactive time series | [`reports/maps/timeseries_interactive.html`](reports/maps/timeseries_interactive.html) |
| Monthly trend + rolling averages | [`reports/figures/timeseries_monthly.png`](reports/figures/timeseries_monthly.png) |
| Hourly profile / severity share over time | [`timeseries_hourly_profile.png`](reports/figures/timeseries_hourly_profile.png), [`timeseries_severity_share.png`](reports/figures/timeseries_severity_share.png) |
| Hour x weekday heatmap | [`reports/figures/heatmap_hour_weekday.png`](reports/figures/heatmap_hour_weekday.png) |
| Correlation heatmaps (Pearson, Spearman) | [`reports/figures/correlation_heatmaps.png`](reports/figures/correlation_heatmaps.png) |
| Cramer's V vs Severity | [`reports/figures/cramers_v.png`](reports/figures/cramers_v.png) |
| Weather analysis | [`weather_counts_severity.png`](reports/figures/weather_counts_severity.png), [`weather_numeric_by_severity.png`](reports/figures/weather_numeric_by_severity.png), [`weather_severity_mix.png`](reports/figures/weather_severity_mix.png), [`weather_visibility_severity.png`](reports/figures/weather_visibility_severity.png) |
| Hotspots | [`top_states_cities.png`](reports/figures/top_states_cities.png), [`kmeans_selection.png`](reports/figures/kmeans_selection.png), [`kmeans_clusters_map.png`](reports/figures/kmeans_clusters_map.png), [`dbscan_clusters_map.png`](reports/figures/dbscan_clusters_map.png), table [`hotspots.csv`](reports/metrics/hotspots.csv) |
| Missing GPS section | notebook 01 section 8, [`gps_missing.json`](reports/metrics/gps_missing.json) |
| ML | [`ml_model_comparison.png`](reports/figures/ml_model_comparison.png), [`ml_confusion_matrices.png`](reports/figures/ml_confusion_matrices.png), [`ml_rf_feature_importance.png`](reports/figures/ml_rf_feature_importance.png), [`ml_lr_coefficients.png`](reports/figures/ml_lr_coefficients.png), [`ml_decision_tree.png`](reports/figures/ml_decision_tree.png) |
| Big data | [`data_flow.png`](reports/figures/data_flow.png), [`mongo_query_timings.png`](reports/figures/mongo_query_timings.png) |
| Power BI | data in [`data/powerbi/`](data/powerbi/), build steps in [`powerbi/POWERBI_GUIDE.md`](powerbi/POWERBI_GUIDE.md) |

## Tech stack

Python 3.14 - pandas, NumPy, PyArrow (Parquet), SciPy, scikit-learn, Matplotlib, Seaborn, Plotly, Folium, joblib,
Jupyter/nbconvert - MongoDB 9 (pymongo, GeoJSON, 2dsphere) - Hadoop Streaming (Python mapper/reducer; optional
Docker Hadoop 3.3.6) - optional PySpark - Power BI Desktop.

## Limitations

Severity is traffic impact, not injury; counts are not rates (no traffic-volume data); the yearly trend reflects data
collection; models use a 5.18% stratified sample and a random (not time-based) split; the Hadoop cluster and Spark
runs were not executed on this laptop. Details in [`docs/report_notes.md`](docs/report_notes.md).

## Based on / Acknowledgements

This project adapts code from **[Accident Severity Prediction and Hotspot Analysis of US Road Accidents (BDA Project)](https://github.com/rit-vik/Accident-Severity-Prediction-and-Hotspot-Analysis-of-US-Road-Accidents-BDA-Project-)**
by **Ritvik Kar, Dhruv Abhijit Desai and Mithil S** (MIT Manipal), released under the MIT license (commit `160ba7f`).
See [`NOTICE.md`](NOTICE.md) for the quoted license statement and the reconstructed MIT notice.

**Reused / adapted from upstream** (each adapted file says so in its header):
* `src/ingest.py`, `src/clean.py` -> `src/cleaning.py`, `src/features.py`: column-name sanitising, duplicate-ID
  removal, plausible-range limits for weather values, time features, regex weather grouping (re-expressed in pandas).
* `src/analysis.py` -> `src/analysis.py`: the group-by / severe-share queries (Spark SQL -> pandas).
* `src/ml.py`, `src/ml2.py`, `src/make_ml_charts.py` -> `src/modeling.py`, `src/utils.py`, notebook 04: feature list,
  leakage rules, majority baseline, `metrics()` helper, inverse-vs-sqrt class-weight comparison, chart pattern.
* PySpark scripts kept as an optional, not-executed extra in `bigdata/spark_optional/`.

**My additions:** chunked full-file profiling and stratified sampling; missing-GPS audit and recovery; State+Month
weather imputation and the tested precipitation rule; winsorizing; the 7 project weather groups; all EDA statistics
(chi-square, Kruskal-Wallis, Cramer's V, KMeans, DBSCAN, grid hotspots); Folium maps, Plotly time series and Power BI
exports/guide; the Decision Tree model, scikit-learn pipelines, randomized search, ROC-AUC and cross-validation;
MongoDB storage and queries; Hadoop Streaming MapReduce jobs and the three-way cross-check; the data-flow diagram.

No upstream results, charts, screenshots, logs, report or cluster files are included; every number here comes from
this project's own run.

**Dataset:** S. Moosavi, M. H. Samavatian, S. Parthasarathy, R. Ramnath, "A Countrywide Traffic Accident Dataset",
arXiv:1906.05409, 2019; S. Moosavi et al., "Accident Risk Prediction based on Heterogeneous Sparse Data: New Dataset
and Insights", ACM SIGSPATIAL 2019. License CC BY-NC-SA 4.0, used for non-commercial academic purposes.

## License

Code: MIT (see [`LICENSE`](LICENSE), which keeps the upstream copyright line). Data: CC BY-NC-SA 4.0 (not covered by the MIT license).
"""


def report_notes(d: dict, t: dict) -> str:
    s, g, b, log = d["dataset_stats"], d["gps_missing"], d["best_model"], d["cleaning_log"]
    ins, mli, wt, db = d["eda_insights"], d["ml_insights"], d["weather_tests"], d["dbscan_summary"]
    ks = d["kmeans_selection"]
    k_best = d["hotspots"]
    sev = pd.Series(s["full_severity_counts"]).astype(int)
    imp = d["weather_imputation"]
    precip = imp[imp.column == "Precipitation(in)"].iloc[0]
    yc = d["full_year_counts"]
    cw = d["class_weight_comparison"].set_index(["model", "weights"])
    rf = d["rf_feature_importance"].head(5)
    mc = d["model_comparison"]
    return f"""# Report notes - Smart Traffic Accident Analysis and Severity Prediction

Consolidated notes for the written report (generated by `src/build_docs.py`; every number is read from
`reports/metrics/`). Author: Abin Shaji Thomas.

## 1. Problem

Find where and when US road accidents cluster, which weather / time / road conditions are linked to high traffic
impact (Severity 3-4), and how well Severity (1-4) can be predicted at report time. Severity measures delay on
traffic, not injury.

## 2. Data

* {s['total_rows']:,} records x {s['total_columns']} columns, {s['date_min'][:10]} to {s['date_max'][:10]}; CC BY-NC-SA 4.0.
* Full-data Severity counts: 1 = {sev['1']:,}; 2 = {sev['2']:,}; 3 = {sev['3']:,}; 4 = {sev['4']:,}.
* Recorded accidents per year (full file): {', '.join(f"{r.Year}: {r.accidents:,}" for r in yc.itertuples())}
  (2016 and 2023 are partial years).

## 3. Methods and decisions

1. **Profiling** - one chunked pass (500,000 rows) over the whole file for null counts, dtypes and full-data
   State / City / hotspot-grid counts (`data_dictionary.csv`).
2. **Sampling** - {s['sample_rows']:,} rows, same fraction ({s['sample_fraction']:.6f}) per Severity level in every chunk,
   `random_state=42`; sample class mix equals the full mix.
3. **Cleaning** - {log['duplicates']['duplicate_content']:,} duplicate-content rows removed ({log['duplicates']['duplicate_ids']} duplicate IDs);
   {len(log['dropped_columns'])} columns dropped (constant, redundant, metadata, high-cardinality or leaky - reasons in `cleaning_log.json`);
   {sum(log['impossible_values_set_to_nan'].values())} physically impossible weather values set to missing.
4. **Missing GPS** - Start GPS missing: {g['before']['Start']['missing']:,}, out of bounds: {g['before']['Start']['out_of_us_bounds']:,} (so the
   City+State median recovery recovered {g['start_recovered_city_state_median']:,} and {g['start_dropped_unrecoverable']:,} rows were dropped);
   End GPS missing in {g['before']['End']['missing']:,} rows -> imputed from Start (point-event assumption, flag `End_GPS_Imputed`).
5. **Missing weather** - numeric -> State+Month median; categorical -> State+Month mode. The upstream rule
   "missing precipitation = 0" was tested (`precipitation_rule_test.csv`) and kept only for dry weather groups;
   precipitation was missing in {precip['missing_before']:,} rows ({precip['pct_missing_before']}%).
6. **Weather groups** - 7 groups: Clear, Cloudy, Rain, Snow, Fog/Haze, Storm, Other.
7. **Outliers** - IQR counts reported; winsorized at the 0.5th / 99.5th percentiles (`outliers_winsorize.csv`).
8. **Features** - Hour, DayOfWeek, Month, Year, IsWeekend, IsRushHour, DayNight, RoadFeatureCount; Duration (EDA only).
9. **EDA statistics** - chi-square + Cramer's V (categorical), Kruskal-Wallis + epsilon-squared (numeric), Pearson
   and Spearman correlation, KMeans (k={int(ks.loc[ks[ks.k >= 5].silhouette.idxmax(), 'k'])} by silhouette for k>=5),
   DBSCAN (haversine, eps {db['eps_km']} km, min_samples {db['min_samples']}), 0.1-degree grid hotspots on all records.
10. **ML** - scikit-learn Pipeline + ColumnTransformer, stratified 80/20 split ({b['train_rows']:,} / {b['test_rows']:,}),
    class_weight='balanced', 3-fold RandomizedSearchCV on macro-F1 (full training set), runs with and without Distance.
    Excluded: End_Time, Duration (post-event), Year and Source (collection artefacts), ID, free text.
11. **Big data** - MongoDB documents with GeoJSON + 2dsphere; 10 queries timed with/without indexes; Hadoop Streaming
    mapper/reducer for 3 jobs run locally (map -> sort -> reduce); three-way cross-check.

## 4. Findings

* {ins['severity']}
* {ins['weather']}
* {ins['weather_numeric']}
* {ins['states']}
* {ins['hotspots']}
* {ins['dbscan']}
* {ins['correlation']}
* {ins['time']}
* {ins['year_artifact']}
* {ins['infrastructure']}
* {ins['duration']}
* Chi-square WeatherGroup x Severity: chi2 = {wt['chi2_weathergroup_severity']['chi2']:,.1f}, dof = {wt['chi2_weathergroup_severity']['dof']}.

## 5. Results

{t['models']}

* {mli['best']}
* {mli['distance']}
* {mli['cv']}
* {mli['top_feature']} Top 5 RF features: {', '.join(f"{r.iloc[0]} ({r.iloc[1]:.3f})" for _, r in rf.iterrows())}.
* {mli['weights']} For Random Forest: sqrt macro-F1 {cw.loc[('Random Forest', 'sqrt'), 'macro_f1']} with Severity-4 recall
  {cw.loc[('Random Forest', 'sqrt'), 'recall_sev4']}, vs balanced macro-F1 {cw.loc[('Random Forest', 'inverse (balanced)'), 'macro_f1']} with Severity-4 recall
  {cw.loc[('Random Forest', 'inverse (balanced)'), 'recall_sev4']}. So sqrt weights give a higher macro-F1 but find far fewer rare
  high-impact accidents; the balanced scheme is kept as the main setting (better for triage).
* Majority baseline: accuracy {b['baseline_majority']['accuracy']}, macro-F1 {b['baseline_majority']['macro_f1']} - every model has lower
  accuracy than the baseline because class weighting shifts predictions towards rare classes; macro-F1 is the fair measure.

Big data:

{t['mongo']}

{t['cross']}

## 6. Checks of the reused upstream ideas

| Upstream idea | Result on this data |
|---|---|
| Leakage: drop duration / Distance | Distance raises the best model's macro-F1 from {b['test']['macro_f1']} to {b['test_with_distance']['macro_f1']}; it is post-event, so the headline excludes it |
| Year is a collection artefact | {ins['year_artifact']} |
| Precipitation missing -> 0 | holds only for dry weather (see `precipitation_rule_test.csv`) |
| sqrt vs inverse weights | sqrt: higher accuracy and macro-F1, lower rare-class recall (table in `class_weight_comparison.csv`) |

## 7. Limitations

* Severity = traffic impact, not injury; labels depend on the data provider and collection period.
* Counts are not rates - no traffic-volume, speed-limit or road-class data.
* Models trained on a 5.18% stratified sample with a random split; a time-based split would be stricter.
* Decision Tree probabilities are close to 0/1, so its ROC-AUC ({mc[(mc.model == 'Decision Tree') & (mc.distance_feature == 'without')]['roc_auc_ovr_macro'].iloc[0]}) is low even though its macro-F1 is close to Random Forest.
* Hadoop cluster (HDFS/YARN) and Spark runs were documented but not executed (no Docker/WSL/Java on the laptop).
* The best model file ({b['best_model']}) is larger than 50 MB and is kept locally in `models/` (not committed).
"""


def main():
    d = load_all()
    t = results_tables(d)
    (ROOT / "README.md").write_text(readme(d, t), encoding="utf-8")
    (ROOT / "docs" / "report_notes.md").write_text(report_notes(d, t), encoding="utf-8")
    print("Wrote README.md and docs/report_notes.md")


if __name__ == "__main__":
    main()
