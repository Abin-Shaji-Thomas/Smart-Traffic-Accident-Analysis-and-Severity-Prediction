"""Consistent chart styling for all notebooks (Abin Shaji Thomas).

Colour rules: Severity is ordinal -> one blue ramp light-to-dark; weather groups and other
categories -> fixed categorical order; correlations -> blue / neutral / orange diverging map.
"""
from __future__ import annotations

import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap

INK = "#0b0b0b"
INK2 = "#52514e"
MUTED = "#898781"
GRID = "#e1e0d9"
AXIS = "#c3c2b7"
SURFACE = "#fcfcfb"

CATEGORICAL = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#6250d6", "#e34948"]
SEVERITY = {1: "#9ec5f4", 2: "#5598e7", 3: "#256abf", 4: "#0d366b"}
WEATHER_COLORS = dict(zip(["Clear", "Cloudy", "Rain", "Snow", "Fog/Haze", "Storm", "Other"], CATEGORICAL))
PRIMARY = CATEGORICAL[0]
ACCENT = CATEGORICAL[1]

SEQ_CMAP = LinearSegmentedColormap.from_list("seq_blue", ["#f4f8fd", "#cde2fb", "#86b6ef", "#3987e5", "#1c5cab", "#0d366b"])
DIV_CMAP = LinearSegmentedColormap.from_list("div_blue_orange", ["#1c5cab", "#86b6ef", "#f0efec", "#f3a582", "#c2410c"])


def apply_style() -> None:
    mpl.rcParams.update({
        "figure.facecolor": SURFACE, "axes.facecolor": SURFACE, "savefig.facecolor": SURFACE,
        "axes.edgecolor": AXIS, "axes.labelcolor": INK2, "axes.titlecolor": INK,
        "axes.titlesize": 12, "axes.titleweight": "bold", "axes.titlelocation": "left",
        "axes.labelsize": 10, "axes.grid": True, "axes.grid.axis": "y", "grid.color": GRID,
        "grid.linewidth": 0.6, "axes.spines.top": False, "axes.spines.right": False,
        "xtick.color": MUTED, "ytick.color": MUTED, "xtick.labelcolor": INK2, "ytick.labelcolor": INK2,
        "font.size": 10, "legend.frameon": False, "lines.linewidth": 2, "axes.prop_cycle": mpl.cycler(color=CATEGORICAL),
        "figure.dpi": 100, "savefig.dpi": 150, "savefig.bbox": "tight",
    })


def save(fig, path, dpi: int = 150) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=dpi)
    plt.show()
    plt.close(fig)
