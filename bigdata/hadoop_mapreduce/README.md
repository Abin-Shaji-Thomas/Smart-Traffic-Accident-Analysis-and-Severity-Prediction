# Hadoop data flow - MapReduce with Hadoop Streaming

Three MapReduce jobs written for **Hadoop Streaming** (Python mapper/reducer on stdin/stdout):

| Job | Mapper emits | Reducer outputs |
|---|---|---|
| `state` - accidents per state | `State \t 1` | `State \t count` |
| `weather` - average severity per weather group | `WeatherGroup \t Severity` | `WeatherGroup \t count \t sum \t avg` |
| `hour` - accidents per hour | `HH \t 1` | `HH \t count` |

Input: `input/accidents.tsv` (`ID, State, WeatherGroup, Hour, Severity`) exported from the cleaned sample by
`export_input.py` - the same rows used by pandas and MongoDB, so all three engines can be cross-checked
(notebook 05).

## 1. Local run of the Hadoop data flow (EXECUTED)

`run_pipeline.py` runs the unchanged `mapper.py` / `reducer.py` with the same stages as Hadoop Streaming:

```
input/accidents.tsv -> 4 input splits (like HDFS blocks) -> 4 map tasks (mapper.py <job>)
  -> partition by zlib.crc32(key) % 2 -> sort each partition by key -> 2 reduce tasks (reducer.py <job>)
  -> output/<job>/part-00000, part-00001 -> merged output/<job>.tsv
```

```powershell
.venv\Scripts\python.exe bigdata\hadoop_mapreduce\run_pipeline.py
```

It writes the real job counters (splits, map input/output records, records per partition, reduce input groups,
reduce output records, seconds) to `reports/metrics/mapreduce_counters.json`. `input/` and `output/` are regenerated
and not committed. Notebook 05 compares the outputs with pandas and MongoDB (`reports/metrics/bigdata_crosscheck.json`).

## 2. Optional run on a real Hadoop cluster (NOT EXECUTED)

**The cluster was not executed** for this project: Docker (and WSL) are not installed on the development laptop. The commands below
are the standard Hadoop 3 commands for the single-node cluster defined in `docker-compose.yml` + `hadoop.env`.

```powershell
# start HDFS (NameNode, DataNode) and YARN (ResourceManager, NodeManager)
docker compose -f bigdata/hadoop_mapreduce/docker-compose.yml up -d
docker compose -f bigdata/hadoop_mapreduce/docker-compose.yml exec namenode bash
```

Inside the `namenode` container (the folder is mounted at `/workspace`):

```bash
# 1. put the input into HDFS
hdfs dfs -mkdir -p /user/root/accidents/input
hdfs dfs -put -f /workspace/input/accidents.tsv /user/root/accidents/input/
hdfs dfs -ls /user/root/accidents/input

# 2. run one streaming job per task (job = state | weather | hour)
for JOB in state weather hour; do
  hdfs dfs -rm -r -f /user/root/accidents/output_$JOB
  hadoop jar $HADOOP_HOME/share/hadoop/tools/lib/hadoop-streaming-*.jar \
    -files /workspace/mapper.py,/workspace/reducer.py \
    -mapper "python3 mapper.py $JOB" \
    -reducer "python3 reducer.py $JOB" \
    -input /user/root/accidents/input \
    -output /user/root/accidents/output_$JOB
done

# 3. read the results back
hdfs dfs -cat /user/root/accidents/output_state/part-*   | head
hdfs dfs -get /user/root/accidents/output_weather/part-00000 /workspace/output/weather_hadoop.tsv
```

Web UIs: HDFS http://localhost:9870, YARN http://localhost:8088. Stop with
`docker compose -f bigdata/hadoop_mapreduce/docker-compose.yml down`.
(The `apache/hadoop` image needs `python3` available in the container for the streaming tasks; install it with
`yum install -y python3` / `apt-get install -y python3` inside the containers if missing.)
