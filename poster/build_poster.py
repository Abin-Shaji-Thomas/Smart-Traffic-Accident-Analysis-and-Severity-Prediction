#!/usr/bin/env python3
"""
Build the A3 (297 x 420 mm) project poster from the Karunya Global Showcase template.

Every result number on the poster is read from a facts file (poster_facts.json) that
is generated from the real project run. Anything missing is printed as a yellow
highlighted [fill] marker so it can never be mistaken for a real result.

Usage:
  python build_poster.py --template KGS_2026_-_Poster_Design_Template.pptx \
      --facts poster_facts.json --root . --out Accident_Poster_A3.pptx
"""
import argparse
import json
import os
import tempfile

from lxml import etree
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.dml import MSO_LINE
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, MSO_AUTO_SIZE, PP_ALIGN
from pptx.oxml.ns import qn
from pptx.util import Mm, Pt

FONT = "Times New Roman"
INK = RGBColor(0x14, 0x1B, 0x2D)
NAVY = RGBColor(0x1F, 0x2A, 0x44)
RED = RGBColor(0xC1, 0x1B, 0x2F)
GREY = RGBColor(0x6B, 0x72, 0x80)
PALE = RGBColor(0xEE, 0xF2, 0xFA)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)

A3_W, A3_H = 297.0, 420.0
REPO_URL = "https://github.com/Abin-Shaji-Thomas/Smart-Traffic-Accident-Analysis-and-Severity-Prediction"


# ----------------------------------------------------------------- text helpers
def _highlight(run):
    rPr = run._r.get_or_add_rPr()
    hl = etree.Element(qn("a:highlight"))
    etree.SubElement(hl, qn("a:srgbClr")).set("val", "FFFF00")
    fill = rPr.find(qn("a:solidFill"))
    if fill is not None:
        fill.addnext(hl)
    else:
        rPr.insert(0, hl)


def add_parts(p, parts, size, color=INK, bold=False):
    """parts: str | (text, flags) where flags may contain 'b' (bold) and/or 'ph' (placeholder)."""
    if isinstance(parts, (str, tuple)):
        parts = [parts]
    for part in parts:
        text, flags = (part, "") if isinstance(part, str) else part
        r = p.add_run()
        r.text = text
        f = r.font
        f.size = Pt(size)
        f.bold = bold or ("b" in flags) or ("ph" in flags)
        f.name = FONT
        f.color.rgb = color
        if "ph" in flags:
            _highlight(r)


def set_bullet(p, char="•", indent_mm=4.0):
    pPr = p._p.get_or_add_pPr()
    pPr.set("marL", str(int(Mm(indent_mm))))
    pPr.set("indent", str(-int(Mm(indent_mm))))
    for tag in ("a:buNone", "a:buChar", "a:buAutoNum"):
        for el in pPr.findall(qn(tag)):
            pPr.remove(el)
    etree.SubElement(pPr, qn("a:buChar")).set("char", char)


def textbox(slide, x, y, w, h, paras, size=13, bullets=True, anchor=MSO_ANCHOR.TOP,
            align=None, color=INK, space_after=4):
    s = slide.shapes.add_textbox(Mm(x), Mm(y), Mm(w), Mm(h))
    tf = s.text_frame
    tf.word_wrap = True
    tf.auto_size = MSO_AUTO_SIZE.NONE
    tf.margin_left = tf.margin_right = Mm(1.5)
    tf.margin_top = tf.margin_bottom = Mm(0.8)
    tf.vertical_anchor = anchor
    for i, para in enumerate(paras):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.line_spacing = 1.0
        p.space_after = Pt(space_after)
        if align is not None:
            p.alignment = align
        add_parts(p, para, size, color=color)
        if bullets:
            set_bullet(p)
    return s


def replace_text(shape, parts, size, bold=False, color=INK):
    """Re-write text of an existing template shape, keeping its fill / alignment."""
    tf = shape.text_frame
    tf.word_wrap = True
    tf.auto_size = MSO_AUTO_SIZE.NONE
    for p in tf.paragraphs[1:]:
        p._p.getparent().remove(p._p)
    p = tf.paragraphs[0]
    for child in list(p._p):
        if child.tag in (qn("a:r"), qn("a:br"), qn("a:fld")):
            p._p.remove(child)
    add_parts(p, parts, size, color=color, bold=bold)


def delete(shape):
    el = shape._element
    el.getparent().remove(el)


def ph(label):
    return (f"[{label}]", "ph")


