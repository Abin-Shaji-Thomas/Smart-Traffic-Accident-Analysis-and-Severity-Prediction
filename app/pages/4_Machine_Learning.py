"""Module 4 - model comparison and evaluation (Abin Shaji Thomas)."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import plotly.express as px  # noqa: E402
import streamlit as st  # noqa: E402

import utils as U  # noqa: E402
from src import modeling as M  # noqa: E402

U.setup("Machine Learning", "Module 4 - predicting Severity 1-4 with four classifiers (class_weight='balanced', test set).")
comp = U.metric_csv("model_comparison.csv")
best = U.metric_json("best_model.json")

dist = st.radio("Distance(mi) feature", ["without", "with"], horizontal=True,
                help="Distance is measured after the accident (leakage), so the headline results are WITHOUT it.")
t = comp[comp["distance_feature"] == dist]
cols = ["model", "accuracy", "macro_f1", "weighted_f1", "balanced_accuracy", "roc_auc_ovr_macro",
        "recall_sev1", "recall_sev2", "recall_sev3", "recall_sev4", "train_seconds"]
st.subheader("Model comparison (incl. majority-class baseline)")
st.caption("Macro-F1 averages the F1 of the four classes equally, so it is the headline metric for this imbalanced target.")
num = [c for c in cols if c not in ("model", "train_seconds")]
show = t[cols].copy()
best_row = show["macro_f1"].idxmax()
for c in num:
    show[c] = show[c].map(lambda v: "-" if v != v else f"{v:.3f}")
show["train_seconds"] = show["train_seconds"].map(lambda v: f"{v:.1f}")
st.dataframe(show.style.apply(lambda r: ["background-color: #dceaf9" if r.name == best_row else "" for _ in r], axis=1),
             width="stretch", hide_index=True)

long = t.melt(id_vars="model", value_vars=["accuracy", "macro_f1", "weighted_f1", "roc_auc_ovr_macro"], var_name="metric", value_name="score")
st.plotly_chart(px.bar(long, x="model", y="score", color="metric", barmode="group", height=380, range_y=[0, 1],
                       color_discrete_sequence=["#2a78d6", "#eb6834", "#1baf7a", "#eda100"]), width="stretch")

a, b = st.columns(2)
with a:
    st.subheader("Confusion matrix")
    name = st.selectbox("Model", M.MODEL_NAMES, index=M.MODEL_NAMES.index(best["best_model"]))
    st.caption("Rows = actual severity, normalised so each row sums to 1 (without Distance).")
    cm = U.metric_csv(f"confusion_{M.slug(name)}.csv", index_col=0)
    st.plotly_chart(px.imshow(cm, text_auto=".2f", zmin=0, zmax=1, color_continuous_scale=["#f4f8fd", "#86b6ef", "#1c5cab", "#0d366b"],
                              height=400, labels={"x": "predicted", "y": "actual", "color": "share"}), width="stretch")
    st.caption("Per-class report")
    st.dataframe(U.metric_csv(f"classification_report_{M.slug(name)}.csv"), width="stretch", hide_index=True)
with b:
    st.subheader("ROC curves (one-vs-rest, macro-average)")
    st.caption("Higher curve = better ranking of accidents by severity probability.")
    U.figure("roc_comparison.png")

c, d = st.columns(2)
with c:
    fi = U.metric_csv("feature_importance.csv").head(15).iloc[::-1]
    st.subheader(f"Top 15 features - {best['best_model']}")
    st.caption("Permutation importance: drop in macro-F1 when a column is shuffled (20,000 test rows, 5 repeats).")
    st.plotly_chart(px.bar(fi, x="importance_mean", y="feature", orientation="h", error_x="importance_std", height=480,
                           color_discrete_sequence=["#2a78d6"], labels={"importance_mean": "drop in macro-F1", "feature": ""}),
                    width="stretch")
with d:
    st.subheader("Tuned hyper-parameters")
    st.caption("3-fold RandomizedSearchCV on macro-F1 over the full training set.")
    hs = U.metric_csv("hyperparameter_search.csv")
    st.dataframe(hs, width="stretch", hide_index=True)
    st.markdown(f"**Best model:** {best['best_model']} - `{json.dumps(best['params'])}`")

st.subheader("Honest reading of the results")
tb, bl = best["test"], best["baseline_majority"]
st.info(
    f"{best['best_model']} reaches macro-F1 {tb['macro_f1']:.3f} (5-fold CV {best['cv_5fold']['macro_f1_mean']:.3f} ± "
    f"{best['cv_5fold']['macro_f1_std']:.3f}) against {bl['macro_f1']:.3f} for always predicting the majority class. Its accuracy "
    f"({tb['accuracy']:.3f}) is {'below' if tb['accuracy'] < bl['accuracy'] else 'above'} the baseline's {bl['accuracy']:.3f}, because "
    f"balanced class weights trade accuracy for recall of the rare classes (Severity 3 recall {tb['recall_sev3']:.3f}, "
    f"Severity 4 recall {tb['recall_sev4']:.3f}). With the post-event Distance feature macro-F1 would be "
    f"{best['test_with_distance']['macro_f1']:.3f}, but that information is not available when an accident is reported. "
    f"Year is excluded because the severity labels drift with the data collection.")
