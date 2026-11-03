#!/usr/bin/env python3
"""Hadoop Streaming reducer for the three jobs (Abin Shaji Thomas).

Usage:  python reducer.py <job>      job = state | weather | hour
Input (stdin): key <TAB> value lines, SORTED by key (Hadoop's shuffle/sort, or `sort` locally).
Output:
  state / hour -> key <TAB> count
  weather      -> key <TAB> count <TAB> sum_severity <TAB> avg_severity
Standard library only.
"""
import sys


def emit(job, key, count, total):
    if key is None:
        return
    if job == "weather":
        print(f"{key}\t{count}\t{total}\t{total / count:.6f}")
    else:
        print(f"{key}\t{count}")


def main(job: str) -> None:
    cur, count, total = None, 0, 0
    for line in sys.stdin:
        line = line.rstrip("\r\n")
        if not line:
            continue
        key, value = line.split("\t", 1)
        v = int(value)
        if key != cur:
            emit(job, cur, count, total)
            cur, count, total = key, 0, 0
        count += 1 if job == "weather" else v
        total += v
    emit(job, cur, count, total)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "state")
