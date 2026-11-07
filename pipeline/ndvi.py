"""MODIS MOD13C2 monthly NDVI (0.05 deg CMG, OPeNDAP subset, Earthdata login) for July and August, as a mean per soum."""
import csv
import sys
from pathlib import Path

import netCDF4
import numpy as np

from pipeline.gldas import soum_means
from pipeline.http import cached, get_bytes_auth, get_json
from pipeline.power import cells_for_xy
from pipeline.boundaries import load_soums

CMR = ("https://cmr.earthdata.nasa.gov/search/granules.json?short_name=MOD13C2&version=061"
       "&temporal={y}-{m}-01T00:00:00Z,{y}-{m}-28T23:59:59Z&page_size=1")
VAR = "/MOD_Grid_monthly_CMG_VI/Data_Fields/CMG_0_05_Deg_Monthly_NDVI"
ROWS, COLS = (755, 970), (5340, 6000)
CE = f".dap.nc4?dap4.ce={VAR}%5B{ROWS[0]}:{ROWS[1]}%5D%5B{COLS[0]}:{COLS[1]}%5D"
FILL = -3000
SCALE = 10000.0  # HDF-EOS convention: value = raw / scale_factor
RAW = Path("data/raw/ndvi")
OUT = Path("data/derived/soum_ndvi.csv")


def to_ndvi(raw: np.ndarray) -> np.ma.MaskedArray:
    raw = np.asarray(raw)
    return np.ma.masked_equal(raw, FILL).astype(float) / SCALE


def grid_centres() -> tuple[np.ndarray, np.ndarray]:
    rows = np.arange(ROWS[0], ROWS[1] + 1)
    cols = np.arange(COLS[0], COLS[1] + 1)
    return 90 - 0.05 * (rows + 0.5), -180 + 0.05 * (cols + 0.5)


def granule_url(y: int, m: int) -> str:
    entry = get_json(CMR.format(y=y, m=f"{m:02d}"))["feed"]["entry"][0]
    base = next(l["href"] for l in entry["links"] if l["href"].startswith("https://opendap.earthdata.nasa.gov/"))
    return base + CE


def read(path: Path) -> np.ma.MaskedArray:
    with netCDF4.Dataset("mem", memory=path.read_bytes()) as d:
        v = d[VAR.lstrip("/")]
        v.set_auto_maskandscale(False)  # netCDF4 would multiply by scale_factor; HDF-EOS means divide
        return to_ndvi(v[:])


def main() -> None:
    RAW.mkdir(parents=True, exist_ok=True)
    months = [(y, m) for y in range(2001, 2024) for m in (7, 8)]
    for y, m in months:
        cached(RAW / f"{y}{m:02d}.nc4", lambda y=y, m=m: get_bytes_auth(granule_url(y, m)))
    lats, lons = grid_centres()
    yy, xx = np.meshgrid(lats, lons, indexing="ij")
    xs, ys = xx.ravel(), yy.ravel()
    cells = {s["pcode"]: cells_for_xy(s["geom"], xs, ys) for s in load_soums()}
    rows = []
    for y, m in months:
        for pcode, v in soum_means(read(RAW / f"{y}{m:02d}.nc4"), cells).items():
            if v is not None:
                rows.append((pcode, f"{y}{m:02d}", round(v, 4)))
    with OUT.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["pcode", "yyyymm", "ndvi"])
        w.writerows(rows)
    jul23 = [v for p, ym, v in rows if ym == "202307"]
    print(f"{len(months)} months, {len(cells)} soums, {len(rows)} rows; range {min(r[2] for r in rows)}..{max(r[2] for r in rows)}; "
          f"Jul 2023 soum mean {sum(jul23) / len(jul23):.3f}")


def check() -> None:
    v = to_ndvi(np.array([3861, -3000, 10000]))
    assert v.mask.tolist() == [False, True, False]
    assert abs(v[0] - 0.3861) < 1e-12 and v[2] == 1.0
    lats, lons = grid_centres()
    assert abs(lats[0] - 52.225) < 1e-9 and abs(lons[0] - 87.025) < 1e-9 and lats.size == 216 and lons.size == 661
    import tempfile
    with tempfile.TemporaryDirectory() as d:
        path = Path(d) / "t.nc4"
        with netCDF4.Dataset(path, "w") as ds:
            g = ds.createGroup("MOD_Grid_monthly_CMG_VI").createGroup("Data_Fields")
            g.createDimension("y", 1)
            g.createDimension("x", 2)
            v = g.createVariable("CMG_0_05_Deg_Monthly_NDVI", "i2", ("y", "x"), fill_value=FILL)
            v.scale_factor = 10000.0
            v.set_auto_maskandscale(False)
            v[:] = np.array([[3861, FILL]], dtype="i2")
        got = read(path)
        assert abs(got[0, 0] - 0.3861) < 1e-12 and got.mask.tolist() == [[False, True]], got
    print("ndvi check: ok")


if __name__ == "__main__":
    check() if "--check" in sys.argv else main()
