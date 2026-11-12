"""Write the site's data: simplified soum polygons carrying each winter's scores, and its validation."""
import argparse
import csv
import functools
import json
import shutil
import sys
from pathlib import Path

import numpy as np
import shapely
from shapely.geometry import Polygon, mapping

from pipeline.boundaries import is_aimag_centre, load_soums
from pipeline.indicators import census_year, out_path, winter_end
from pipeline.nso import load_livestock, load_livestock_aimag
from pipeline.validate import mortality, out_path_json

SIMPLIFY_DEG = 0.005
COVERAGE_TOL = 0.01  # coverage_simplify's tolerance; about the vertex count SIMPLIFY_DEG gave polygon by polygon
MAX_BYTES = 2_000_000
SITE = Path("site/data")
NUMERIC = ["cold_c", "z_cold", "snow_m", "z_snow", "ndvi", "z_summer", "su_per_km2", "z_pressure", "risk",
           "z_snow_gldas", "snow_days", "density_kgm3", "z_density"]


def coverage(soums: list[dict]) -> dict[str, object]:
    """Simplify the soums together, so a border two soums share stays one line: simplified one by one they
    overlapped by 0.032 square degrees and left 0.027 open."""
    shapes = shapely.coverage_simplify(np.array([s["geom"] for s in soums], dtype=object), COVERAGE_TOL)
    return {s["pcode"]: g for s, g in zip(soums, shapes)}


@functools.cache
def soum_shapes() -> dict[str, object]:
    return coverage(load_soums())


def feature(geom, props: dict, simplify: bool = True) -> dict:
    g = geom.simplify(SIMPLIFY_DEG, preserve_topology=True) if simplify else geom
    g = shapely.transform(g, lambda xy: np.round(xy, 4))
    return {"type": "Feature", "properties": props, "geometry": mapping(g)}


def label(year: int) -> str:
    return f"{year}-{(year + 1) % 100:02d}"


def winters_index(years: list[int]) -> list[str]:
    return [label(y) for y in sorted(years)]


def write_index(years: list[int]) -> None:
    (SITE / "winters.json").write_text(json.dumps(winters_index(years)), encoding="utf-8")


def props_for(soum: dict, row: dict) -> dict:
    """A soum's map properties from an indicator row whose missing values are None."""
    props = {k: soum[k] for k in ("pcode", "name_mn", "name_en", "aimag_mn", "aimag_en", "is_ub")}
    props["is_centre"] = is_aimag_centre(soum)  # its herd density is the aimag's (indicators.pressure_by_soum)
    props.update({k: None if row.get(k) is None else round(float(row[k]), 4) for k in NUMERIC})
    for k in ("risk_class", "n_indicators", "no_herd"):
        props[k] = None if row.get(k) is None else int(row[k])
    return props


def copy_validation(src: Path, dst: Path) -> None:
    """A winter's validation to the site; a winter whose losses are not out yet has none, and leaves none behind."""
    if src.exists():
        shutil.copy(src, dst)
    else:
        dst.unlink(missing_ok=True)


def national_pct(path: Path) -> float | None:
    """A winter's national mortality from its validation, or None while its losses are not out."""
    return json.loads(path.read_text(encoding="utf-8"))["mortality_pct"] if path.exists() else None


def main(year: int) -> None:
    with out_path(year).open(encoding="utf-8") as f:
        scores = {r["pcode"]: {k: v or None for k, v in r.items()} for r in csv.DictReader(f)}
    from pipeline import aimags  # aimags imports this module
    props = {s["pcode"]: props_for(s, scores.get(s["pcode"], {})) for s in load_soums()}
    feats = [feature(soum_shapes()[s["pcode"]], props[s["pcode"]], simplify=False) for s in load_soums()]
    aimags.write_scores(label(year), props, load_livestock(), census_year(year, winter_end(year)))
    from pipeline import zones  # zones imports this module
    zones.write_scores(label(year), year, props, load_livestock(), census_year(year, winter_end(year)))
    SITE.mkdir(parents=True, exist_ok=True)
    out = SITE / f"risk_{label(year)}.geojson"
    out.write_text(json.dumps({"type": "FeatureCollection", "features": feats}, ensure_ascii=False,
                              separators=(",", ":")), encoding="utf-8")
    copy_validation(out_path_json(year), SITE / f"validation_{label(year)}.json")
    size = out.stat().st_size
    print(f"{out}: {len(feats)} soums, {size / 1e6:.2f} MB")
    if size > MAX_BYTES:
        sys.exit(f"{out} is over {MAX_BYTES / 1e6:.0f} MB: raise SIMPLIFY_DEG")


def history(years: list[int], risk: dict[int, dict], aimag_risk: dict[int, dict], soums: list[dict], herds: dict,
            aherds: dict, national: dict[int, float], zones: dict[int, dict] | None = None) -> dict:
    """Every soum's, aimag's and natural zone's risk and recorded mortality across the winters, for the popup charts."""
    r3 = lambda v: None if v is None else round(v, 3)  # noqa: E731
    out = {"winters": [label(y) for y in years], "national_pct": [national.get(y) for y in years], "soum": {}, "aimag": {}}
    for s in soums:
        out["soum"][s["pcode"]] = {"risk": [r3(risk[y].get(s["pcode"])) for y in years],
                                   "mort": [r3(mortality(herds, s["pcode"], y)) for y in years]}
    for a in sorted({s["aimag_pcode"] for s in soums}):
        out["aimag"][a] = {"risk": [r3(aimag_risk[y].get(a, {}).get("risk")) for y in years],
                           "mort": [r3(mortality(aherds, a, y)) for y in years]}
    if zones is not None:
        out["zone"] = {z: {"risk": [r3(zones[y].get(z, {}).get("risk")) for y in years],
                           "mort": [r3(zones[y].get(z, {}).get("mortality")) for y in years]}
                       for z in sorted({z for y in years for z in zones[y]})}
    return out


