# Smart Traffic Accident Analysis and Severity Prediction

End-semester **Data Science & Ecosystem** project (Project 3)
**Abin Shaji Thomas** - B.Tech Computer Science and Engineering (3rd year), Karunya Institute of Technology and Sciences

An end-to-end analysis of **7,728,394 US road-accident records** (2016 - March 2023): cleaning and missing-GPS
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
* File used: `US_Accidents_March23.csv` - 7,728,394 rows, 46 columns (not committed; place it in `data/raw/`).
* License: **CC BY-NC-SA 4.0** - used here for non-commercial academic purposes only. Only a 5,000-row sample
  (`data/sample/sample_5k.csv`) is redistributed, under the same license.
* Analysis sample: 399,999 rows drawn in 500,000-row chunks, stratified by Severity
  (fraction 0.051757, `random_state=42`); 399,581 rows after cleaning.

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
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
# put US_Accidents_March23.csv in data\raw\

# Modules 1-4 (run in order; each writes its outputs to data/processed and reports/)
.\.venv\Scripts\python.exe -m nbconvert --to notebook --execute --inplace --ExecutePreprocessor.timeout=-1 notebooks\01_data_science_concepts.ipynb
.\.venv\Scripts\python.exe -m nbconvert --to notebook --execute --inplace --ExecutePreprocessor.timeout=-1 notebooks\02_exploratory_data_analysis.ipynb
.\.venv\Scripts\python.exe -m nbconvert --to notebook --execute --inplace --ExecutePreprocessor.timeout=-1 notebooks\03_data_visualization.ipynb
.\.venv\Scripts\python.exe -m nbconvert --to notebook --execute --inplace --ExecutePreprocessor.timeout=-1 notebooks\04_machine_learning.ipynb

# Module 5 needs MongoDB on localhost:27017 (winget install MongoDB.Server) or MONGO_URI in a .env file
.\.venv\Scripts\python.exe -m nbconvert --to notebook --execute --inplace --ExecutePreprocessor.timeout=-1 notebooks\05_big_data_analytics.ipynb
#   (the notebook calls these; they can also be run on their own)
.\.venv\Scripts\python.exe bigdata\mongodb\load_to_mongo.py
.\.venv\Scripts\python.exe bigdata\mongodb\queries.py
powershell -ExecutionPolicy Bypass -File bigdata\hadoop_mapreduce\run_local.ps1

