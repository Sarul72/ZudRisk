"""NASA GLDAS-2.1 Noah monthly snow depth over Mongolia (OPeNDAP subset, Earthdata login), as a mean per soum."""
import csv
import sys
from pathlib import Path

import netCDF4
import numpy as np

from pipeline.boundaries import load_soums
from pipeline.http import cached, get_bytes_auth
from pipeline.power import cells_for_xy

URL = ("https://opendap.earthdata.nasa.gov/collections/C1342986036-GES_DISC/granules/"
       "GLDAS_NOAH025_M.2.1:GLDAS_NOAH025_M.A{ym}.021.nc4.dap.nc4"
       "?dap4.ce=/SnowDepth_inst%5B0%5D%5B406:448%5D%5B1068:1199%5D;/lat%5B406:448%5D;/lon%5B1068:1199%5D")
RAW = Path("data/raw/gldas")
OUT = Path("data/derived/soum_snow.csv")
WINTER_MONTHS = (11, 12, 1, 2, 3)


def winter_months_range(first: int, last: int) -> list[str]:
    """Nov first .. Mar last+1, winter months only."""
    out = []
    for y in range(first, last + 1):
        out += [f"{y}11", f"{y}12"] + [f"{y + 1}{m:02d}" for m in (1, 2, 3)]
    return out


def soum_means(grid: np.ma.MaskedArray, cells: dict[str, np.ndarray]) -> dict[str, float | None]:
    """Mean of each soum's unmasked cells (flat indices); a soum whose cells are all water gets None."""
    flat = grid.ravel()
    out = {}
    for pcode, idx in cells.items():
        v = flat[idx]
        out[pcode] = None if v.count() == 0 else float(v.mean())
    return out


def map_cells(grid: np.ma.MaskedArray, lats: np.ndarray, lons: np.ndarray) -> dict[str, np.ndarray]:
    """Flat grid indices per soum, over land cells only, so the nearest-cell fallback never picks water."""
    yy, xx = np.meshgrid(lats, lons, indexing="ij")
    land = np.nonzero(~np.ma.getmaskarray(grid).ravel())[0]
    xs, ys = xx.ravel()[land], yy.ravel()[land]
    return {s["pcode"]: land[cells_for_xy(s["geom"], xs, ys)] for s in load_soums()}


def read(path: Path) -> tuple[np.ma.MaskedArray, np.ndarray, np.ndarray]:
    with netCDF4.Dataset("mem", memory=path.read_bytes()) as d:
        return d["SnowDepth_inst"][0], d["lat"][:].data, d["lon"][:].data


def load_series(path: Path) -> dict[str, dict[str, float]]:
    out: dict[str, dict[str, float]] = {}
    with path.open() as f:
        for pcode, ym, v in csv.reader(f):
            if pcode != "pcode":
                out.setdefault(pcode, {})[ym] = float(v)
    return out


def main() -> None:
    RAW.mkdir(parents=True, exist_ok=True)
    months = winter_months_range(2001, 2023)
    for ym in months:
        cached(RAW / f"A{ym}.nc4", lambda ym=ym: get_bytes_auth(URL.format(ym=ym)))
    grid, lats, lons = read(RAW / f"A{months[0]}.nc4")
    cells = map_cells(grid, lats, lons)
    rows = []
    for ym in months:
        for pcode, v in soum_means(read(RAW / f"A{ym}.nc4")[0], cells).items():
            if v is not None:
                rows.append((pcode, ym, round(v, 5)))
    with OUT.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["pcode", "yyyymm", "snow_m"])
        w.writerows(rows)
    print(f"{len(months)} months, {len(cells)} soums, {len(rows)} rows -> {OUT}")


def check() -> None:
    grid = np.ma.array([[1.0, 2.0], [3.0, 99.0]], mask=[[False, False], [False, True]])
    means = soum_means(grid, {"all": np.array([0, 1, 2, 3]), "lake": np.array([3])})
    assert means == {"all": 2.0, "lake": None}, means
    assert len(winter_months_range(2001, 2023)) == 115
    print("gldas check: ok")


if __name__ == "__main__":
    check() if "--check" in sys.argv else main()
