r"""Generate docs/report_notes.md - material for writing the report later (Abin Shaji Thomas).

Every number is read from reports/metrics/ and the source file is named next to it.
Run:  .venv\Scripts\python.exe scripts\build_report_notes.py
"""
import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
M = ROOT / "reports" / "metrics"
FIG = ROOT / "reports" / "figures"
MAPS = ROOT / "reports" / "maps"


def j(name):
    return json.loads((M / name).read_text(encoding="utf-8"))


def c(name, **kw):
    return pd.read_csv(M / name, **kw)


def md(df: pd.DataFrame) -> str:
    lines = ["| " + " | ".join(map(str, df.columns)) + " |", "|" + "|".join("---" for _ in df.columns) + "|"]
    for _, r in df.iterrows():
        lines.append("| " + " | ".join("-" if (isinstance(v, float) and v != v) else str(v) for v in r.values) + " |")
    return "\n".join(lines)


FIGURES = {
    "severity_distribution.png": "Severity distribution (02)", "weather_counts_severity.png": "Accidents and severe share by weather group (02)",
    "weather_numeric_by_severity.png": "Weather variables by severity, box plots (02)", "top_states_cities.png": "Top states and cities, full data (02)",
    "kmeans_selection.png": "KMeans elbow + silhouette (02)", "kmeans_clusters_map.png": "KMeans regional clusters (02)",
    "dbscan_clusters_map.png": "DBSCAN dense clusters (02)", "cramers_v.png": "Cramér's V with severity (02)",
    "time_patterns.png": "Counts and severe share by hour / weekday / month / year (02)",
    "infrastructure_severe_share.png": "Severe share with / without road features (02)",
    "accident_map.png": "Static accident map by severity (03)", "hotspot_density_heatmap.png": "Hotspot density heatmap, all records (03)",
    "heatmap_hour_weekday.png": "Hour x weekday heatmaps (03)", "timeseries_monthly.png": "Monthly trend with rolling means (03)",
    "timeseries_hourly_profile.png": "Hourly profile weekday vs weekend (03)", "timeseries_severity_share.png": "Severity share by quarter (03)",
    "weather_severity_mix.png": "Severity mix by weather + temperature bands (03)", "weather_visibility_severity.png": "Severe share by visibility (03)",
    "weather_severe_share.png": "Severe share by weather group (03)", "correlation_heatmaps.png": "Pearson and Spearman heatmaps (03)",
    "dashboard_overview.png": "One-page dashboard overview (03)", "ml_model_comparison.png": "Model comparison chart (04)",
    "roc_comparison.png": "ROC curves, OvR macro (04)", "feature_importance_top15.png": "Permutation importance, top 15 (04)",
    "ml_lr_coefficients.png": "Logistic Regression coefficients (04)", "ml_decision_tree.png": "Decision Tree, first 3 levels (04)",
    "mongo_query_timings.png": "MongoDB query timings (05)", "hadoop_data_flow.png": "Hadoop data flow with counters (05)",
    "data_flow.png": "Project data flow (05)",
}


