#!/usr/bin/env python3
"""Hadoop Streaming mapper for three jobs (Abin Shaji Thomas).

Usage:  python mapper.py <job>      job = state | weather | hour
Input  (stdin): tab-separated lines  ID  State  WeatherGroup  Hour  Severity   (first line = header)
Output (stdout): key <TAB> value
  state   -> State        1
  weather -> WeatherGroup Severity
  hour    -> HH (00-23)   1
The header/malformed-line handling follows the idea of the upstream ingest step
(https://github.com/rit-vik/Accident-Severity-Prediction-and-Hotspot-Analysis-of-US-Road-Accidents-BDA-Project-,
MIT): skip the header, never fail on a bad record, count bad records. Counters use the Hadoop Streaming
'reporter:counter:' protocol on stderr, so they appear in the job counters on a real cluster.
Standard library only, so the same file runs on any Hadoop node.
"""
import sys

FIELDS = ["ID", "State", "WeatherGroup", "Hour", "Severity"]


def main(job: str) -> None:
    for line in sys.stdin:
        parts = line.rstrip("\r\n").split("\t")
        if len(parts) != len(FIELDS) or parts[0] == "ID":
            if parts[0] != "ID":
                sys.stderr.write("reporter:counter:accidents,malformed_lines,1\n")
            continue
        _id, state, weather, hour, severity = parts
        try:
            sev = int(severity)
            hr = int(hour)
        except ValueError:
            sys.stderr.write("reporter:counter:accidents,bad_numbers,1\n")
            continue
        if job == "state":
            print(f"{state}\t1")
        elif job == "weather":
            print(f"{weather}\t{sev}")
        elif job == "hour":
            print(f"{hr:02d}\t1")
        else:
            raise SystemExit(f"unknown job: {job}")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "state")
