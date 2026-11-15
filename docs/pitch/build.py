"""Hazard Watch pitch deck by team Spy Kids (ZudRisk and Mongolia Hazard Watch): 7 slides, 16:9, built from one spec into a PowerPoint file and an HTML twin.

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
    "hz": crop("hz_combined.png", "c_hz.png", (380, 250, 2320, 1220)),
    "hzflood": crop("hz_flood.png", "c_hzflood.png", (0, 100, 1150, 1350)),
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
    return T("!!brand", 0.6, 0.32, 3.0, 0.35, [[("Hazard ", {}), ("Watch", {"color": ORANGE})]], size=14, bold=True,
             color=WHITE if dark else INK)


def title(text, dark=False):
    return T("!!title", 0.6, 0.72, 11.6, 0.9, text, size=34, bold=True, color=WHITE if dark else INK)


mh = 6.0 / RATIO
HR = 1940 / 970
SLIDES = [
    dict(dark=True, transition="fade", items=[
        R("!!orb", 6.9, -0.9, 7.2, 7.2, ACCENT, "oval", alpha=28),
        I("!!map", 7.0, 0.75, 5.8, 5.8 / RATIO, MAPS["dzud"]),
        I("hz", 7.0, 0.75 + 5.8 / RATIO + 0.3, 5.8, 5.8 / HR, MAPS["hz"]),
        brand(True),
        T("!!title", 0.6, 1.7, 6.0, 2.1, "Watching Mongolia's slow disasters from space", size=42, bold=True, color=WHITE),
        T("sub", 0.6, 4.0, 5.8, 1.1, [[("Hazard Watch", {"bold": True, "color": WHITE}), ("  by team Spy Kids", {})],
                                       "ZudRisk  ·  Mongolia Hazard Watch"], size=20, color=SOFT),
        T("event", 0.6, 6.45, 6.3, 0.6, "NASA Space Apps Challenge 2026  ·  Ulaanbaatar  ·  Be An Earth System Trend Detective!",
          size=12, color="9AA6BD"),
    ], notes="Mongolia lives with hazards that build up slowly and strike different places: dzud in winter, floods, "
             "wildfires and dust storms. We built two linked, open maps that read the trends behind them from space."),
    dict(dark=False, transition="morph", items=[
        R("!!orb", 11.7, 0.25, 1.2, 1.2, ORANGE, "oval", alpha=30),
        brand(False),
        title("Slow disasters that hit different places"),
        T("stat", 0.6, 2.05, 4.0, 1.3, "21.7%", size=72, bold=True, color=RED),
        T("stat_l", 0.6, 3.45, 3.9, 1.3, "of Mongolia's adult livestock died in the 2009/10 dzud. In 2023/24 it was 13.8%.",
          size=18, color=INK),
        T("why", 0.6, 4.95, 3.9, 1.4, "Floods, wildfires and dust storms strike every year too. The data to see them is open, "
          "but scattered across a dozen portals.", size=15, color=MUTED, italic=True),
        dict(kind="chart", name="losses", x=4.9, y=1.85, w=7.9, h=4.75, data=LOSSES, hi={"09/10": RED, "23/24": ORANGE}),
        T("src", 4.9, 6.65, 7.9, 0.4, "Adult livestock lost by winter, % (NSO, aimag totals excl. Ulaanbaatar)", size=11, color=MUTED),
    ], notes="Dzud took a fifth of the national herd in 2009/10 and almost 14 percent in 2023/24. Floods, wildfires and "
             "dust storms come every year. The satellite data to watch all of them exists, but it is scattered."),
    dict(dark=False, transition="morph", items=[
        R("!!orb", 11.7, 0.25, 1.2, 1.2, ORANGE, "oval", alpha=22),
        brand(False),
        title("The trend: greener pastures, nearly twice the herd"),
        I("green", 0.6, 1.8, 6.6, 6.6 / RATIO, MAPS["green"]),
        T("green_cap", 0.6, 1.85 + 6.6 / RATIO, 6.6, 0.6,
          "Trend in July–August greenness per soum, 2001–2026 (NASA MODIS NDVI, Theil–Sen slope). "
          "Darker green: greening faster. Brown: browning.", size=11, color=MUTED),
        T("g_stat", 7.65, 1.75, 5.1, 0.9, "+15%", size=50, bold=True, color="2E7D32"),
        T("g_lab", 7.65, 2.65, 5.1, 1.0, "summer greenness of the median soum since 2001. Greener in 322 of 339 soums "
          "(significant in 157); browner in 17, all in the far west, none significant.", size=14, color=INK),
        T("h_stat", 7.65, 3.7, 5.1, 0.9, "×1.9", size=50, bold=True, color=RED),
        T("h_lab", 7.65, 4.6, 5.1, 0.8, "the herd in sheep units, 2000 to 2025 (NSO). More grass, but far more "
          "animals on it.", size=14, color=INK),
        R("scorebox", 0.6, 5.85, 12.15, 1.2, LIGHT, "rect", radius=True),
        T("score", 0.85, 5.85, 11.7, 1.2, [[("One dzud score per soum  ", {"bold": True, "color": INK}),
                                            ("snow depth and winter cold (ERA5-Land), summer pasture (NASA MODIS NDVI) "
                                             "and grazing pressure (NSO), each against the soum's own 2001–2020 normal; "
                                             "weights fixed from the literature. 339 soums × 25 winters, plus a monthly "
                                             "outlook.", {})]], size=14, color=MUTED, anchor="m"),
    ], notes="The trend first. Since 2001, NASA MODIS shows summer pasture greening in 322 of 339 soums, by 15 percent in "
             "the median soum; only the far west browned. But the herd grazing it nearly doubled. That is why grazing "
             "pressure is one of the four signals in our dzud score, next to snow depth, winter cold and summer pasture, "
             "each compared with the soum's own normal, with weights fixed from published research before any test."),
    dict(dark=False, transition="morph", items=[
        R("!!orb", 12.2, 6.45, 0.7, 0.7, ORANGE, "oval", alpha=30),
        brand(False),
        title("Same map, two winters, checked against real losses"),
        T("cap_a", 0.6, 1.75, 6.0, 0.5, [[("2026/27 outlook", {"bold": True}), (" · October, before any snow", {})]], size=16),
        I("map_a", 0.6, 2.3, 6.0, mh, MAPS["outlook"]),
        T("cap_b", 6.73, 1.75, 6.0, 0.5, [[("2009/10", {"bold": True, "color": RED}), (" · the dzud winter", {})]], size=16),
        I("!!map", 6.73, 2.3, 6.0, mh, MAPS["dzud"]),
        T("leg", 0.6, 2.3 + mh + 0.2, 12.1, 1.6, [
            [("Do we rank the soums in the order of their real losses? ", {"bold": True, "color": INK}),
             ("Spearman ρ, 1 = same order, 0 = no link: ", {}),
             ("0.60", {"bold": True, "color": ACCENT}), (" in the five test winters fixed in advance, ", {}),
             ("0.44", {"bold": True, "color": ACCENT}), (" over all 4,688 soum-winters 2011–2025.", {})],
            [("58% vs 15%: ", {"bold": True, "color": RED}),
             ("soums we rated very high lost 5% or more of their herd, against 15% overall. The outlook sharpens as "
              "winter comes: ρ 0.23 in October, 0.50 in November, 0.64 by December.", {})]],
          size=14, color=MUTED),
    ], notes="Live demo. The October outlook before any snow is mostly yellow; 2009/10 turns red in the west and centre, "
             "where the losses happened. We check the order of soums against real losses: a rank correlation of 0.60 in "
             "the dzud winters we fixed in advance, 0.44 over every winter. The outlook is weak in October and useful "
             "from December, so that is when governors should act on it."),
    dict(dark=False, transition="morph", items=[
        R("!!orb", 11.0, 5.3, 2.0, 2.0, "7F77DD", "oval", alpha=22),
        brand(False),
        title("Mongolia Hazard Watch: four hazards since 2001"),
        I("!!map", 0.6, 1.85, 7.8, 7.8 / HR, MAPS["hz"]),
        T("t1", 8.85, 1.95, 4.0, 1.4, [[("What  ", {"bold": True, "color": INK}),
                                        ("flood, wildfire, dust storm and dzud risk on a 0.1° grid", {})]], size=16, color=MUTED),
        T("t2", 8.85, 3.35, 4.0, 1.4, [[("When  ", {"bold": True, "color": INK}),
                                        ("any day since 2001; step or play through the years", {})]], size=16, color=MUTED),
        T("t3", 8.85, 4.75, 4.0, 1.4, [[("Data  ", {"bold": True, "color": INK}),
                                        ("NASA MODIS, VIIRS, HLS and GIBS imagery, computed in Google Earth Engine", {})]],
          size=16, color=MUTED),
    ], notes="Mongolia Hazard Watch puts four hazards on one map, day by day since 2001, on NASA imagery. "
             "Pick a hazard, pick a day, and watch where each one comes back."),
    dict(dark=False, transition="morph", items=[
        R("!!orb", 0.3, 5.9, 1.2, 1.2, "7F77DD", "oval", alpha=25),
        brand(False),
        title("Draw any area, compute it in the browser"),
        I("panel", 0.6, 1.8, 4.4, 4.4 / (1150 / 1250), MAPS["hzflood"]),
        *[c for i, (head, body) in enumerate([
            ("Flood extent", "Sentinel-1 radar sees through cloud; Sentinel-2 checks it"),
            ("Burned area", "Sentinel-2 dNBR before and after a fire"),
            ("Dust conditions", "bare ground, wind and rain for the chosen day"),
        ]) for c in (
            R(f"hc{i}", 5.3, 1.85 + i * 1.12, 7.45, 0.98, LIGHT, "rect", radius=True),
            T(f"hh{i}", 5.55, 1.85 + i * 1.12, 2.4, 0.98, head, size=18, bold=True, anchor="m"),
            T(f"hb{i}", 7.95, 1.85 + i * 1.12, 4.6, 0.98, body, size=15, color=MUTED, anchor="m"),
        )],
        T("dl", 5.3, 5.3, 7.45, 0.5, [[("Download  ", {"bold": True, "color": INK}),
                                       ("GeoTIFF · Shapefile · GeoJSON · KML · KMZ, straight into QGIS or ArcGIS", {})]],
          size=15, color=MUTED),
        R("devbox", 5.3, 5.95, 7.45, 0.95, "FFF4E8", "rect", radius=True),
        T("dev", 5.55, 5.95, 7.0, 0.95, [[("In development: ", {"bold": True, "color": "8A3B00"}),
                                          ("the flood and wildfire risk indices are not yet calibrated against recorded events; "
                                           "that is our next step.", {})]], size=14, color="8A3B00", anchor="m"),
    ], notes="Draw any area and the browser computes flood extent from Sentinel-1 radar, burned area from Sentinel-2, or "
             "dust conditions, and you download it as GIS files. Honestly: the flood and wildfire risk indices are still "
             "being developed; calibrating them against recorded events is our next step."),
    dict(dark=True, transition="fade", items=[
        R("!!orb", -1.6, 3.6, 6.0, 6.0, ACCENT, "oval", alpha=28),
        brand(True),
        T("!!title", 0.6, 0.95, 11.6, 1.0, "Built for those who act before disaster", size=40, bold=True, color=WHITE),
        T("who", 0.6, 2.25, 7.6, 2.4, [
            [("Soum and aimag governors", {"bold": True, "color": WHITE}), ("  where to stock hay, where floods and fires threaten", {})],
            [("NEMA", {"bold": True, "color": WHITE}), ("  where to send support first", {})],
            [("Aid agencies and researchers", {"bold": True, "color": WHITE}), ("  open maps and GIS files, no coding", {})],
        ], size=20, color=SOFT),
        T("url", 4.4, 4.95, 8.4, 0.8, "mongolia-risk.vercel.app", size=38, bold=True, color="8FB4FF", align="r"),
        T("open", 4.4, 5.85, 8.4, 0.5, "Open code · github.com/Sarul72/ZudRisk · github.com/Sigma0sanaa/hazard", size=14,
          color="9AA6BD", align="r"),
    ], notes="Two open maps, one goal: let governors, NEMA and aid agencies act before the disaster, not after. Thank you."),
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
