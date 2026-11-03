r"""Smoke tests for the Streamlit app (Abin Shaji Thomas).  Run:  .venv\Scripts\python.exe -m pytest -q"""
import sys
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "app"
PAGES = [APP / "Home.py"] + sorted((APP / "pages").glob("*.py"))
sys.path.insert(0, str(APP))


@pytest.mark.parametrize("page", PAGES, ids=[p.stem for p in PAGES])
def test_page_loads_without_exception(page):
    at = AppTest.from_file(str(page), default_timeout=120).run()
    assert not at.exception, [e.value for e in at.exception]


def test_predictor_returns_four_probabilities_summing_to_one():
    import utils as U
    from src import modeling as M
    df = U.clean_data(M.feature_columns(with_distance=False) + ["Start_Time"])
    row = U.build_row(U.default_inputs(df), df["Start_Time"].iloc[0])
    proba = U.predict_proba(U.model(), row)
    assert list(proba.index) == [1, 2, 3, 4]
    assert abs(proba.sum() - 1) < 1e-9
    assert ((proba >= 0) & (proba <= 1)).all()


def test_big_data_page_handles_mongodb_down(monkeypatch):
    monkeypatch.setenv("MONGO_URI", "mongodb://127.0.0.1:1")   # nothing listens here
    at = AppTest.from_file(str(APP / "pages" / "6_Big_Data.py"), default_timeout=120).run()
    at.button[0].click().run()
    assert not at.exception
    assert any("not reachable" in w.value for w in at.warning)
