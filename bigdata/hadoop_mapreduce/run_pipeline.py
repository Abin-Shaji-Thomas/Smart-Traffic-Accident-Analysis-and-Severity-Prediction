"""Run the three MapReduce jobs with the same data flow as Hadoop Streaming, locally (Abin Shaji Thomas).

    input/accidents.tsv
      -> INPUT SPLITS   4 splits (like HDFS blocks / map input splits)
      -> MAP            mapper.py <job> on every split (4 map tasks, run in parallel)
      -> PARTITION      key -> zlib.crc32(key) % 2  (2 reducers; deterministic, unlike Python's hash())
      -> SORT           each partition sorted by key (Hadoop's shuffle & sort)
      -> REDUCE         reducer.py <job> on every partition (2 reduce tasks)
      -> OUTPUT         part-00000 / part-00001 merged into output/<job>.tsv

The real counters of every job are written to reports/metrics/mapreduce_counters.json.
mapper.py and reducer.py are the unchanged Hadoop Streaming scripts (see README.md for the cluster commands).

Run from the repository root:  .venv\\Scripts\\python.exe bigdata\\hadoop_mapreduce\\run_pipeline.py
"""
from __future__ import annotations

import json
import subprocess
import sys
import time
import zlib
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
INPUT = HERE / "input" / "accidents.tsv"
SPLIT_DIR = HERE / "input" / "splits"
OUT_DIR = HERE / "output"
COUNTERS = ROOT / "reports" / "metrics" / "mapreduce_counters.json"
JOBS = ["state", "weather", "hour"]
N_SPLITS, N_REDUCERS = 4, 2
PY = sys.executable


def make_splits() -> list[Path]:
    """Cut the input into N_SPLITS line-aligned splits of (almost) equal size; the header stays in split 0."""
    lines = INPUT.read_text(encoding="utf-8").splitlines(keepends=True)
    SPLIT_DIR.mkdir(parents=True, exist_ok=True)
    size = -(-len(lines) // N_SPLITS)
    paths = []
    for i in range(N_SPLITS):
        p = SPLIT_DIR / f"split-{i:05d}.tsv"
        p.write_text("".join(lines[i * size:(i + 1) * size]), encoding="utf-8")
        paths.append(p)
    return paths


def run_task(script: str, job: str, data: str) -> tuple[list[str], dict]:
    r = subprocess.run([PY, str(HERE / script), job], input=data, capture_output=True, text=True, encoding="utf-8")
    if r.returncode != 0:
        raise RuntimeError(f"{script} {job} failed:\n{r.stderr}")
    user = {}
    for line in r.stderr.splitlines():   # Hadoop Streaming counter protocol: reporter:counter:group,name,amount
        if line.startswith("reporter:counter:"):
            _, _, rest = line.split(":", 2)
            group, name, amount = rest.split(",")
            user[f"{group}.{name}"] = user.get(f"{group}.{name}", 0) + int(amount)
    return [l for l in r.stdout.splitlines() if l], user


def partition(key: str) -> int:
    return zlib.crc32(key.encode("utf-8")) % N_REDUCERS


def run_job(job: str, splits: list[Path]) -> dict:
    t0 = time.time()
    split_text = [p.read_text(encoding="utf-8") for p in splits]
    map_in = [sum(1 for l in t.splitlines() if l and not l.startswith("ID\t")) for t in split_text]
    with ThreadPoolExecutor(N_SPLITS) as ex:                      # 4 map tasks in parallel
        maps = list(ex.map(lambda t: run_task("mapper.py", job, t), split_text))
    user_counters = {}
    for _, u in maps:
        for k, v in u.items():
            user_counters[k] = user_counters.get(k, 0) + v
    parts = [[] for _ in range(N_REDUCERS)]                       # shuffle / partition
    for out, _ in maps:
        for line in out:
            parts[partition(line.split("\t", 1)[0])].append(line)
    for p in parts:                                               # sort by key (stable)
        p.sort(key=lambda l: l.split("\t", 1)[0])
    with ThreadPoolExecutor(N_REDUCERS) as ex:                    # 2 reduce tasks in parallel
        reds = list(ex.map(lambda p: run_task("reducer.py", job, "\n".join(p) + "\n"), parts))
    OUT_DIR.mkdir(exist_ok=True)
    job_dir = OUT_DIR / job
    job_dir.mkdir(exist_ok=True)
    for i, (out, _) in enumerate(reds):                           # part-0000i like Hadoop
        (job_dir / f"part-{i:05d}").write_text("\n".join(out) + "\n", encoding="utf-8")
    merged = sorted(l for out, _ in reds for l in out)
    (OUT_DIR / f"{job}.tsv").write_text("\n".join(merged) + "\n", encoding="utf-8")
    return {"splits": N_SPLITS, "map_tasks": N_SPLITS, "map_input_records": sum(map_in),
            "map_input_records_per_split": map_in, "map_output_records": sum(len(o) for o, _ in maps),
            "partitions": N_REDUCERS, "reduce_tasks": N_REDUCERS,
            "partition_records": [len(p) for p in parts],
            "reduce_input_groups": sum(len({l.split("\t", 1)[0] for l in p}) for p in parts),
            "reduce_output_records": len(merged), "user_counters": user_counters,
            "output": f"bigdata/hadoop_mapreduce/output/{job}.tsv", "seconds": round(time.time() - t0, 2)}


def main() -> dict:
    if not INPUT.exists():
        subprocess.run([PY, str(HERE / "export_input.py")], check=True)
    splits = make_splits()
    counters = {"input": "bigdata/hadoop_mapreduce/input/accidents.tsv",
                "input_lines_including_header": sum(1 for _ in open(INPUT, encoding="utf-8")),
                "partitioner": "zlib.crc32(key) % 2", "jobs": {}}
    for job in JOBS:
        counters["jobs"][job] = run_job(job, splits)
        c = counters["jobs"][job]
        print(f"job={job:8s} map_in={c['map_input_records']:,} map_out={c['map_output_records']:,} "
              f"partitions={c['partition_records']} groups={c['reduce_input_groups']} out={c['reduce_output_records']} "
              f"{c['seconds']} s")
    COUNTERS.parent.mkdir(parents=True, exist_ok=True)
    COUNTERS.write_text(json.dumps(counters, indent=2), encoding="utf-8")
    return counters


if __name__ == "__main__":
    main()
