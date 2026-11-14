"""ZudRisk pitch deck: 7 slides, 16:9, built from one spec into a PowerPoint file and an HTML twin.

The .pptx carries Morph transitions with a Fade fallback (older PowerPoint, Google Slides and LibreOffice show the fade).
The HTML twin draws the same boxes at the same positions so the deck can be checked, and printed to PDF, on a machine
without PowerPoint. Run:  uv run --system-certs --no-project --with python-pptx --with pillow python docs/pitch/build.py
Screenshots come from docs/pitch/shots.mjs (the live site, in English)."""
import copy
import html
import json
from pathlib import Path

from lxml import etree
from PIL import Image
from pptx import Presentation
from pptx.chart.data import CategoryChartData
from pptx.dml.color import RGBColor
from pptx.enum.chart import XL_CHART_TYPE
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.util import Emu, Inches, Pt

HERE = Path(__file__).parent
IMG = HERE / "img"
ROOT = HERE.parent.parent
W, H = 13.333, 7.5

INK, WHITE, MUTED, LIGHT = "1D2433", "FFFFFF", "5B6475", "F3F5F8"
ACCENT, RED, ORANGE, SOFT = "2F6FD6", "BD0026", "FD8D3C", "C9D3E6"
FONT = "Calibri"


def crop(src, dst, box):
    Image.open(IMG / src).crop(box).save(IMG / dst)
    return IMG / dst


# map crops around Mongolia (the screenshots are 1890 x 1300 px)
MAPS = {
    "outlook": crop("outlook.png", "c_outlook.png", (340, 400, 1540, 985)),
    "dzud": crop("dzud2010.png", "c_dzud.png", (340, 400, 1540, 985)),
    "green": crop("greenness.png", "c_green.png", (340, 400, 1540, 985)),
    "popup": crop("popup2010.png", "c_popup.png", (470, 120, 1300, 1000)),
}
RATIO = 1200 / 585

hist = json.loads((ROOT / "site/data/history.json").read_text(encoding="utf-8"))
LOSSES = [(w.replace("-", "/")[2:], p) for w, p in zip(hist["winters"], hist["national_pct"]) if p is not None]


def T(name, x, y, w, h, runs, size=16, color=INK, bold=False, align="l", anchor="t", italic=False):
    """A text box; runs is a string or a list of paragraphs, each a string or a list of (text, overrides)."""
    return dict(kind="text", name=name, x=x, y=y, w=w, h=h, runs=runs, size=size, color=color, bold=bold, align=align,
                anchor=anchor, italic=italic)


def R(name, x, y, w, h, fill, shape="rect", alpha=None, radius=False):
    return dict(kind="shape", name=name, x=x, y=y, w=w, h=h, fill=fill, shape=shape, alpha=alpha, radius=radius)


def I(name, x, y, w, h, path):
    return dict(kind="image", name=name, x=x, y=y, w=w, h=h, path=path)


def brand(dark):
    return T("!!brand", 0.6, 0.32, 3.0, 0.35, [[("Zud", {}), ("Risk", {"color": ORANGE})]], size=14, bold=True,
             color=WHITE if dark else INK)


def title(text, dark=False):
    return T("!!title", 0.6, 0.72, 11.6, 0.9, text, size=34, bold=True, color=WHITE if dark else INK)


