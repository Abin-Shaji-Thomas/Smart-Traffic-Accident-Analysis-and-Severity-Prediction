#!/usr/bin/env python3
"""Draw the two data figures of the poster at their exact printed size (89 x 63 mm, 300 DPI)
from the real project result tables. Labels are sized for reading on an A3 print.

Reads : data/processed/full_hotspot_grid.parquet   (all records, 0.1-degree cells)
        reports/metrics/monthly_trend.csv
        reports/metrics/hotspots.csv
Writes: poster/assets/hotspots_map.png, timeseries.png

Usage (from the repo root):  python poster/make_poster_figures.py [--root .]
"""
import argparse
import os

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.colors import LinearSegmentedColormap

NAVY, RED, MUTED, GRID = "#1F2A44", "#C11B2F", "#8A93A6", "#E3E7EF"
SEQ = LinearSegmentedColormap.from_list("seq", ["#EAF0FA", "#9DB4DC", "#3C5FA8", NAVY])
W_IN, H_IN, DPI = 89 / 25.4, 63 / 25.4, 300

plt.rcParams.update({
    "font.family": "serif",
    "font.serif": ["Times New Roman", "Liberation Serif", "DejaVu Serif"],
    "font.size": 8, "axes.edgecolor": MUTED, "axes.labelcolor": NAVY,
    "xtick.color": NAVY, "ytick.color": NAVY, "axes.linewidth": 0.5,
})


def clean(ax):
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)


def fig_map(root, out):
    grid = pd.read_parquet(os.path.join(root, "data", "processed", "full_hotspot_grid.parquet"))
    g = grid.groupby(["cell_lat", "cell_lng"], as_index=False)["n"].sum().sort_values("n")   # one point per cell
    fig, ax = plt.subplots(figsize=(W_IN, H_IN), dpi=DPI)
    sc = ax.scatter(g.cell_lng + 0.05, g.cell_lat + 0.05, c=np.log10(g.n), s=1.3, marker="s",
                    linewidths=0, cmap=SEQ, vmin=0, vmax=np.log10(g.n.max()))
    ax.set_xlim(-125.5, -66.5)
    ax.set_ylim(24, 50)
    ax.set_aspect(1 / np.cos(np.radians(38)))
    ax.axis("off")
    hot = pd.read_csv(os.path.join(root, "reports", "metrics", "hotspots.csv"))
    top = hot.drop_duplicates("City").head(3)                   # three densest distinct cities
    spots = [(-125.0, 30.0), (-76.0, 27.6), (-75.5, 31.6)]   # label anchors in open space
    for (_, r), (tx, ty) in zip(top.iterrows(), spots):
        ax.annotate(f"{r.City}", (r.center_lng, r.center_lat), (tx, ty),
                    fontsize=8, color=RED, fontweight="bold", va="center",
                    arrowprops=dict(arrowstyle="-", color=RED, lw=0.6, shrinkA=1, shrinkB=0))
    cax = fig.add_axes([0.03, 0.11, 0.30, 0.032])
    cb = fig.colorbar(sc, cax=cax, orientation="horizontal")
    cb.set_ticks([0, 1, 2, 3, 4])
    cb.set_ticklabels(["1", "10", "100", "1k", "10k"])
    cb.ax.tick_params(labelsize=7, length=2, width=0.4)
    cb.outline.set_linewidth(0.4)
    cb.set_label("accidents per 0.1° cell", fontsize=7.5, labelpad=1)
    fig.subplots_adjust(left=0.01, right=0.99, top=0.99, bottom=0.01)
    fig.savefig(out, dpi=DPI, facecolor="white")
    plt.close(fig)


def fig_trend(root, out):
    d = pd.read_csv(os.path.join(root, "reports", "metrics", "monthly_trend.csv"), parse_dates=["month"])
    fig, ax = plt.subplots(figsize=(W_IN, H_IN), dpi=DPI)
    ax.plot(d.month, d.accidents, color=MUTED, lw=0.8)
    ax.plot(d.month, d.rolling_12m, color=NAVY, lw=1.8)
    ax.set_ylabel("Accidents per month (sample)", fontsize=8)
    ax.grid(axis="y", color=GRID, lw=0.5)
    ax.set_axisbelow(True)
    ax.tick_params(labelsize=8, length=2, width=0.4)
    clean(ax)
    last = d.dropna(subset=["rolling_12m"]).iloc[-1]
    ax.annotate("12-month mean", (last.month, last.rolling_12m), (-52, -34), textcoords="offset points",
                fontsize=8, color=NAVY, fontweight="bold", arrowprops=dict(arrowstyle="-", color=NAVY, lw=0.6))
    peak = d.loc[d.accidents.idxmax()]
    ax.annotate("monthly count", (peak.month, peak.accidents), (-62, -4), textcoords="offset points",
                fontsize=8, color=MUTED, fontweight="bold")
    fig.subplots_adjust(left=0.17, right=0.98, top=0.97, bottom=0.12)
    fig.savefig(out, dpi=DPI, facecolor="white")
    plt.close(fig)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".")
    root = ap.parse_args().root
    assets = os.path.join(root, "poster", "assets")
    os.makedirs(assets, exist_ok=True)
    fig_map(root, os.path.join(assets, "hotspots_map.png"))
    fig_trend(root, os.path.join(assets, "timeseries.png"))
    print("wrote 2 figures to", assets, "(Fig. 3 = poster/assets/streamlit.png from scripts/take_screenshots.py)")
