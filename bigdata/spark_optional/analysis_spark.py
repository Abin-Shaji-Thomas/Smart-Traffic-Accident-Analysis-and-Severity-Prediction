"""OPTIONAL PySpark version - NOT EXECUTED in this project (no Java/Spark installed; PySpark
does not support the project's Python 3.14). The executed pipeline is the pandas version in src/.

Adapted from src/analysis.py of
https://github.com/rit-vik/Accident-Severity-Prediction-and-Hotspot-Analysis-of-US-Road-Accidents-BDA-Project-
(MIT, Ritvik Kar, Dhruv Abhijit Desai, Mithil S) - see NOTICE.md.
Changes by Abin Shaji Thomas: local paths; outputs go to bigdata/spark_optional/output/.
Run (if Spark is available):  spark-submit bigdata/spark_optional/analysis_spark.py
"""
import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from pyspark.sql import SparkSession

spark = SparkSession.builder.appName("accidents-analysis").getOrCreate()
spark.read.parquet("data/processed/spark_clean").createOrReplaceTempView("acc")
os.makedirs("bigdata/spark_optional/output", exist_ok=True)
os.makedirs("bigdata/spark_optional/output", exist_ok=True)

SEV = "ROUND(100 * AVG(CASE WHEN Severity >= 3 THEN 1 ELSE 0 END), 1) AS severe_pct"
queries = {
  "top_states":  f"SELECT State, COUNT(*) AS accidents, {SEV} FROM acc GROUP BY State ORDER BY accidents DESC LIMIT 10",
  "top_cities":  f"SELECT City, State, COUNT(*) AS accidents, {SEV} FROM acc WHERE City <> 'Unknown' GROUP BY City, State ORDER BY accidents DESC LIMIT 10",
  "by_hour":     f"SELECT hour, COUNT(*) AS accidents, {SEV} FROM acc GROUP BY hour ORDER BY hour",
  "by_weekday":  f"SELECT day_of_week, COUNT(*) AS accidents, {SEV} FROM acc GROUP BY day_of_week ORDER BY day_of_week",
  "by_weather":  f"SELECT weather_group, COUNT(*) AS accidents, {SEV} FROM acc GROUP BY weather_group ORDER BY accidents DESC",
  "by_season":   f"SELECT season, COUNT(*) AS accidents, {SEV} FROM acc GROUP BY season ORDER BY accidents DESC",
  "by_year":     f"SELECT year, COUNT(*) AS accidents, {SEV} FROM acc GROUP BY year ORDER BY year",
}

results = {}
for name, q in queries.items():
    pdf = spark.sql(q).toPandas()
    pdf.to_csv(f"bigdata/spark_optional/output/{name}.csv", index=False)
    results[name] = pdf
    print("\n==", name)
    print(pdf.to_string(index=False))

# Road infrastructure vs severity
infra = None
for f in ["Traffic_Signal", "Junction", "Crossing", "Stop", "Railway", "Bump"]:
    part = spark.sql(f"SELECT '{f}' AS feature, {f} AS present, COUNT(*) AS accidents, {SEV} FROM acc GROUP BY {f}")
    infra = part if infra is None else infra.unionByName(part)
ipdf = infra.toPandas().sort_values(["feature", "present"])
ipdf.to_csv("bigdata/spark_optional/output/infrastructure.csv", index=False)
print("\n== infrastructure")
print(ipdf.to_string(index=False))

def bar(pdf, x, y, title, fname, rot=0):
    plt.figure(figsize=(8, 4))
    plt.bar(pdf[x].astype(str), pdf[y])
    plt.title(title); plt.xlabel(x); plt.ylabel(y)
    plt.xticks(rotation=rot); plt.tight_layout()
    plt.savefig(f"bigdata/spark_optional/output/{fname}.png", dpi=150); plt.close()

bar(results["top_states"], "State", "accidents", "Top 10 states by accidents", "top_states")
bar(results["by_hour"], "hour", "accidents", "Accidents by hour of day", "by_hour")
bar(results["by_hour"], "hour", "severe_pct", "Severe (3-4) share by hour of day, %", "severe_by_hour")
bar(results["by_weather"], "weather_group", "severe_pct", "Severe (3-4) share by weather, %", "severe_by_weather", 30)
bar(results["by_year"], "year", "accidents", "Accidents by year", "by_year")
spark.stop()