# ------------------------------------------------------------- picture / frames
def fit_picture(slide, path, x, y, w, h):
    from PIL import Image

    with Image.open(path) as im:
        iw, ih = im.size
    scale = min(w / iw, h / ih)
    pw, ph_ = iw * scale, ih * scale
    slide.shapes.add_picture(path, Mm(x + (w - pw) / 2), Mm(y + (h - ph_) / 2), Mm(pw), Mm(ph_))


def figure_slot(slide, root, rel_path, x, y, w, h, caption, missing_label):
    path = os.path.join(root, rel_path) if rel_path else None
    frame = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Mm(x), Mm(y), Mm(w), Mm(h))
    frame.fill.solid()
    frame.fill.fore_color.rgb = PALE
    frame.line.color.rgb = GREY
    frame.line.width = Pt(0.75)
    if path and os.path.exists(path):
        frame.line.fill.background()
        fit_picture(slide, path, x + 0.5, y + 0.5, w - 1, h - 1)
    else:
        frame.line.dash_style = MSO_LINE.DASH
        tf = frame.text_frame
        tf.word_wrap = True
        tf.vertical_anchor = MSO_ANCHOR.MIDDLE
        p = tf.paragraphs[0]
        p.alignment = PP_ALIGN.CENTER
        add_parts(p, ph(missing_label), 12)
    textbox(slide, x, y + h + 0.5, w, 6, [[(caption, "b")]], size=11, bullets=False,
            align=PP_ALIGN.CENTER, color=NAVY)


# ------------------------------------------------------------------- formatters
def fmt_int(v):
    return f"{int(v):,}"


def fmt_acc(v):
    v = float(v)
    return f"{v:.1f}%" if v > 1 else f"{v * 100:.1f}%"


def fmt_dec(v):
    return f"{float(v):.3f}"


def get(d, *keys):
    for k in keys:
        if isinstance(d, dict) and d.get(k) not in (None, "", []):
            d = d[k]
        else:
            return None
    return d