# regenerate this README and docs/report_notes.md from reports/metrics
.\.venv\Scripts\python.exe -m src.build_docs
```

Use `python -m nbconvert` from the venv (not a bare `jupyter` command), otherwise Windows may pick up a system-wide
Jupyter and run the notebooks with a different Python.

## Results

*All tables below are generated by `src/build_docs.py` from `reports/metrics/`.*

### Data preparation (Module 1)

* Missing GPS: Start coordinates missing **0**, outside the US box **0**;
  recovered from City+State median **0**, dropped **0**;
  End coordinates imputed from Start **176,088** (44.1% of rows)
  - `reports/metrics/gps_missing.json`.
* Duplicates removed: 418; 13 columns dropped with a computed justification
  (`reports/metrics/cleaning_log.json`); weather imputation before/after in `weather_imputation.csv`.

### Weather influence, hotspots, correlation, time (Module 2)

| WeatherGroup | accidents | share_of_accidents_pct | avg_severity | severe_pct |
|---|---|---|---|---|
| Clear | 184,327 | 46.13 | 2.1877 | 17.16 |
| Cloudy | 164,458 | 41.16 | 2.235 | 21.68 |
| Rain | 26,457 | 6.62 | 2.2491 | 22.87 |
| Fog/Haze | 10,321 | 2.58 | 2.1751 | 15.81 |
| Snow | 9,264 | 2.32 | 2.2409 | 20.2 |
| Storm | 4,590 | 1.15 | 2.2207 | 21.05 |
| Other | 164 | 0.04 | 2.0976 | 7.32 |

* Rain has the highest severe share (22.87%) vs Fog/Haze the lowest (15.81%); overall 19.47%. The link is significant (chi-square p<1e-300) but weak (Cramer's V=0.039).
* Strongest numeric weather effect: Pressure(in) (epsilon^2=0.0106); all six effects are below 0.06 (negligible/small), so single weather readings separate severity levels only slightly.
* Strongest numeric link to Severity: Year (Spearman -0.28); strongest categorical: Source (V=0.29), then City (V=0.28).
* Peak hours are 07:00 and 16:00; a weekend day averages 53% fewer accidents than a weekday.
* Severe share falls from 33.99% in 2016 to 2.83% in 2023 while counts rise - a change in data collection, so Year is not used as an ML feature.
* Accidents near a junction are severe 26.75% of the time vs 18.9% elsewhere; near a traffic signal only 9.54% vs 21.2%.
* CA, FL and TX record the most accidents (41.5% of all); top city is Miami, FL (186,768). Counts are not rates (no traffic volume).
* DBSCAN (2 km, 25 points) finds 302 dense urban clusters; the largest is around Los Angeles, CA; 57.81% of accidents are outside any dense cluster.

**Top 10 hotspot cells** (0.1 x 0.1 degree grid over all 7,728,394 records) - `reports/metrics/hotspots.csv`

| rank | label | center_lat | center_lng | accidents | avg_severity | severe_pct |
|---|---|---|---|---|---|---|
| 1 | Los Angeles, CA | 34.05 | -118.25 | 50,254 | 2.239 | 23.2 |
| 2 | Miami, FL | 25.75 | -80.35 | 42,955 | 2.023 | 1.9 |
| 3 | Miami, FL | 25.85 | -80.25 | 37,466 | 2.206 | 19.1 |
| 4 | Los Angeles, CA | 33.95 | -118.25 | 36,294 | 2.188 | 18.6 |
| 5 | Charlotte, NC | 35.25 | -80.85 | 36,259 | 2.076 | 9.1 |
| 6 | Baton Rouge, LA | 30.45 | -91.15 | 33,612 | 2.126 | 13.4 |
| 7 | Nashville, TN | 36.15 | -86.75 | 33,140 | 2.193 | 19.9 |
| 8 | Orlando, FL | 28.45 | -81.45 | 30,216 | 2.065 | 6.2 |
| 9 | Los Angeles, CA | 34.05 | -118.15 | 29,171 | 2.213 | 20.8 |
| 10 | Bronx, NY | 40.85 | -73.95 | 27,631 | 2.339 | 32.3 |

### Severity prediction (Module 4) - test set (79,917 rows)

| model | Distance(mi) | accuracy | macro-F1 | weighted-F1 | balanced acc. | ROC-AUC (OvR) | recall Sev1 | recall Sev4 |
|---|---|---|---|---|---|---|---|---|
| Decision Tree | without | 0.649 | 0.353 | 0.6852 | 0.4265 | 0.6272 | 0.3075 | 0.2287 |
| Random Forest | without | 0.5946 | 0.3751 | 0.6525 | 0.5902 | 0.8096 | 0.6537 | 0.4721 |
| Logistic Regression | without | 0.3747 | 0.2611 | 0.4606 | 0.5294 | 0.7352 | 0.7055 | 0.5964 |
| Decision Tree | with | 0.7028 | 0.4138 | 0.7322 | 0.5086 | 0.6844 | 0.3966 | 0.3034 |
| Random Forest | with | 0.6313 | 0.4206 | 0.6881 | 0.6946 | 0.8721 | 0.7457 | 0.6881 |
| Logistic Regression | with | 0.3901 | 0.2736 | 0.474 | 0.5591 | 0.75 | 0.7543 | 0.6163 |
| Majority baseline | - | 0.7966 | 0.2217 | 0.7063 | 0.25 |  | 0.0 | 0.0 |

* **Best model: Random Forest** (highest test macro-F1, without Distance(mi)); 5-fold CV macro-F1 0.3738 +/- 0.0011.
* Adding Distance(mi) changes Random Forest's macro-F1 from 0.375 to 0.421. Distance is measured after the event, so the headline results exclude it.
* Most important Random Forest feature: City_freq (0.110), then Month (0.106).

Class-weighting comparison (upstream idea, re-tested on this data) - `class_weight_comparison.csv`:

| model | weights | accuracy | macro_f1 | weighted_f1 | recall_sev1 | recall_sev4 |
|---|---|---|---|---|---|---|
| Logistic Regression | inverse (balanced) | 0.3747 | 0.2611 | 0.4606 | 0.7055 | 0.5964 |
| Logistic Regression | sqrt | 0.7681 | 0.3504 | 0.7463 | 0.1279 | 0.0681 |
| Random Forest | inverse (balanced) | 0.5946 | 0.3751 | 0.6525 | 0.6537 | 0.4721 |
| Random Forest | sqrt | 0.7984 | 0.4262 | 0.7839 | 0.1322 | 0.1493 |
| Decision Tree | inverse (balanced) | 0.649 | 0.353 | 0.6852 | 0.3075 | 0.2287 |
| Decision Tree | sqrt | 0.7007 | 0.3703 | 0.7187 | 0.2126 | 0.1805 |

### Big data (Module 5)

MongoDB `traffic_db.accidents`: 399,581 documents, indexes Severity_1, Start_Time_1, State_1, _id_, location_2dsphere; 10 queries
(median of 5 runs) - `reports/metrics/mongo_results.json`:

| query | ms with index | plan | ms without index |
|---|---|---|---|
| count_by_state | 272.52 | COLLSCAN | 253.71 |
| avg_severity_by_weather | 329.6 | COLLSCAN | 352.2 |
| top_cities | 317.42 | COLLSCAN | 375.65 |
| hourly_distribution | 264.66 | COLLSCAN | 269.84 |
| severity_counts | 228.31 | COLLSCAN | 238.9 |
| geo_near_hotspot | 50.38 | GEO_NEAR_2DSPHERE | n/a (needs 2dsphere) |
| time_range_jan_2022 | 3.29 | IXSCAN | 201.15 |
| ca_severity_4 | 14.81 | IXSCAN | 233.94 |
| top_states_severe | 113.86 | IXSCAN | 241.43 |
| latest_ny | 0.76 | IXSCAN | 297.72 |

Cross-check of the same aggregations in three engines (80 values) - `mapreduce_crosscheck.csv`:

| job | keys | pandas = MongoDB = MapReduce |
|---|---|---|
| accidents per hour | 24 | True |
| accidents per state | 49 | True |
| avg severity per weather | 7 | True |

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
