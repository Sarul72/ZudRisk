"""NASA POWER monthly 2 m air temperature over Mongolia (keyless), and which grid points belong to each soum."""
import csv
import json
import math
import sys
from pathlib import Path

from shapely.geometry import Point, box

from pipeline.boundaries import load_soums
from pipeline.http import get_json

URL = ("https://power.larc.nasa.gov/api/temporal/monthly/regional?latitude-min={s}&latitude-max={n}"
       "&longitude-min={w}&longitude-max={e}&parameters=T2M&community=AG&start=2001&end=2024&format=JSON")
# POWER takes a range of 2 to 10 degrees on each axis; the top band overlaps and merge() dedupes it
LATS = [(41.5, 51.5), (50.5, 52.5)]
LONS = [(87, 97), (97, 107), (107, 117), (117, 120)]
FILL = -999
RAW = Path("data/raw/power_t2m.json")
T2M = Path("data/derived/t2m_monthly.csv")
CELLS = Path("data/derived/soum_cells.json")


def cells_for(geom, points: list[tuple[float, float]]) -> list[tuple[float, float]]:
    """Grid points inside the soum; a soum too small to hold one takes the nearest point."""
    inside = [p for p in points if geom.contains(Point(p))]
    if inside:
        return inside
    c = geom.representative_point()
    k = math.cos(math.radians(c.y))  # a degree of longitude shrinks with latitude
    return [min(points, key=lambda p: ((p[0] - c.x) * k) ** 2 + (p[1] - c.y) ** 2)]


def merge(boxes: list[list[dict]]) -> dict[tuple[float, float], dict[str, float]]:
    """One series per grid point: boxes share their edges, and the annual (month 13) and fill values go."""
    out = {}
    for features in boxes:
        for f in features:
            lon, lat = f["geometry"]["coordinates"][:2]
            series = f["properties"]["parameter"]["T2M"]
            out[(lon, lat)] = {k: v for k, v in series.items() if not k.endswith("13") and v != FILL}
    return out


def main() -> None:
    if not RAW.exists():
        boxes = [get_json(URL.format(s=s, n=n, w=w, e=e))["features"] for s, n in LATS for w, e in LONS]
        RAW.parent.mkdir(parents=True, exist_ok=True)
        RAW.write_text(json.dumps(boxes))
    grid = merge(json.loads(RAW.read_text()))
    T2M.parent.mkdir(parents=True, exist_ok=True)
    with T2M.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["lon", "lat", "yyyymm", "t2m"])
        for (lon, lat), series in sorted(grid.items()):
            w.writerows((lon, lat, k, v) for k, v in sorted(series.items()))
    points = list(grid)
    cells, fallback = {}, 0
    for s in load_soums():
        inside = [p for p in points if s["geom"].contains(Point(p))]
        fallback += not inside
        cells[s["pcode"]] = [list(p) for p in cells_for(s["geom"], points)]
    CELLS.write_text(json.dumps(cells))
    print(f"{len(points)} unique points; {len(cells)} soums mapped, {fallback} by nearest point")


def check() -> None:
    sq = box(0, 0, 1, 1)
    assert cells_for(sq, [(0.5, 0.5), (2, 2)]) == [(0.5, 0.5)]
    tiny = box(5, 5, 5.1, 5.1)
    assert cells_for(tiny, [(0.5, 0.5), (5.3, 5.0), (9, 9)]) == [(5.3, 5.0)]
    north = box(100, 60, 100.01, 60.01)  # at 60N a degree of longitude is half a degree of latitude
    assert cells_for(north, [(101.0, 60.0), (100.0, 60.7)]) == [(101.0, 60.0)]
    f = lambda lon, lat, v: {"geometry": {"coordinates": [lon, lat, 100]},
                             "properties": {"parameter": {"T2M": {"202301": v, "202313": 0, "202302": FILL}}}}
    merged = merge([[f(1, 2, -10.0)], [f(1, 2, -10.0), f(3, 4, -5.0)]])
    assert merged == {(1, 2): {"202301": -10.0}, (3, 4): {"202301": -5.0}}, merged
    print("power check: ok")


if __name__ == "__main__":
    check() if "--check" in sys.argv else main()