# ------------------------------------------------------------------------ build
def build(template, facts_path, root, out):
    facts = {}
    if facts_path and os.path.exists(facts_path):
        with open(facts_path, encoding="utf-8") as fh:
            facts = json.load(fh)

    prs = Presentation(template)
    slide = prs.slides[0]
    fx = Mm(A3_W) / prs.slide_width
    fy = Mm(A3_H) / prs.slide_height
    prs.slide_width, prs.slide_height = Mm(A3_W), Mm(A3_H)

    # Scale every template shape from A0 down to A3 (same A-series proportions).
    for sh in slide.shapes:
        if sh.left is None:
            continue
        sh.left, sh.top = int(sh.left * fx), int(sh.top * fy)
        sh.width, sh.height = int(sh.width * fx), int(sh.height * fy)

    by_name = {sh.name: sh for sh in slide.shapes}
    title = by_name["Rounded Rectangle 1"]
    h_intro = by_name["Google Shape;54;p13"]
    h_methods = by_name["Google Shape;62;p13"]
    h_results = by_name["Google Shape;63;p13"]
    h_disc = by_name["Google Shape;67;p13"]
    team = by_name["Google Shape;58;p13"]
    sup = by_name["Google Shape;69;p13"]

    for name in ("Google Shape;59;p13", "Google Shape;60;p13", "Google Shape;61;p13",
                 "Google Shape;64;p13", "Google Shape;65;p13", "Google Shape;66;p13",
                 "Google Shape;68;p13"):
        delete(by_name[name])

    # --- header block --------------------------------------------------------
    title.left, title.top, title.width, title.height = Mm(2), Mm(37), Mm(216), Mm(12)
    replace_text(title, "Smart Traffic Accident Analysis and Severity Prediction", 23, color=INK)

    members = facts.get("team") or []
    if members:
        parts = []
        for i, m in enumerate(members):
            if i:
                parts.append("   |   ")
            parts.append(m.get("name", ""))
            reg = m.get("reg_no")
            parts.append(f" ({reg})" if reg else "")
            if not reg:
                parts.append(" ")
                parts.append(ph("Reg. No."))
    else:
        parts = ["Abin Shaji Thomas ", ph("Reg. No."), "   |   ",
                 ph("Team member 2 + Reg. No. – delete if solo")]
    delete(team)
    delete(sup)
    textbox(slide, 2, 49, 292, 8.5, [parts], size=18, bullets=False, space_after=0)
    textbox(slide, 2, 57, 292, 8.5,
            [["Supervisor: ", facts.get("supervisor") or ph("Faculty name, designation")]],
            size=18, bullets=False, space_after=0)
    textbox(slide, 2, 65, 292, 8,
            [["Karunya Institute of Technology and Sciences  |  Course: Data Science Ecosystem (25CS305)"]],
            size=14.5, bullets=False, color=NAVY, space_after=0)

    # --- section headers -----------------------------------------------------
    hdr_size = 20
    for shp, text, x, w in ((h_intro, "Introduction", 6, 134), (h_methods, "Methods", 149, 139)):
        shp.left, shp.top, shp.width, shp.height = Mm(x), Mm(78), Mm(w), Mm(9.5)
        replace_text(shp, text, hdr_size, bold=True)
    for shp, text, y in ((h_results, "Results", 166), (h_disc, "Discussions", 319.5)):
        shp.left, shp.top, shp.width, shp.height = Mm(6), Mm(y), Mm(285), Mm(9.5)
        replace_text(shp, text, hdr_size, bold=True)

    # --- introduction --------------------------------------------------------
    total = facts.get("total_rows")
    total_txt = f"{fmt_int(total)}" if total else None
    dr = facts.get("date_range") or [None, None]
    intro = [
        [("Problem: ", "b"), "road accidents block traffic and slow emergency response; estimating early "
         "how much an accident will disrupt traffic helps target police and recovery crews."],
        [("Data: ", "b"), "US Accidents (Moosavi et al., Kaggle): "] + ([total_txt] if total_txt else [ph("rows")]) +
        [" accident records, "] + ([f"{dr[0]} to {dr[1]}"] if dr[0] else [ph("date range")]) +
        [", with GPS, weather, time and road-feature attributes."],
        [("Objectives: ", "b"), "clean the records and handle missing GPS values; measure weather "
         "influence; find accident hotspots; run correlation analysis; predict crash Severity (1–4)."],
        [("Scope: ", "b"), "five modules: Data Science Concepts, Exploratory Data Analysis, Data "
         "Visualization, Machine Learning, Big Data Analytics."],
    ]
    textbox(slide, 6, 89, 138, 76, intro, size=13.5)

    # --- methods -------------------------------------------------------------
    sample = facts.get("sample_rows")
    sample_txt = [f"stratified sample of {fmt_int(sample)} rows"] if sample else \
        ["stratified sample of ", ph("sample size"), " rows"]
    methods = [
        [("Ingest: ", "b"), (f"{facts['raw_size_gb']} GB CSV" if facts.get("raw_size_gb") else "raw CSV") + " read in chunks; "]
        + sample_txt + [" (random_state = 42)."],
        [("Clean & features: ", "b"), "duplicates and impossible values removed, outliers winsorized, End GPS "
         "imputed from Start, weather by State + month."],
        [("Models: ", "b"), "Decision Tree, Random Forest, Logistic Regression, HistGradientBoosting; "
         "class-balanced, stratified 80/20 split, CV tuning."],
        [("Big data: ", "b"), "MongoDB (2dsphere) and Hadoop-style MapReduce, cross-checked."],
    ]
    textbox(slide, 149, 89, 139, 53, methods, size=12.5, space_after=3)

    # pipeline diagram (native shapes so it stays editable and sharp)
    labels = ["1\nData Science\nConcepts", "2\nEDA", "3\nVisuali-\nzation", "4\nMachine\nLearning",
              "5\nBig Data\nAnalytics"]
    bw, bh, gap, by0 = 24.0, 14.0, 4.75, 144.5
    for i, lab in enumerate(labels):
        bx = 149 + i * (bw + gap)
        box = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Mm(bx), Mm(by0), Mm(bw), Mm(bh))
        box.fill.solid()
        box.fill.fore_color.rgb = NAVY if i % 2 == 0 else RED
        box.line.fill.background()
        tf = box.text_frame
        tf.word_wrap = True
        tf.margin_left = tf.margin_right = Mm(0.5)
        tf.margin_top = tf.margin_bottom = Mm(0.3)
        tf.vertical_anchor = MSO_ANCHOR.MIDDLE
        for j, line in enumerate(lab.split("\n")):
            p = tf.paragraphs[0] if j == 0 else tf.add_paragraph()
            p.alignment = PP_ALIGN.CENTER
            p.line_spacing = 0.9
            add_parts(p, line, 12 if j == 0 else 9.5, color=WHITE, bold=(j == 0))
        if i < len(labels) - 1:
            arrow = slide.shapes.add_shape(MSO_SHAPE.RIGHT_ARROW, Mm(bx + bw + 0.4), Mm(by0 + bh / 2 - 2),
                                           Mm(gap - 0.8), Mm(4))
            arrow.fill.solid()
            arrow.fill.fore_color.rgb = GREY
            arrow.line.fill.background()
    textbox(slide, 149, 159.3, 139, 5.5,
            [["CSV \u2192 Parquet \u2192 MongoDB / MapReduce \u2192 ML \u2192 Streamlit dashboard"]],
            size=10.5, bullets=False, align=PP_ALIGN.CENTER, color=GREY)

    # --- results: column 1 (key findings) ------------------------------------
    images = facts.get("images") or {}
    hot = facts.get("top_hotspots") or []
    gps = facts.get("gps") or {}
    miss = ph("fill from run")
    if facts.get("gps_text"):
        gps_parts = [facts["gps_text"]]
    elif gps.get("missing_before") is not None:
        gps_parts = [f"{fmt_int(gps['missing_before'])} records affected; "
                     f"{fmt_int(gps.get('recovered', 0))} recovered via City + State medians, "
                     f"{fmt_int(gps.get('dropped', 0))} dropped."]
    else:
        gps_parts = [miss]
    findings = [
        [("Hotspots (accidents per 0.1\u00b0 cell): ", "b")] + ([", ".join(f"{h['label']} ({fmt_int(h['count'])})" for h in hot[:4])] if hot else [miss]),
        [("Weather: ", "b")] + ([facts["weather_insight"]] if facts.get("weather_insight") else [miss]),
        [("Time pattern: ", "b")] + ([facts["time_insight"]] if facts.get("time_insight") else [miss]),
        [("Predictors: ", "b")] + ([facts["correlation_insight"]] if facts.get("correlation_insight") else [miss]),
        [("Missing GPS: ", "b")] + gps_parts,
    ]
    textbox(slide, 6, 176, 89, 138, [[("Key findings", "b")]], size=15, bullets=False, color=RED)
    textbox(slide, 6, 184, 89, 130, findings, size=14, space_after=7)

    # --- results: column 2 (figures) -----------------------------------------
    figure_slot(slide, root, images.get("heatmap"), 103, 176, 89, 63,
                (facts.get("captions") or {}).get("fig1", "Fig. 1  Accident density heatmap"), "insert accident heatmap image")
    figure_slot(slide, root, images.get("timeseries"), 103, 247, 89, 63,
                (facts.get("captions") or {}).get("fig2", "Fig. 2  Monthly accident trend"), "insert time-series image")

    # --- results: column 3 (models, big data, dashboard) ---------------------
    textbox(slide, 200, 176, 90, 8, [[("Model comparison (test set)", "b")]], size=15, bullets=False, color=RED)
    models = facts.get("models") or []
    default_names = ["Decision Tree", "Random Forest", "Logistic Regression", "HistGradientBoosting", "Majority baseline"]
    rows = models if models else [{"model": n} for n in default_names]
    nrows = len(rows) + 1
    tbl_shape = slide.shapes.add_table(nrows, 4, Mm(200), Mm(184.5), Mm(90), Mm(7 * nrows))
    tbl = tbl_shape.table
    for ci, wmm in enumerate((39, 17, 17, 17)):
        tbl.columns[ci].width = Mm(wmm)
    for ri in range(nrows):
        tbl.rows[ri].height = Mm(7)
    heads = ["Model", "Accuracy", "Macro-F1", "ROC-AUC"]
    best = facts.get("best_model")

    def cell(ri, ci, parts, head=False, strong=False):
        c = tbl.cell(ri, ci)
        c.fill.solid()
        c.fill.fore_color.rgb = NAVY if head else (PALE if ri % 2 == 0 else WHITE)
        c.margin_left = c.margin_right = Mm(1)
        c.margin_top = c.margin_bottom = Mm(0.5)
        c.vertical_anchor = MSO_ANCHOR.MIDDLE
        p = c.text_frame.paragraphs[0]
        p.alignment = PP_ALIGN.LEFT if ci == 0 else PP_ALIGN.CENTER
        add_parts(p, parts, 10 if head else 10.5, color=WHITE if head else INK, bold=head or strong)

    for ci, htxt in enumerate(heads):
        cell(0, ci, htxt, head=True)
    for ri, row in enumerate(rows, start=1):
        strong = bool(best) and row.get("model") == best
        cell(ri, 0, row.get("model", ""), strong=strong)
        for ci, (key, fn) in enumerate((("accuracy", fmt_acc), ("macro_f1", fmt_dec), ("roc_auc", fmt_dec)), start=1):
            v = row.get(key)
            na = row.get("model") == "Majority baseline"      # ROC-AUC is undefined for a constant prediction
            cell(ri, ci, fn(v) if v is not None else ("n/a" if na else ("—", "ph")), strong=strong)

    mongo = facts.get("mongo") or {}
    mr = facts.get("mapreduce_matches_pandas")
    mongo_txt = [f"{fmt_int(mongo['documents'])} documents, 2dsphere index; "
                 f"{mongo['queries']} queries timed with / without indexes."] if mongo.get("documents") else \
        [ph("MongoDB document count")]
    mr_txt = (["4 splits, 4 maps, 2 reducers; all 3 jobs match pandas and MongoDB."] if mr is True else
              ["MapReduce results differ from pandas – see report."] if mr is False else
              [ph("MapReduce check result")])
    big = [[("MongoDB: ", "b")] + mongo_txt, [("MapReduce: ", "b")] + mr_txt]
    big_y = 184.5 + 7 * nrows + 3
    textbox(slide, 200, big_y, 90, 30, big, size=11.5, space_after=2)

    dash_y = max(247.0, big_y + 29)
    figure_slot(slide, root, images.get("dashboard"), 200, dash_y, 90, 310 - dash_y,
                (facts.get("captions") or {}).get("fig3", "Fig. 3  Streamlit dashboard"), "insert dashboard screenshot")

    # --- discussion ----------------------------------------------------------
    if best and models:
        brow = next((m for m in models if m.get("model") == best), {})
        parts = [f"{best} gave the best result"]
        if brow.get("macro_f1") is not None:
            parts.append(f" (macro-F1 {fmt_dec(brow['macro_f1'])}")
            if brow.get("accuracy") is not None:
                parts.append(f", accuracy {fmt_acc(brow['accuracy'])}")
            parts.append(")")
        parts.append(".")
        concl_main = ["".join(parts)]
    else:
        concl_main = [ph("best model and score")]
    conclusion = [concl_main] + ([[facts["conclusion"]]] if facts.get("conclusion") else [])
    limits = [
        ["Severity classes are imbalanced, so macro-F1 is reported next to accuracy."],
        ["Models were trained on a sample, not on all records."],
        ["Weather is taken from the nearest weather station, so it is approximate."],
    ]
    future = [
        ["Real-time severity alerts from streaming data."],
        ["Spark MLlib on all records instead of a sample."],
        ["Add road-network and traffic-volume features."],
    ]
    cols = ((6, 77, "Conclusion", conclusion), (86, 77, "Limitations", limits), (166, 77, "Future work", future))
    for x, w, head, paras in cols:
        textbox(slide, x, 330, w, 7, [[(head, "b")]], size=15, bullets=False, color=RED)
        textbox(slide, x, 337, w, 50, paras, size=13)

    # QR code to the repository
    try:
        import qrcode

        qr_path = os.path.join(tempfile.gettempdir(), "poster_repo_qr.png")
        qrcode.make(REPO_URL, box_size=10, border=1).save(qr_path)
        slide.shapes.add_picture(qr_path, Mm(251), Mm(333), Mm(36), Mm(36))
        textbox(slide, 245, 370, 48, 14, [["Scan for the code and results"]], size=11, bullets=False,
                align=PP_ALIGN.CENTER, color=NAVY)
    except Exception:
        pass

    textbox(slide, 6, 389.5, 285, 6,
            [["Dataset: Moosavi et al., US Accidents (Kaggle), CC BY-NC-SA 4.0.   Code: "
              "github.com/Abin-Shaji-Thomas/Smart-Traffic-Accident-Analysis-and-Severity-Prediction"]],
            size=9.5, bullets=False, align=PP_ALIGN.CENTER, color=GREY)

    cp = prs.core_properties
    cp.author = cp.last_modified_by = "Abin Shaji Thomas"
    cp.title = "Smart Traffic Accident Analysis and Severity Prediction"
    prs.save(out)
    print("saved", out, f"({A3_W:.0f} x {A3_H:.0f} mm)")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--template", required=True)
    ap.add_argument("--facts", default="poster_facts.json")
    ap.add_argument("--root", default=".")
    ap.add_argument("--out", default="Accident_Poster_A3.pptx")
    a = ap.parse_args()
    build(a.template, a.facts, a.root, a.out)
