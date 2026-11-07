"""ERA5-Land monthly snow depth, density and cover over Mongolia (Copernicus CDS), as a mean per soum."""
import csv
import sys
from datetime import datetime, timezone
from pathlib import Path

import netCDF4
import numpy as np

from pipeline.gldas import map_cells, soum_means
from pipeline.http import cached, cds_retrieve

DATASET = "reanalysis-era5-land-monthly-means"
INPUTS = {
    "product_type": ["monthly_averaged_reanalysis"],
    "variable": ["snow_depth", "snow_density", "snow_cover"],
    "year": [str(y) for y in range(2001, 2025)],
    "month": ["01", "02", "03", "11", "12"],
    "time": ["00:00"],
    "area": [52.2, 87.0, 41.5, 120.0],  # N, W, S, E: the soum boundaries' extent plus a cell
    "data_format": "netcdf",
    "download_format": "unarchived",
}
RAW = Path("data/raw/era5_land_monthly.nc")
OUT = Path("data/derived/soum_era5.csv")
VARS = {"sde": "sde_m", "rsn": "rsn_kgm3", "snowc": "snowc_pct"}  # file variable -> CSV column


def yyyymm(seconds: float) -> str:
    """valid_time is seconds since 1970-01-01 UTC; read it in UTC so a month's first midnight stays in that month."""
    return datetime.fromtimestamp(float(seconds), timezone.utc).strftime("%Y%m")


def read_fields(path: Path) -> tuple[dict[str, dict[str, np.ma.MaskedArray]], np.ndarray, np.ndarray]:
    """{yyyymm: {var: 2-D grid}}, latitudes, longitudes."""
    with netCDF4.Dataset(path) as d:
        times = [yyyymm(t) for t in d["valid_time"][:]]
        grids = {v: d[v][:] for v in VARS}
        fields = {ym: {v: grids[v][i] for v in VARS} for i, ym in enumerate(times)}
        return fields, d["latitude"][:].data, d["longitude"][:].data


def fetch() -> Path:
    RAW.parent.mkdir(parents=True, exist_ok=True)
    return cached(RAW, lambda: cds_retrieve(DATASET, INPUTS))


def main() -> None:
    fields, lats, lons = read_fields(fetch())
    months = sorted(fields)
    cells = map_cells(fields[months[0]]["sde"], lats, lons)
    rows = []
    for ym in months:
        means = {v: soum_means(fields[ym][v], cells) for v in VARS}
        for pcode in cells:
            if all(means[v][pcode] is not None for v in VARS):
                rows.append((pcode, ym, *(round(means[v][pcode], 5) for v in VARS)))
    with OUT.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["pcode", "yyyymm", *VARS.values()])
        w.writerows(rows)
    print(f"{len(months)} months, {len(cells)} soums, {len(rows)} rows -> {OUT}")


def load_era5(path: Path = OUT) -> dict[str, dict[str, dict[str, float]]]:
    """pcode -> variable (sde, rsn, snowc) -> {yyyymm: value}."""
    out: dict[str, dict[str, dict[str, float]]] = {}
    with path.open() as f:
        for r in csv.DictReader(f):
            series = out.setdefault(r["pcode"], {v: {} for v in VARS})
            for v, col in VARS.items():
                series[v][r["yyyymm"]] = float(r[col])
    return out


def check() -> None:
    import tempfile
    assert yyyymm(1704067200) == "202401"  # 2024-01-01 00:00 UTC
    assert yyyymm(1701388800) == "202312"  # 2023-12-01 00:00 UTC
    assert yyyymm(1701385200) == "202311"  # 2023-11-30 23:00 UTC: Ulaanbaatar's local clock already reads December
    with tempfile.TemporaryDirectory() as d:
        p = Path(d) / "t.nc"
        with netCDF4.Dataset(p, "w") as nc:
            nc.createDimension("valid_time", 1)
            nc.createDimension("latitude", 2)
            nc.createDimension("longitude", 2)
            nc.createVariable("valid_time", "i8", ("valid_time",))[:] = [1704067200]
            nc.createVariable("latitude", "f8", ("latitude",))[:] = [50.0, 49.9]
            nc.createVariable("longitude", "f8", ("longitude",))[:] = [100.0, 100.1]
            for name, v in (("sde", 0.2), ("rsn", 150.0), ("snowc", 80.0)):
                nc.createVariable(name, "f4", ("valid_time", "latitude", "longitude"))[:] = np.full((1, 2, 2), v)
        fields, lats, lons = read_fields(p)
    assert list(fields) == ["202401"], fields.keys()
    assert set(fields["202401"]) == {"sde", "rsn", "snowc"}
    assert fields["202401"]["rsn"].shape == (2, 2) and float(fields["202401"]["sde"][0, 0]) == np.float32(0.2)
    assert list(lats) == [50.0, 49.9] and list(lons) == [100.0, 100.1]
    print("era5 check: ok")


if __name__ == "__main__":
    if "--check" in sys.argv:
        check()
    elif "--fetch" in sys.argv:
        fetch()
    else:
        main()
