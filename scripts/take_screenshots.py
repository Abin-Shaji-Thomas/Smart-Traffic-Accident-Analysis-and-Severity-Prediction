"""Screenshot every page of the running Streamlit app (Abin Shaji Thomas).

Start the app first (streamlit run app/Home.py), then:
    .venv\\Scripts\\python.exe scripts\\take_screenshots.py [--url http://localhost:8501]
Writes docs/screenshots/<page>.png (viewport 1440 x 900, top of each page) and poster/assets/streamlit.png
(the Machine Learning page, used as Fig. 3 on the poster).
"""
import argparse
import shutil
import time
from pathlib import Path

from PIL import Image
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "screenshots"
PAGES = {"home": "", "dataset_and_cleaning": "Dataset_and_Cleaning", "eda": "EDA",
         "maps_and_hotspots": "Maps_and_Hotspots", "machine_learning": "Machine_Learning",
         "severity_predictor": "Severity_Predictor", "big_data": "Big_Data"}


def main(url: str) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1440, "height": 900}, device_scale_factor=1)
        for name, path in PAGES.items():
            t0 = time.time()
            page.goto(f"{url}/{path}", wait_until="networkidle")
            page.wait_for_selector("h1", timeout=60_000)
            page.wait_for_function("!document.querySelector('[data-testid=\"stStatusWidget\"]')", timeout=60_000)
            page.wait_for_timeout(2500 if name == "maps_and_hotspots" else 1200)   # let charts and map tiles draw
            file = OUT / f"{name}.png"
            page.screenshot(path=str(file))
            img = Image.open(file).convert("RGB")
            img = img.quantize(colors=256, method=Image.Quantize.MEDIANCUT)   # keep the PNGs small
            img.save(file, optimize=True)
            print(f"{name:22s} {time.time() - t0:4.1f} s  {file.stat().st_size / 1e3:.0f} kB")
        browser.close()
    (ROOT / "poster" / "assets").mkdir(parents=True, exist_ok=True)
    shutil.copy(OUT / "machine_learning.png", ROOT / "poster" / "assets" / "streamlit.png")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default="http://localhost:8501")
    main(ap.parse_args().url)