def build() -> str:
    prof, stats, log, gps = j("dataset_profile.json"), j("dataset_stats.json"), j("cleaning_log.json"), j("gps_missing.json")
    ins, wt, db = j("eda_insights.json"), j("weather_tests.json"), j("dbscan_summary.json")
    best, mli = j("best_model.json"), j("ml_insights.json")
    mongo, cnt, cross = j("mongo_results.json"), j("mapreduce_counters.json"), j("bigdata_crosscheck.json")
    comp, hs, fi = c("model_comparison.csv"), c("hyperparameter_search.csv"), c("feature_importance.csv")
    cw, hot, infra = c("class_weight_comparison.csv"), c("hotspots.csv"), c("infrastructure_severity.csv")
    imp, win, mv = c("weather_imputation.csv"), c("outliers_winsorize.csv"), c("missing_values_before_after.csv")
    kw, cv = c("weather_kruskal.csv"), c("cramers_v.csv")
    sp = c("severity_correlations.csv", index_col=0)
    d = log["duplicates"]
    sev = stats["full_severity_counts"]
    chi = wt["chi2_weathergroup_severity"]
    pval = "< 1e-300" if chi["p_value"] == 0 else f"{chi['p_value']:.3g}"
    mt = comp[["model", "distance_feature", "accuracy", "macro_f1", "weighted_f1", "balanced_accuracy", "roc_auc_ovr_macro",
               "recall_sev1", "recall_sev2", "recall_sev3", "recall_sev4"]]
    q = pd.DataFrame(mongo["queries"])[["name", "ms_with_index", "plan_with_index", "ms_without_index", "plan_without_index"]]
    ctab = pd.DataFrame([{"job": job, **{k: v[k] for k in ("splits", "map_input_records", "map_output_records", "partitions",
                                                              "reduce_input_groups", "reduce_output_records", "seconds")},
                          "records_per_partition": str(v["partition_records"])} for job, v in cnt["jobs"].items()])
    xtab = pd.DataFrame(cross["jobs"]).T.reset_index(names="job")
    figs = [(f"reports/figures/{p.name}", FIGURES.get(p.name, "")) for p in sorted(FIG.glob("*.png"))]
    maps = [(f"reports/maps/{p.name}", "interactive HTML") for p in sorted(MAPS.glob("*.html"))]
    tabs = [f"reports/metrics/{p.name}" for p in sorted(M.glob("*")) if p.suffix in (".csv", ".json")]
    ex = mongo["example_document"]
    ex_short = {k: ex[k] for k in ["_id", "Severity", "Start_Time", "City", "State", "WeatherGroup", "Temperature_F", "Junction", "location"] if k in ex}

    return f"""# Report notes - Smart Traffic Accident Analysis and Severity Prediction

Material for writing the report (this is not the report). Generated by `scripts/build_report_notes.py`; every number
is read from `reports/metrics/` and the source file is given in brackets.

## 1. Problem

Find where and when US road accidents cluster, which weather, time and road conditions go with high traffic impact
(Severity 3-4), and how well Severity 1-4 can be predicted from what is known when an accident is reported. Severity
measures delay on traffic, not injury.

## 2. Objectives

Clean the records and handle missing GPS values; analyse weather influence; identify hotspots; run correlation
analysis; build accident maps, heatmaps, time-series plots and a dashboard; train Decision Tree, Random Forest and
Logistic Regression (+ HistGradientBoosting); store the data in MongoDB and run a Hadoop-style MapReduce data flow.

## 3. Dataset profile (`dataset_profile.json`, `dataset_stats.json`)

* File `{prof['file']}`, {prof['size_gb']} GB, {prof['rows']:,} rows x {prof['columns']} columns, {prof['n_states']} states.
* Period: {prof['start_time_min']} to {prof['start_time_max']}.
* Full-file Severity counts: 1 = {sev['1']:,}; 2 = {sev['2']:,}; 3 = {sev['3']:,}; 4 = {sev['4']:,}.
* Stratified sample: {stats['sample_rows']:,} rows, fraction {stats['sample_fraction']:.6f} per Severity level per {stats['chunksize']:,}-row chunk, random_state {stats['random_state']}.

## 4. Cleaning steps with counts (`cleaning_log.json`, `gps_missing.json`, `weather_imputation.csv`, `outliers_winsorize.csv`, `missing_values_before_after.csv`)

1. Times parsed with `format="mixed"`; unparseable Start_Time: {log['unparseable_start_time']}.
2. Duplicates: {d['duplicate_ids']} duplicate IDs, {d['duplicate_content']} duplicate-content rows removed ({d['rows_before']:,} -> {d['rows_after']:,}).
3. {len(log['dropped_columns'])} columns dropped, each with a computed reason: {', '.join(log['dropped_columns'])}.
4. Physically impossible weather values set to missing: {sum(log['impossible_values_set_to_nan'].values())} ({', '.join(f'{k} {v}' for k, v in log['impossible_values_set_to_nan'].items())}).
5. GPS: Start missing {gps['before']['Start']['missing']:,}, out of US bounds {gps['before']['Start']['out_of_us_bounds']:,}; recovered from City+State median {gps['start_recovered_city_state_median']:,}; dropped {gps['start_dropped_unrecoverable']:,}; End missing {gps['before']['End']['missing']:,} -> imputed from Start ({gps['end_imputed_from_start']:,}).
6. Weather imputation (State + Month median / mode; precipitation 0 only in dry weather groups, rule tested in `precipitation_rule_test.csv`):

{md(imp)}

7. Outliers winsorized at the 0.5th / 99.5th percentiles:

{md(win[['column', 'lower', 'upper', 'iqr_outliers', 'n_clipped', 'mean_before', 'mean_after']])}

8. Features: Hour, DayOfWeek, Month, Year, IsWeekend, IsRushHour, DayNight, RoadFeatureCount, Duration_min (EDA only).
   Durations outside (0, 1440] min set to missing: {log['duration_outside_0_1440_set_nan']:,}. Clean data: {log['rows_clean']:,} rows x {log['columns_clean']} columns.

Missing values before / after (top rows of `missing_values_before_after.csv`):

{md(mv.head(10))}

## 5. EDA findings

* Imbalance: {ins['severity']} (`eda_insights.json`)
* Weather: {ins['weather']} Chi-square {chi['chi2']:,.1f}, dof {chi['dof']}, p {pval} (`weather_tests.json`).
* Numeric weather: {ins['weather_numeric']} (`weather_kruskal.csv`)

{md(kw[['variable', 'H', 'epsilon_squared', 'median_sev1', 'median_sev2', 'median_sev3', 'median_sev4']])}

* Infrastructure: {ins['infrastructure']} (`infrastructure_severity.csv`)

{md(infra[['feature', 'true_rows', 'severe_pct_true', 'severe_pct_false', 'difference_pp', 'cramers_v']])}

* States / cities: {ins['states']} (`top_states_full.csv`, `top_cities_full.csv`)
* Hotspots: {ins['hotspots']} (`hotspots.csv`)

{md(hot[['rank', 'label', 'center_lat', 'center_lng', 'accidents', 'avg_severity', 'severe_pct']])}

* DBSCAN: {ins['dbscan']} (`dbscan_summary.json`, eps {db['eps_km']} km, min_samples {db['min_samples']}, {db['subsample_rows']:,} rows)
* Correlation: {ins['correlation']} Spearman with Severity (`severity_correlations.csv`): {', '.join(f'{i} {v:+.3f}' for i, v in sp['spearman'].head(5).items())}.
  Cramér's V (`cramers_v.csv`): {', '.join(f'{r.iloc[0]} {r.iloc[1]:.3f}' for _, r in cv.head(5).iterrows())}.
* Time: {ins['time']} {ins['year_artifact']} (`by_hour.csv`, `by_weekday.csv`, `by_month.csv`, `by_year.csv`)
* Duration: {ins['duration']}

## 6. Machine learning

**Method.** Target Severity 1-4; scikit-learn Pipeline (ColumnTransformer: scaled numeric for Logistic Regression only,
12 road flags, one-hot State / WeatherGroup / DayNight / Wind_Direction, City as frequency + top-30 one-hot);
stratified 80/20 split ({best['train_rows']:,} / {best['test_rows']:,} rows, random_state {best['random_state']});
`class_weight="balanced"`; 3-fold RandomizedSearchCV on macro-F1 over the full training set (`hyperparameter_search.csv`).
Macro-F1 is the headline because the classes are imbalanced (accuracy rewards always predicting Severity 2).
Excluded: End_Time / Duration and Distance(mi) (known only after the accident - Distance is reported separately),
Year and Source (data-collection artefacts), ID, free text.

**Results** (`model_comparison.csv`):

{md(mt)}

* {mli['best']}
* {mli['cv']} (`best_model.json`)
* {mli['distance']}
* {mli['weights']} (`class_weight_comparison.csv`)
* Best parameters ({best['best_model']}): `{json.dumps(best['params'])}`

Tuning (`hyperparameter_search.csv`):

{md(hs[['model', 'n_iter', 'cv_folds', 'best_cv_macro_f1', 'search_seconds']])}

**Feature importance** - permutation, macro-F1, 20,000 stratified test rows, 5 repeats (`feature_importance.csv`):

{md(fi.head(10))}

Class-weight comparison (`class_weight_comparison.csv`):

{md(cw)}

## 7. MongoDB design (`mongo_results.json`)

* Database `{mongo['database']}`, collection `{mongo['collection']}`, {mongo['documents']:,} documents (one per accident, `_id` = dataset ID,
  missing values omitted instead of stored as null), loaded with insert_many in batches of {mongo['load']['batch_size']:,} in {mongo['load']['load_seconds']} s.
* Indexes: {', '.join(mongo['indexes'])}.
* Example document (shortened):

```json
{json.dumps(ex_short, indent=2)}
```

* Query timings, median of {mongo['repeat']} runs:

{md(q)}

## 8. Hadoop data flow (`mapreduce_counters.json`, `bigdata_crosscheck.json`)

`run_pipeline.py`: input splits -> map (mapper.py) -> partition by `{cnt['partitioner']}` -> sort -> reduce (reducer.py) -> merge.

{md(ctab)}

Three-way cross-check ({cross['values_compared']} values, averages to {cross['tolerance_avg']}):

{md(xtab)}

The real HDFS/YARN cluster (`bigdata/hadoop_mapreduce/docker-compose.yml`) and the PySpark jobs were not executed.

## 9. UI pages (`app/`)

Home (team, objective, modules, data flow, headline KPIs) · Dataset & Cleaning · EDA (filters by State, Year, Weather,
Severity) · Maps & Hotspots (density map of all records, State filter, hotspot table, DBSCAN, hour x weekday) ·
Machine Learning (comparison with/without Distance, confusion matrices, ROC, per-class report, importance,
hyper-parameters) · Severity Predictor (form -> probabilities for Severity 1-4) · Big Data (MongoDB document,
indexes, timings, Hadoop flow, counters, cross-check). Screenshots in `docs/screenshots/`.

## 10. Testing done

* `tests/test_app.py` (pytest + Streamlit AppTest): every page loads without exception; the predictor returns four
  probabilities summing to 1; the Big Data page shows a warning, not an error, when MongoDB is unreachable.
* `scripts/check_consistency.py`: README results, poster facts and best_model.json agree with `reports/metrics`;
  MapReduce = pandas = MongoDB for all three jobs.
* Every notebook executed top to bottom with nbconvert in a fresh virtual environment.

## 11. Limitations

Severity = traffic impact, not injury; labels depend on provider and period; no traffic-volume data (counts are not
rates); models trained on a stratified sample with a random split; weather from the nearest station; the real Hadoop
cluster and Spark were not run.

## 12. Future work

Time-based train/test split; all records with Spark; traffic-volume, speed-limit and road-class features; streaming
alerts; probability calibration for the predictor.

## 13. Changes from the problem-statement document

* HistGradientBoosting (scikit-learn) is used instead of Gradient Boosting / XGBoost.
* `Distance(mi)` is excluded from the headline models (post-event leakage); runs with it are reported separately.
* A Hadoop / MapReduce data flow was added (local split-map-shuffle-sort-reduce with real counters).
* The desktop BI-tool dashboard named in the problem statement was replaced by the Streamlit dashboard plus `reports/figures/dashboard_overview.png`.
* The verified dataset period is {prof['start_time_min'][:10]} to {prof['start_time_max'][:10]} (`dataset_profile.json`).

## 14. Figures, maps and tables

{md(pd.DataFrame(figs + maps, columns=['file', 'content (notebook)']))}

Tables (`reports/metrics/`): {', '.join(f'`{t.split("/")[-1]}`' for t in tabs)}.
"""


if __name__ == "__main__":
    (ROOT / "docs" / "report_notes.md").write_text(build(), encoding="utf-8")
    print("wrote docs/report_notes.md")