mh = 6.0 / RATIO
SLIDES = [
    dict(dark=True, transition="fade", items=[
        R("!!orb", 6.6, -0.9, 7.6, 7.6, ACCENT, "oval", alpha=28),
        I("!!map", 6.2, 1.75, 6.6, 6.6 / RATIO, MAPS["dzud"]),
        brand(True),
        T("!!title", 0.6, 1.9, 5.6, 2.0, "Watching dzud coming from space", size=44, bold=True, color=WHITE),
        T("sub", 0.6, 4.05, 5.4, 1.0, "Soum-level dzud risk for Mongolia from Earth observation trends", size=20, color=SOFT),
        T("event", 0.6, 6.45, 9.0, 0.5, "NASA Space Apps Challenge 2026  ·  Ulaanbaatar  ·  Be An Earth System Trend Detective!",
          size=12, color="9AA6BD"),
    ], notes="In the winter of 2009/10, Mongolia lost more than a fifth of its livestock, 21.7 percent, to a dzud: deep "
             "snow and extreme cold after a dry summer. A dzud does not arrive overnight. It builds up over months, in "
             "data we can see from space. We asked: can Earth observation trends tell us which soums are heading into trouble?"),
    dict(dark=False, transition="morph", items=[
        R("!!orb", 11.7, 0.25, 1.2, 1.2, ORANGE, "oval", alpha=30),
        brand(False),
        title("A slow disaster that took a fifth of the herd"),
        T("stat", 0.6, 2.05, 4.0, 1.3, "21.7%", size=72, bold=True, color=RED),
        T("stat_l", 0.6, 3.45, 3.9, 1.4, "of Mongolia's adult livestock died in the 2009/10 dzud. In 2023/24 it was 13.8%.",
          size=18, color=INK),
        T("why", 0.6, 5.05, 3.9, 1.2, "Deep snow and cold after a dry summer: herds starve over weeks, not hours.",
          size=15, color=MUTED, italic=True),
        dict(kind="chart", name="losses", x=4.9, y=1.85, w=7.9, h=4.75, data=LOSSES, hi={"09/10": RED, "23/24": ORANGE}),
        T("src", 4.9, 6.65, 7.9, 0.4, "Adult livestock lost by winter, % (NSO, aimag totals excl. Ulaanbaatar)", size=11, color=MUTED),
    ], notes="Losses come in waves. 2000/01 and 2009/10 each took about a fifth of the national herd, 2023/24 almost "
             "14 percent. Between them, most winters lose 1 to 4 percent."),
    dict(dark=False, transition="morph", items=[
        R("!!orb", 9.55, 2.0, 3.2, 3.2, ORANGE, "oval", alpha=22),
        brand(False),
        title("Four signals, one risk score per soum"),
        *[c for i, (head, body) in enumerate([
            ("Snow depth", "Deepest monthly snow, November to March · ERA5-Land"),
            ("Winter cold", "Mean air temperature, November to February · ERA5-Land"),
            ("Summer pasture", "July–August greenness · NASA MODIS NDVI"),
            ("Grazing pressure", "Sheep units per km² of pasture · NSO census, EIC pasture map"),
        ]) for c in (
            R(f"card{i}", 0.6 + (i % 2) * 4.3, 1.95 + (i // 2) * 2.35, 4.05, 2.1, LIGHT, "rect", radius=True),
            R(f"num{i}", 0.85 + (i % 2) * 4.3, 2.2 + (i // 2) * 2.35, 0.55, 0.55, ACCENT, "oval"),
            T(f"numt{i}", 0.85 + (i % 2) * 4.3, 2.2 + (i // 2) * 2.35, 0.55, 0.55, str(i + 1), size=16, bold=True,
              color=WHITE, align="c", anchor="m"),
            T(f"head{i}", 1.6 + (i % 2) * 4.3, 2.2 + (i // 2) * 2.35, 2.9, 0.55, head, size=20, bold=True, anchor="m"),
            T(f"body{i}", 0.85 + (i % 2) * 4.3, 3.0 + (i // 2) * 2.35, 3.6, 0.9, body, size=15, color=MUTED),
        )],
        T("one", 9.55, 2.75, 3.2, 1.0, "1 score", size=36, bold=True, color=INK, align="c", anchor="m"),
        T("one_l", 9.55, 3.65, 3.2, 1.0, "339 soums × 25 winters, plus a monthly outlook", size=15, color=INK, align="c"),
        T("w", 9.0, 5.55, 4.3, 0.9, "Weights fixed from the literature before any test", size=13, color=MUTED, align="c", italic=True),
    ], notes="ZudRisk scores dzud risk for all 339 soums. It combines four signals: snow depth and winter cold from "
             "ERA5-Land, summer pasture greenness from NASA's MODIS NDVI, and grazing pressure from the national livestock "
             "census over each soum's pasture area. We compute it for 25 past winters, and as a live outlook for this "
             "winter that updates every month."),
    dict(dark=False, transition="morph", items=[
        R("!!orb", 12.2, 6.45, 0.7, 0.7, ORANGE, "oval", alpha=30),
        brand(False),
        title("Same map, two winters"),
        T("cap_a", 0.6, 1.75, 6.0, 0.5, [[("2026/27 outlook", {"bold": True}), (" · October, before any snow", {})]], size=16),
        I("map_a", 0.6, 2.3, 6.0, mh, MAPS["outlook"]),
        T("cap_b", 6.73, 1.75, 6.0, 0.5, [[("2009/10", {"bold": True, "color": RED}), (" · the dzud winter", {})]], size=16),
        I("!!map", 6.73, 2.3, 6.0, mh, MAPS["dzud"]),
        T("leg", 0.6, 2.3 + mh + 0.25, 12.1, 0.5,
          "Darker red: a higher chance that 5% or more of the herd dies. The model put the 2009/10 losses in the west and centre.",
          size=15, color=MUTED),
    ], notes="Live demo. This is this winter's outlook, as of October, before any snow: mostly yellow, honestly, because "
             "the winter has not started. Now 2009/10: the model turns the west and centre red, where the losses happened. "
             "For each soum the popup gives the chance that 5 percent or more of the herd dies, and which signals drove it."),
    dict(dark=False, transition="morph", items=[
        R("!!orb", 11.0, 5.2, 2.0, 2.0, "238B45", "oval", alpha=22),
        brand(False),
        title("The trend detective: 25 years of summer greenness"),
        I("!!map", 0.6, 1.85, 7.6, 7.6 / RATIO, MAPS["green"]),
        T("t1", 8.65, 1.95, 4.2, 1.3, [[("What  ", {"bold": True, "color": INK}),
                                        ("Theil–Sen slope of July–August NDVI per soum, every summer since 2000", {})]],
          size=16, color=MUTED),
        T("t2", 8.65, 3.35, 4.2, 1.3, [[("Why  ", {"bold": True, "color": INK}),
                                        ("browning pasture leaves herds weaker before the snow", {})]], size=16, color=MUTED),
        T("t3", 8.65, 4.75, 4.2, 1.0, [[("Data  ", {"bold": True, "color": INK}), ("NASA MODIS MOD13C2", {})]],
          size=16, color=MUTED),
        *[R(f"g{i}", 0.6 + i * 0.55, 1.85 + 7.6 / RATIO + 0.25, 0.5, 0.22, c)
          for i, c in enumerate(["A6611A", "F5F5F5", "C7E9C0", "74C476", "238B45"])],
        T("gl", 3.5, 1.85 + 7.6 / RATIO + 0.15, 4.7, 0.42, "browning  →  strong greening, per decade", size=12, color=MUTED,
          anchor="m"),
    ], notes="And here is the long-term trend: 25 years of summer greenness per soum, from NASA MODIS. Where pasture is "
             "browning, a dzud hits harder. It is a sign of desertification, not the official desertification map: "
             "NDVI cannot tell rain from grazing."),
    dict(dark=False, transition="morph", items=[
        R("!!orb", 0.6, 5.35, 1.1, 1.1, ORANGE, "oval", alpha=30),
        brand(False),
        title("Does it work?"),
        *[c for i, (big, color, small) in enumerate([
            ("0.60", ACCENT, "Spearman ρ between our risk score and real losses, pre-registered winters (n = 1,683 soum-winters)"),
            ("58%", RED, "of soum-winters we rated very high lost 5% or more of the herd, against 15% overall"),
            ("0.23 → 0.64", INK, "the ranking sharpens as the winter unfolds: October to December outlook"),
        ]) for c in (
            R(f"sc{i}", 0.6 + i * 4.15, 1.95, 3.9, 2.95, LIGHT, "rect", radius=True),
            T(f"sb{i}", 0.85 + i * 4.15, 2.2, 3.45, 1.2, big, size=48 if i < 2 else 40, bold=True, color=color, anchor="m"),
            T(f"ss{i}", 0.85 + i * 4.15, 3.5, 3.45, 1.3, small, size=16, color=INK),
        )],
        T("lim", 2.0, 5.55, 10.7, 0.9, [[("Limits we state openly: ", {"bold": True, "color": INK}),
                                          ("snow comes from a model, not pasture measurements; the October outlook is weak; "
                                           "this is not an official warning.", {})]], size=14, color=MUTED),
    ], notes="Did it work? Across pre-registered winters, our risk ranking matched real losses with a Spearman "
             "correlation of 0.6. In soums we rated very high, losses of 5 percent or more followed 58 percent of the time, "
             "against 15 percent overall. We also say openly what we cannot do: the October outlook is weak, and snow "
             "comes from a model."),
    dict(dark=True, transition="fade", items=[
        R("!!orb", -1.6, 3.6, 6.0, 6.0, ACCENT, "oval", alpha=28),
        brand(True),
        T("!!title", 0.6, 0.95, 11.6, 1.0, "Built for those who act before the snow", size=40, bold=True, color=WHITE),
        T("who", 0.6, 2.25, 7.4, 2.4, [
            [("Soum and aimag governors", {"bold": True, "color": WHITE}), ("  where to stock hay and fodder", {})],
            [("NEMA", {"bold": True, "color": WHITE}), ("  where to send support first", {})],
            [("Aid agencies", {"bold": True, "color": WHITE}), ("  where to pre-position feed and cash", {})],
        ], size=20, color=SOFT),
        T("url", 5.0, 5.0, 7.8, 0.8, "sarul72.github.io/ZudRisk", size=36, bold=True, color="8FB4FF", align="r"),
        T("open", 5.0, 5.85, 7.8, 0.5, "Open code and data · github.com/Sarul72/ZudRisk", size=14, color="9AA6BD", align="r"),
    ], notes="Dzud is a slow disaster we can watch coming from space. ZudRisk turns NASA's Earth observations into a map "
             "a herder, a governor or an aid agency can act on, before the animals die. Thank you."),
]

# ---------- PowerPoint ----------
NS = {"a": "http://schemas.openxmlformats.org/drawingml/2006/main",
      "p": "http://schemas.openxmlformats.org/presentationml/2006/main"}
MORPH = """<mc:AlternateContent xmlns:mc="http://schemas.openxmlformats.org/markup-compatibility/2006"
  xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main">
  <mc:Choice xmlns:p159="http://schemas.microsoft.com/office/powerpoint/2015/09/main" Requires="p159">
    <p:transition xmlns:p14="http://schemas.microsoft.com/office/powerpoint/2010/main" spd="slow" p14:dur="1200"><p159:morph option="byObject"/></p:transition>
  </mc:Choice>
  <mc:Fallback><p:transition spd="slow"><p:fade/></p:transition></mc:Fallback>
</mc:AlternateContent>"""
FADE = '<p:transition xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main" spd="slow"><p:fade/></p:transition>'


def rgb(h):
    return RGBColor.from_string(h)


def add_text(slide, it):
    tb = slide.shapes.add_textbox(Inches(it["x"]), Inches(it["y"]), Inches(it["w"]), Inches(it["h"]))
    tb.name = it["name"]
    tf = tb.text_frame
    tf.word_wrap = True
    for side in ("left", "right", "top", "bottom"):
        setattr(tf, f"margin_{side}", 0)
    tf.vertical_anchor = {"t": MSO_ANCHOR.TOP, "m": MSO_ANCHOR.MIDDLE}[it["anchor"]]
    paras = it["runs"] if isinstance(it["runs"], list) else [it["runs"]]
    for i, para in enumerate(paras):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = {"l": PP_ALIGN.LEFT, "c": PP_ALIGN.CENTER, "r": PP_ALIGN.RIGHT}[it["align"]]
        if i:
            p.space_before = Pt(10)
        for text, o in ([(para, {})] if isinstance(para, str) else para):
            r = p.add_run()
            r.text = text
            f = r.font
            f.name, f.size = FONT, Pt(it["size"])
            f.bold = o.get("bold", it["bold"])
            f.italic = it["italic"]
            f.color.rgb = rgb(o.get("color", it["color"]))


def add_shape(slide, it):
    kind = {"rect": MSO_SHAPE.ROUNDED_RECTANGLE if it["radius"] else MSO_SHAPE.RECTANGLE, "oval": MSO_SHAPE.OVAL}[it["shape"]]
    s = slide.shapes.add_shape(kind, Inches(it["x"]), Inches(it["y"]), Inches(it["w"]), Inches(it["h"]))
    s.name = it["name"]
    s.fill.solid()
    s.fill.fore_color.rgb = rgb(it["fill"])
    s.line.fill.background()
    s.shadow.inherit = False
    if it["radius"]:
        s.adjustments[0] = 0.06
    if it["alpha"] is not None:
        clr = s.fill._xPr.find(".//a:srgbClr", NS)
        etree.SubElement(clr, f"{{{NS['a']}}}alpha").set("val", str(it["alpha"] * 1000))


def add_chart(slide, it):
    cd = CategoryChartData()
    cd.categories = [w for w, _ in it["data"]]
    cd.add_series("Losses %", [v for _, v in it["data"]])
    gf = slide.shapes.add_chart(XL_CHART_TYPE.COLUMN_CLUSTERED, Inches(it["x"]), Inches(it["y"]), Inches(it["w"]),
                                Inches(it["h"]), cd)
    gf.name = it["name"]
    ch = gf.chart
    ch.has_legend = False
    ch.font.name, ch.font.size = FONT, Pt(11)
    ch.font.color.rgb = rgb(MUTED)
    plot = ch.plots[0]
    plot.gap_width = 45
    ser = plot.series[0]
    ser.format.fill.solid()
    ser.format.fill.fore_color.rgb = rgb("B8BFCC")
    for i, (w, v) in enumerate(it["data"]):
        if w in it["hi"]:
            pt = ser.points[i]
            pt.format.fill.solid()
            pt.format.fill.fore_color.rgb = rgb(it["hi"][w])
            pt.data_label.has_text_frame = True
            pt.data_label.text_frame.text = f"{v:.1f}%"
            pt.data_label.font.size, pt.data_label.font.bold = Pt(12), True
            pt.data_label.font.color.rgb = rgb(it["hi"][w])
    va = ch.value_axis
    va.has_major_gridlines = True
    va.major_gridlines.format.line.color.rgb = rgb("E3E6EC")
    va.format.line.fill.background()
    va.maximum_scale = 25
    va.tick_labels.font.size = Pt(11)
    ca = ch.category_axis
    ca.tick_labels.font.size = Pt(10)
    ca.format.line.color.rgb = rgb("B8BFCC")


def build_pptx(path):
    prs = Presentation()
    prs.slide_width, prs.slide_height = Inches(W), Inches(H)
    blank = prs.slide_layouts[6]
    for s in SLIDES:
        slide = prs.slides.add_slide(blank)
        bg = slide.background.fill
        bg.solid()
        bg.fore_color.rgb = rgb(INK if s["dark"] else WHITE)
        for it in s["items"]:
            {"text": add_text, "shape": add_shape, "chart": add_chart,
             "image": lambda sl, i: setattr(sl.shapes.add_picture(str(i["path"]), Inches(i["x"]), Inches(i["y"]),
                                                                 Inches(i["w"]), Inches(i["h"])), "name", i["name"])}[it["kind"]](slide, it)
        slide.notes_slide.notes_text_frame.text = s["notes"]
        sld = slide._element
        tr = etree.fromstring(MORPH if s["transition"] == "morph" else FADE)
        clr = sld.find("p:clrMapOvr", NS)
        (clr.addnext if clr is not None else sld.find("p:cSld", NS).addnext)(tr)
    prs.save(path)


# ---------- HTML twin ----------
def css_text(it):
    jc = {"t": "flex-start", "m": "center"}[it["anchor"]]
    return (f"display:flex;flex-direction:column;justify-content:{jc};font:{'italic ' if it['italic'] else ''}"
            f"{700 if it['bold'] else 400} {it['size']}pt/1.2 {FONT},Arial,sans-serif;color:#{it['color']};"
            f"text-align:{ {'l': 'left', 'c': 'center', 'r': 'right'}[it['align']] }")


def html_item(it):
    pos = f"position:absolute;left:{it['x']}in;top:{it['y']}in;width:{it['w']}in;height:{it['h']}in;"
    if it["kind"] == "text":
        paras = it["runs"] if isinstance(it["runs"], list) else [it["runs"]]
        out = []
        for i, para in enumerate(paras):
            runs = [(para, {})] if isinstance(para, str) else para
            spans = "".join(f"<span style=\"{'font-weight:700;' if o.get('bold', it['bold']) else ''}"
                            f"{'color:#' + o['color'] + ';' if 'color' in o else ''}\">{html.escape(t)}</span>" for t, o in runs)
            out.append(f"<p style='margin:{10 if i else 0}pt 0 0'>{spans}</p>")
        return f"<div style='{pos}{css_text(it)}'>{''.join(out)}</div>"
    if it["kind"] == "shape":
        r = "50%" if it["shape"] == "oval" else ("0.12in" if it["radius"] else "0")
        op = 1 if it["alpha"] is None else it["alpha"] / 100
        return f"<div style='{pos}background:#{it['fill']};opacity:{op};border-radius:{r}'></div>"
    if it["kind"] == "image":
        return f"<img src='img/{it['path'].name}' style='{pos}object-fit:fill'>"
    if it["kind"] == "chart":
        mx = 25
        bars = "".join(f"<div style='flex:1;min-width:0;display:flex;flex-direction:column;justify-content:flex-end;align-items:center'>"
                       f"<small style='font:700 12pt {FONT};color:#{it['hi'].get(w, 'fff')}'>{f'{v:.1f}%' if w in it['hi'] else ''}</small>"
                       f"<div style='width:70%;height:{v / mx * 85}%;background:#{it['hi'].get(w, 'B8BFCC')}'></div>"
                       f"<span style='font:10pt {FONT};color:#{MUTED};transform:rotate(-45deg);margin-top:6px'>{w}</span></div>"
                       for w, v in it["data"])
        return f"<div style='{pos}display:flex;gap:2px;align-items:stretch;border-bottom:1px solid #B8BFCC'>{bars}</div>"
    raise ValueError(it["kind"])


def build_html(path):
    slides = "".join(f"<section style='background:#{INK if s['dark'] else WHITE}'>{''.join(html_item(i) for i in s['items'])}</section>"
                     for s in SLIDES)
    path.write_text(f"""<!doctype html><meta charset="utf-8"><title>ZudRisk pitch</title>
<style>@page {{ size: {W}in {H}in; margin: 0 }} body {{ margin: 0; background: #888 }}
section {{ position: relative; width: {W}in; height: {H}in; overflow: hidden; margin: 0 auto 0.2in; page-break-after: always }}
@media print {{ body {{ background: none }} section {{ margin: 0 }} }}</style>{slides}""", encoding="utf-8")


if __name__ == "__main__":
    build_pptx(HERE / "zudrisk-pitch.pptx")
    build_html(HERE / "preview.html")
    print("ok", len(SLIDES), "slides")
