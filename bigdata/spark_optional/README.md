# Optional PySpark pipeline (NOT EXECUTED)

These four scripts are the upstream project's PySpark jobs, adapted to local paths
(see the header of each file and `NOTICE.md`). They are kept only as an optional extra.

**Status: not executed.** Java (OpenJDK 11) and PySpark were deliberately not installed for this
project, and PySpark does not support the project's Python 3.14. All results in this repository come
from the pandas / scikit-learn pipeline in `src/` and `notebooks/`.

| Script | Equivalent executed step |
|---|---|
| `ingest_spark.py` | notebook 01 (chunked read, data dictionary) |
| `clean_spark.py` | notebook 01 (cleaning, features) |
| `analysis_spark.py` | notebook 02 (group-by analysis) |
| `ml_spark.py` | notebook 04 (LR + RF) |

To run them on a machine with Java 11, Python 3.11 and `pip install pyspark==3.5.1`:

```powershell
spark-submit bigdata/spark_optional/ingest_spark.py
spark-submit bigdata/spark_optional/clean_spark.py
spark-submit bigdata/spark_optional/analysis_spark.py
spark-submit bigdata/spark_optional/ml_spark.py
```