def write_history(years: list[int]) -> None:
    from pipeline.indicators import read_risk
    national = {y: national_pct(out_path_json(y)) for y in years}
    aimag_risk = {y: json.loads((SITE / f"aimag_{label(y)}.json").read_text(encoding="utf-8")) for y in years}
    zone_path = {y: SITE / f"zone_{label(y)}.json" for y in years}
    zones = {y: json.loads(p.read_text(encoding="utf-8")) for y, p in zone_path.items()} if all(p.exists() for p in zone_path.values()) else None
    h = history(years, {y: read_risk(y) for y in years}, aimag_risk, load_soums(), load_livestock(),
                load_livestock_aimag(), national, zones)
    (SITE / "history.json").write_text(json.dumps(h, separators=(",", ":"), allow_nan=False), encoding="utf-8")


def check() -> None:
    import math
    ring = [(math.cos(2 * math.pi * i / 1000), math.sin(2 * math.pi * i / 1000)) for i in range(1000)]
    f = feature(Polygon(ring), {"pcode": "X", "risk": None})
    assert len(f["geometry"]["coordinates"][0]) < 1000
    assert f["properties"] == {"pcode": "X", "risk": None}
    assert all(c == round(c, 4) for xy in f["geometry"]["coordinates"][0] for c in xy)
    assert winters_index([2023, 2009]) == ["2009-10", "2023-24"]
    teeth = [(0, 0)] + [(0.0005 * (i % 2), i / 100) for i in range(1, 100)] + [(0, 1)]  # a jagged shared border
    left = Polygon([(-1, 0), *teeth, (-1, 1)])
    right = Polygon([(1, 0), (1, 1), *reversed(teeth)])
    shapes = coverage([{"pcode": "L", "geom": left}, {"pcode": "R", "geom": right}])
    both = shapely.union_all(list(shapes.values()))
    assert shapes["L"].intersection(shapes["R"]).area < 1e-12, "neighbours simplified apart overlap"
    assert abs(both.area - (left.area + right.area)) < 1e-9, "neighbours simplified apart leave a gap"
    assert shapely.get_num_coordinates(shapes["L"]) < shapely.get_num_coordinates(left), "it still simplifies"
    kept = feature(shapes["L"], {}, simplify=False)
    assert len(kept["geometry"]["coordinates"][0]) == shapely.get_num_coordinates(shapes["L"])

    full = {"camel": 0, "horse": 0, "cattle": 0, "goat": 0}
    herds = {("A", 2011, "stock"): {**full, "sheep": 100.0}, ("A", 2012, "loss"): {**full, "sheep": 12.5}}
    aherds = {("X", 2011, "stock"): {**full, "sheep": 1000.0}, ("X", 2012, "loss"): {**full, "sheep": 50.0}}
    h = history([2011, 2012], {2011: {"A": 0.51234}, 2012: {}}, {2011: {"X": {"risk": 0.3}}, 2012: {}},
                [{"pcode": "A", "aimag_pcode": "X"}, {"pcode": "B", "aimag_pcode": "X"}], herds, aherds, {2011: 1.2})
    assert h == {"winters": ["2011-12", "2012-13"], "national_pct": [1.2, None],
                 "soum": {"A": {"risk": [0.512, None], "mort": [0.125, None]}, "B": {"risk": [None, None], "mort": [None, None]}},
                 "aimag": {"X": {"risk": [0.3, None], "mort": [0.05, None]}}}, h
    hz = history([2011, 2012], {2011: {}, 2012: {}}, {2011: {}, 2012: {}}, [], {}, {}, {},
                 zones={2011: {"steppe": {"risk": 0.2, "mortality": 0.05}}, 2012: {}})
    assert hz["zone"] == {"steppe": {"risk": [0.2, None], "mort": [0.05, None]}}, hz

    import tempfile
    with tempfile.TemporaryDirectory() as d:
        p = Path(d) / "validation_2025.json"
        assert national_pct(p) is None, "a winter whose losses are not out has no national mortality"
        p.write_text(json.dumps({"mortality_pct": 2.5}), encoding="utf-8")
        assert national_pct(p) == 2.5
        site = Path(d) / "site"
        site.mkdir()
        (site / "validation_2025-26.json").write_text("{}", encoding="utf-8")
        copy_validation(Path(d) / "absent.json", site / "validation_2025-26.json")
        assert not (site / "validation_2025-26.json").exists(), "a stale validation file is not left behind"
        copy_validation(p, site / "validation_2025-26.json")
        assert json.loads((site / "validation_2025-26.json").read_text(encoding="utf-8")) == {"mortality_pct": 2.5}
    print("export check: ok")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--winter", type=int, default=2023)
    a = ap.parse_args()
    check() if a.check else main(a.winter)
