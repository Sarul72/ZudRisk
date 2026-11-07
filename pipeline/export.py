"""Write the site's data: simplified soum polygons carrying each winter's scores, and its validation."""
import argparse
import csv
import json
import shutil
import sys
from pathlib import Path

import numpy as np
import shapely
from shapely.geometry import Polygon, mapping

from pipeline.boundaries import load_soums
from pipeline.indicators import out_path
from pipeline.validate import out_path_json

SIMPLIFY_DEG = 0.005
MAX_BYTES = 2_000_000
SITE = Path("site/data")
NUMERIC = ["cold_c", "z_cold", "snow_m", "z_snow", "ndvi", "z_summer", "su_per_km2", "z_pressure", "risk",
           "z_snow_gldas", "snow_days", "density_kgm3", "z_density"]


def feature(geom, props: dict) -> dict:
    g = geom.simplify(SIMPLIFY_DEG, preserve_topology=True)
    g = shapely.transform(g, lambda xy: np.round(xy, 4))
    return {"type": "Feature", "properties": props, "geometry": mapping(g)}


def label(year: int) -> str:
    return f"{year}-{(year + 1) % 100:02d}"


def winters_index(years: list[int]) -> list[str]:
    return [label(y) for y in sorted(years)]


def write_index(years: list[int]) -> None:
    (SITE / "winters.json").write_text(json.dumps(winters_index(years)))


def props_for(soum: dict, row: dict) -> dict:
    """A soum's map properties from an indicator row whose missing values are None."""
    props = {k: soum[k] for k in ("pcode", "name_mn", "name_en", "aimag_mn", "aimag_en", "is_ub")}
    props.update({k: None if row.get(k) is None else round(float(row[k]), 4) for k in NUMERIC})
    for k in ("risk_class", "n_indicators"):
        props[k] = None if row.get(k) is None else int(row[k])
    return props


def main(year: int) -> None:
    with out_path(year).open() as f:
        scores = {r["pcode"]: {k: v or None for k, v in r.items()} for r in csv.DictReader(f)}
    feats = [feature(s["geom"], props_for(s, scores.get(s["pcode"], {}))) for s in load_soums()]
    SITE.mkdir(parents=True, exist_ok=True)
    out = SITE / f"risk_{label(year)}.geojson"
    out.write_text(json.dumps({"type": "FeatureCollection", "features": feats}, ensure_ascii=False,
                              separators=(",", ":")))
    shutil.copy(out_path_json(year), SITE / f"validation_{label(year)}.json")
    size = out.stat().st_size
    print(f"{out}: {len(feats)} soums, {size / 1e6:.2f} MB")
    if size > MAX_BYTES:
        sys.exit(f"{out} is over {MAX_BYTES / 1e6:.0f} MB: raise SIMPLIFY_DEG")


def check() -> None:
    import math
    ring = [(math.cos(2 * math.pi * i / 1000), math.sin(2 * math.pi * i / 1000)) for i in range(1000)]
    f = feature(Polygon(ring), {"pcode": "X", "risk": None})
    assert len(f["geometry"]["coordinates"][0]) < 1000
    assert f["properties"] == {"pcode": "X", "risk": None}
    assert all(c == round(c, 4) for xy in f["geometry"]["coordinates"][0] for c in xy)
    assert winters_index([2023, 2009]) == ["2009-10", "2023-24"]
    print("export check: ok")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--winter", type=int, default=2023)
    a = ap.parse_args()
    check() if a.check else main(a.winter)
