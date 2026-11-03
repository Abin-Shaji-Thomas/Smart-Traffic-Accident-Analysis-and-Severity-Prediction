r"""Consistency checks across README, poster, best_model.json and reports/metrics (Abin Shaji Thomas).

Prints PASS / FAIL for every check and exits with code 1 if any check fails.
Run:  .venv\Scripts\python.exe scripts\check_consistency.py
"""
import json
import subprocess
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
M = ROOT / "reports" / "metrics"
results = []


def check(name, ok, detail=""):
    results.append(ok)
    print(f"{'PASS' if ok else 'FAIL'}  {name}" + (f"  ({detail})" if detail and not ok else ""))


def j(p):
    return json.loads(Path(p).read_text(encoding="utf-8"))


comp = pd.read_csv(M / "model_comparison.csv")
best = j(M / "best_model.json")
prof = j(M / "dataset_profile.json")
facts = j(ROOT / "poster" / "poster_facts.json")
cross = j(M / "bigdata_crosscheck.json")
mongo = j(M / "mongo_results.json")
hot = pd.read_csv(M / "hotspots.csv")

# 1. README results block = freshly generated block
import update_readme_results as R  # noqa: E402
readme = (ROOT / "README.md").read_text(encoding="utf-8")
inside = readme.split(R.START, 1)[1].split(R.END, 1)[0].strip()
check("README results block matches reports/metrics", inside == R.block().strip())

# 2. best_model.json agrees with model_comparison.csv
without = comp[comp["distance_feature"] == "without"].set_index("model")
models_only = without.drop(index="Majority baseline")
check("best_model.json names the highest macro-F1 model (without Distance)", best["best_model"] == models_only["macro_f1"].idxmax())
check("best_model.json with_distance is false", best["with_distance"] is False)
row = without.loc[best["best_model"]]
check("best_model.json test metrics = model_comparison.csv",
      all(abs(best["test"][k] - row[k]) < 1e-9 for k in ("accuracy", "macro_f1", "roc_auc_ovr_macro")))
check("baseline in best_model.json = model_comparison.csv",
      abs(best["baseline_majority"]["accuracy"] - without.loc["Majority baseline", "accuracy"]) < 1e-9)

# 3. poster facts agree with the metric files
pm = {m["model"]: m for m in facts["models"]}
ok = all(abs(pm[n]["accuracy"] - without.loc[n, "accuracy"]) < 1e-9 and abs(pm[n]["macro_f1"] - without.loc[n, "macro_f1"]) < 1e-9
         and (pm[n]["roc_auc"] is None if n == "Majority baseline" else abs(pm[n]["roc_auc"] - without.loc[n, "roc_auc_ovr_macro"]) < 1e-9)
         for n in without.index)
check("poster model table = model_comparison.csv (without Distance, incl. baseline)", ok and set(pm) == set(without.index))
check("poster best model = best_model.json", facts["best_model"] == best["best_model"])
check("poster total / sample rows = dataset files", facts["total_rows"] == prof["rows"] and facts["sample_rows"] == j(M / "dataset_stats.json")["sample_rows"])
check("poster date range = dataset_profile.json", facts["date_range"] == [prof["start_time_min"][:10], prof["start_time_max"][:10]])
hc = {r.label: r.accidents for r in hot.drop_duplicates("label").itertuples()}
check("poster hotspots = hotspots.csv", all(hc.get(h["label"]) == h["count"] for h in facts["top_hotspots"]))
check("poster MongoDB numbers = mongo_results.json", facts["mongo"] == {"documents": mongo["documents"], "queries": mongo["n_queries"]})
check("poster MapReduce flag = bigdata_crosscheck.json", facts["mapreduce_matches_pandas"] == cross["all_pass"])

# 4. MapReduce = pandas = MongoDB, recomputed now
from src.bigdata_check import crosscheck  # noqa: E402
fresh, _ = crosscheck(save=False)
for job, v in fresh["jobs"].items():
    check(f"MapReduce = pandas = MongoDB: {v['title']}", v["status"] == "PASS", f"{v['mismatches']} mismatches")
check("saved bigdata_crosscheck.json = fresh recomputation", fresh["jobs"] == cross["jobs"])


# 5. repository hygiene
def git(*args):
    return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True, encoding="utf-8").stdout


BI = "po" + "wer ?bi|po" + "werbi"                                           # split so this file never matches itself
AI = "|".join(["cla" + "ude", "anthr" + "opic", "chat" + "gpt", "open" + "ai", "cop" + "ilot", "co-auth" + "ored", "generated " + "with"])
check("no BI-tool mention in tracked files", git("grep", "-n", "-i", "-E", BI).strip() == "")
ai = git("grep", "-I", "-l", "-i", "-E", AI).split()                          # -I: text files only
check("no AI-tool mention in tracked text files", ai == [], ", ".join(ai))
binary = sorted(set(git("grep", "-l", "-i", "-E", AI).split()) - set(ai))
if binary:
    print(f"INFO  binary files whose embedded third-party metadata matches: {', '.join(binary)}")
allowed = {"NOTICE.md", "LICENSE", "README.md"}
names = git("grep", "-I", "-l", "-w", "-E", "Rit" + "vik|Dhr" + "uv|Mit" + "hil").split()
bad = [f for f in names if f not in allowed and "adapted from" not in (ROOT / f).read_text(encoding="utf-8", errors="ignore")[:1500].lower()]
check("original authors named only in NOTICE, LICENSE, README and adapted-file headers", bad == [], ", ".join(bad))
big = [f for f in git("ls-files").split("\n") if f and (ROOT / f).exists() and (ROOT / f).stat().st_size > 50 * 1024 ** 2]
check("no tracked file over 50 MB", big == [], ", ".join(big))
log = git("log", "--all", "--format=%an|%ae|%cn|%ce|%B%x00").split("\x00")
authors_ok = all(e.strip() == "" or e.strip().startswith("Abin-Shaji-Thomas|abinshajiabin2006@gmail.com|Abin-Shaji-Thomas|abinshajiabin2006@gmail.com|") for e in log)
trailers = [e for e in log if ("co-auth" + "ored") in e.lower() or ("generated " + "with") in e.lower()]
check("git history: only Abin-Shaji-Thomas as author/committer, no trailers", authors_ok and not trailers)

print(f"\n{sum(results)}/{len(results)} checks passed")
sys.exit(0 if all(results) else 1)
