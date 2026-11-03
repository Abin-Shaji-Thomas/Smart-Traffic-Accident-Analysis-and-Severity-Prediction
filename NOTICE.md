# NOTICE - Third-party code and data

## Upstream code

Parts of this repository are adapted from:

- **Repository:** [rit-vik/Accident-Severity-Prediction-and-Hotspot-Analysis-of-US-Road-Accidents-BDA-Project-](https://github.com/rit-vik/Accident-Severity-Prediction-and-Hotspot-Analysis-of-US-Road-Accidents-BDA-Project-)
- **Commit used:** [`160ba7f`](https://github.com/rit-vik/Accident-Severity-Prediction-and-Hotspot-Analysis-of-US-Road-Accidents-BDA-Project-/commit/160ba7f)
- **Authors:** Ritvik Kar, Dhruv Abhijit Desai, Mithil S (Department of Data Science Engineering, MIT Manipal)

### Upstream license statement (quoted exactly)

The upstream repository contains no `LICENSE` file. Its only license statement is
the last line of its `README.md`:

> Code is released under the MIT license. The dataset keeps its original CC BY-NC-SA 4.0 license.

### Reconstructed MIT notice for the upstream code

**This is a reconstruction.** Because the upstream repository ships no LICENSE file
and no copyright line, the text below is the standard MIT license text with a
copyright line built from the upstream authors' names and the year of their commits
(2026). It is provided so that the MIT condition ("the above copyright notice and
this permission notice shall be included") is honoured as closely as possible.

```
MIT License

Copyright (c) 2026 Ritvik Kar, Dhruv Abhijit Desai, Mithil S

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

### What was adapted

| Upstream file | Where it lives here | What changed |
|---|---|---|
| `src/ingest.py` | `src/cleaning.py` (chunked reader, column-name sanitiser), `bigdata/spark_optional/ingest_spark.py` | Re-expressed in pandas with chunked reading; Spark version kept as optional, local paths |
| `src/clean.py` | `src/cleaning.py`, `src/features.py`, `bigdata/spark_optional/clean_spark.py` | Plausible-range limits, time features and regex weather grouping reused; weather groups changed to 7 project categories; GPS recovery, group-wise imputation, outlier handling added |
| `src/analysis.py` | `src/analysis.py`, `bigdata/spark_optional/analysis_spark.py` | Spark SQL group-bys re-expressed in pandas |
| `src/ml.py`, `src/ml2.py` | `src/modeling.py`, notebook 04, `bigdata/spark_optional/ml_spark.py` | Re-expressed in scikit-learn; `metrics()` helper and inverse-vs-sqrt class-weighting idea reused |
| `src/make_ml_charts.py` | notebook 04 | Plotting pattern only |

Nothing from the upstream `charts/`, `results/`, `outputs/`, `screenshots/`, `docs/` or
`cluster/` folders is included. Every number, chart and table in this repository was
regenerated from this project's own run.

## Dataset

US Accidents (2016 - March 2023), by Sobhan Moosavi et al., distributed under
**CC BY-NC-SA 4.0**. Used here for non-commercial academic purposes only. The data is
not redistributed in this repository except for a 5,000-row sample
(`data/sample/sample_5k.csv`), shared under the same CC BY-NC-SA 4.0 terms.

1. S. Moosavi, M. H. Samavatian, S. Parthasarathy, R. Ramnath, "A Countrywide Traffic Accident Dataset", arXiv:1906.05409, 2019.
2. S. Moosavi, M. H. Samavatian, S. Parthasarathy, R. Teodorescu, R. Ramnath, "Accident Risk Prediction based on Heterogeneous Sparse Data: New Dataset and Insights", ACM SIGSPATIAL, 2019.
