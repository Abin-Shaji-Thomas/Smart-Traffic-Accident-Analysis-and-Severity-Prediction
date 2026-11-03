#!/usr/bin/env python3
"""Create poster/poster_facts.json from the real result files in reports/metrics/ (Abin Shaji Thomas).

Every number and every insight sentence is read or built from those files - nothing is typed by hand.
The output follows the schema in poster/poster_facts.template.json (plus captions, date range and raw size).
Model rows are the leakage-free runs (without Distance) plus the majority-class baseline.

Usage (from the repo root):  python poster/make_poster_facts.py [--root .]
"""
import argparse
import csv
import json
import os

MODELS = ["Decision Tree", "Random Forest", "Logistic Regression", "HistGradientBoosting"]
TEAM = [{"name": "Abin Shaji Thomas", "reg_no": "URK24CS6007"},
        {"name": "Jinto Joseph", "reg_no": "URK24CS1210"},
        {"name": "BÉAL Elouan", "reg_no": "ISK26CS1005"}]
SUPERVISOR = "Dr. Anusha Bamini A M, Assistant Professor, Division of Computer Science and Engineering"


def jload(path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def rows_of(path):
    with open(path, encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def main(root):
    m = os.path.join(root, "reports", "metrics")
    prof = jload(os.path.join(m, "dataset_profile.json"))
    stats = jload(os.path.join(m, "dataset_stats.json"))
    gps = jload(os.path.join(m, "gps_missing.json"))
    ins = jload(os.path.join(m, "eda_insights.json"))
    mongo = jload(os.path.join(m, "mongo_results.json"))
    cross = jload(os.path.join(m, "bigdata_crosscheck.json"))
    best_json = jload(os.path.join(m, "best_model.json"))

    # hotspots: four distinct cities, densest 0.1-degree cell of each
    hot, seen = [], set()
    for row in rows_of(os.path.join(m, "hotspots.csv")):
        if row["label"] not in seen:
            seen.add(row["label"])
            hot.append({"label": row["label"], "count": int(row["accidents"])})
        if len(hot) == 4:
            break

    # models (without Distance) + majority baseline
    rows = rows_of(os.path.join(m, "model_comparison.csv"))
    chosen = {r["model"]: r for r in rows if r["distance_feature"] == "without"}
    models = [{"model": n, "accuracy": float(chosen[n]["accuracy"]), "macro_f1": float(chosen[n]["macro_f1"]),
               "roc_auc": float(chosen[n]["roc_auc_ovr_macro"])} for n in MODELS]
    best = max(models, key=lambda r: r["macro_f1"])["model"]
    assert best == best_json["best_model"], "best model differs from best_model.json"
    base = chosen["Majority baseline"]
    models.append({"model": "Majority baseline", "accuracy": float(base["accuracy"]),
                   "macro_f1": float(base["macro_f1"]), "roc_auc": None})
    b = chosen[best]
    n_below = sum(float(chosen[n]["accuracy"]) < float(base["accuracy"]) for n in MODELS)
    conclusion = (f"{'All' if n_below == len(MODELS) else n_below} models fall below the {float(base['accuracy']) * 100:.1f}% baseline "
                  f"accuracy, so macro-F1 is used; it finds {float(b['recall_sev3']) * 100:.0f}% of Severity 3 and "
                  f"{float(b['recall_sev4']) * 100:.0f}% of Severity 4 accidents.")

    # missing GPS
    sm, em, rb = gps["before"]["Start"]["missing"], gps["before"]["End"]["missing"], gps["rows_before"]
    if sm == 0:
        gps_text = f"no Start GPS was missing; {em:,} End coordinates ({em / rb * 100:.1f}% of {rb:,} records) were imputed from the Start point."
    else:
        gps_text = (f"{sm:,} Start and {em:,} End coordinates were missing; {gps['start_recovered_city_state_median']:,} Start values "
                    f"recovered from City + State medians, {gps['start_dropped_unrecoverable']:,} rows dropped, End imputed from Start.")

    # insight sentences built from the files
    wt = jload(os.path.join(m, "weather_tests.json"))["chi2_weathergroup_severity"]
    bw = {r["WeatherGroup"]: float(r["severe_pct"]) for r in rows_of(os.path.join(m, "by_weather.csv")) if r["WeatherGroup"] != "Other"}
    hi, lo = max(bw, key=bw.get), min(bw, key=bw.get)
    weather = (f"{hi} has the highest severe share ({bw[hi]:.1f}%), {lo} the lowest ({bw[lo]:.1f}%); "
               f"weak link (Cramér's V = {wt['cramers_v']:.3f}).")
    time_ = ins["time"]
    fi = rows_of(os.path.join(m, "feature_importance.csv"))[:3]
    predictors = (f"{fi[0]['feature']}, {fi[1]['feature']} and {fi[2]['feature']} lead the permutation importance; "
                  f"Year excluded as a collection artifact.")

    facts = {
        "total_rows": prof["rows"], "sample_rows": stats["sample_rows"],
        "date_range": [prof["start_time_min"][:10], prof["start_time_max"][:10]],
        "raw_size_gb": prof["size_gb"],
        "gps": {"missing_before": sm + em if sm else em, "recovered": gps["start_recovered_city_state_median"],
                "dropped": gps["start_dropped_unrecoverable"]},
        "gps_text": gps_text,
        "top_hotspots": hot,
        "weather_insight": weather, "time_insight": time_, "correlation_insight": predictors,
        "models": models, "best_model": best, "conclusion": conclusion,
        "mongo": {"documents": mongo["documents"], "queries": mongo["n_queries"]},
        "mapreduce_matches_pandas": bool(cross["all_pass"]),
        "images": {"heatmap": "poster/assets/hotspots_map.png", "timeseries": "poster/assets/timeseries.png",
                   "dashboard": "poster/assets/streamlit.png"},
        "captions": {"fig1": f"Fig. 1  Accident density, all {prof['rows'] / 1e6:.1f} million records",
                     "fig2": "Fig. 2  Monthly accidents, 12-month mean",
                     "fig3": "Fig. 3  Streamlit dashboard (ML page)"},
        "team": TEAM, "supervisor": SUPERVISOR,
    }
    out = os.path.join(root, "poster", "poster_facts.json")
    with open(out, "w", encoding="utf-8") as fh:
        json.dump(facts, fh, indent=2, ensure_ascii=False)
    print("wrote", out)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".")
    main(ap.parse_args().root)
