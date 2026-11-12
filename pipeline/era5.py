"""ERA5-Land monthly snow depth, density, cover and 2 m temperature over Mongolia (Copernicus CDS), as a mean per soum.
A history file holds 2001-2024 (and an early one Nov-Dec 2000); each later year has its own file, refetched under a new name as months land."""
import csv
import sys
import urllib.error
from datetime import date, datetime, timezone
from pathlib import Path

import netCDF4
import numpy as np

from pipeline.gldas import map_cells, soum_means
from pipeline.http import cached, cds_months, cds_retrieve

DATASET = "reanalysis-era5-land-monthly-means"
INPUTS = {
    "product_type": ["monthly_averaged_reanalysis"],
    "variable": ["snow_depth", "snow_density", "snow_cover", "2m_temperature"],
    "year": [str(y) for y in range(2001, 2025)],
    "month": ["01", "02", "03", "11", "12"],
    "time": ["00:00"],
    "area": [52.2, 87.0, 41.5, 120.0],  # N, W, S, E: the soum boundaries' extent plus a cell
    "data_format": "netcdf",
    "download_format": "unarchived",
}
RAW = Path("data/raw")
HISTORY = RAW / "era5_land_2001_2024.nc"
EARLY = RAW / "era5_land_2000_11_12.nc"  # the start of winter 2000/01, the first one hindcast
EARLY_INPUTS = {**INPUTS, "year": ["2000"], "month": ["11", "12"]}
FIRST_RECENT = 2025
WINTER = ["01", "02", "03", "11", "12"]
OUT = Path("data/derived/soum_era5.csv")
VARS = {"sde": "sde_m", "rsn": "rsn_kgm3", "snowc": "snowc_pct", "t2m": "t2m_c"}  # file variable -> CSV column


def yyyymm(seconds: float) -> str:
    """valid_time is seconds since 1970-01-01 UTC; read it in UTC so a month's first midnight stays in that month."""
    return datetime.fromtimestamp(float(seconds), timezone.utc).strftime("%Y%m")


def read_fields(path: Path) -> tuple[dict[str, dict[str, np.ma.MaskedArray]], np.ndarray, np.ndarray]:
    """{yyyymm: {var: 2-D grid}}, latitudes, longitudes."""
    with netCDF4.Dataset(path) as d:
        units = getattr(d["valid_time"], "units", "")
        if not units.startswith("seconds since 1970-01-01"):
            raise ValueError(f"{path}: valid_time is in '{units}', read as seconds since 1970")
        times = [yyyymm(t) for t in d["valid_time"][:]]
        grids = {v: d[v][:] for v in VARS}
        fields = {ym: {v: grids[v][i] for v in VARS} for i, ym in enumerate(times)}
        return fields, d["latitude"][:].data, d["longitude"][:].data


def to_celsius(kelvin: float) -> float:
    return kelvin - 273.15


def recent_name(year: int, months: list[str]) -> Path:
    """Named by its last month, so a month that lands later is a new file rather than a stale cache hit."""
    return RAW / f"era5_land_{year}_{months[-1]}.nc"


def merge(fields_list: list[dict]) -> dict:
    """Later files win a month two files hold."""
    out: dict = {}
    for fields in fields_list:
        out.update(fields)
    return out


def depth_weighted(rsn: np.ma.MaskedArray, sde: np.ma.MaskedArray, cells: dict[str, np.ndarray]) -> dict[str, float | None]:
    """A soum's snow density weighted by each cell's depth, so bare cells' nominal ~100 kg/m3 does not dilute
    the snowpack; with no snow anywhere it is the plain mean, which the 0.01 m gate ignores downstream."""
    flat_r, flat_d = rsn.ravel(), sde.ravel()
    out = {}
    for pcode, idx in cells.items():
        v, w = flat_r[idx], np.ma.filled(flat_d[idx], 0.0)
        if v.count() == 0:
            out[pcode] = None
            continue
        total = float(w[~np.ma.getmaskarray(v)].sum())
        out[pcode] = float((v * w).sum() / total) if total > 0 else float(v.mean())
    return out


def recent_months(year: int, months_of=cds_months) -> list[str]:
    """Winter months the CDS has published for a year; unreachable, it warns and the cached files stand."""
    try:
        return [m for m in months_of(DATASET, year, "snow_depth") if m in WINTER]
    except urllib.error.HTTPError as e:
        if e.code < 500:  # a refused or changed request is a bug to see, not an outage to ride out
            raise
        reason = f"HTTP {e.code}"
    except (urllib.error.URLError, TimeoutError) as e:
        reason = str(e)
    print(f"warning: CDS unreachable ({reason}); using cached ERA5-Land files for {year}", file=sys.stderr)
    return []


def fetch() -> None:
    RAW.mkdir(parents=True, exist_ok=True)
    cached(EARLY, lambda: cds_retrieve(DATASET, EARLY_INPUTS))
    cached(HISTORY, lambda: cds_retrieve(DATASET, INPUTS))
    for year in range(FIRST_RECENT, date.today().year + 1):
        months = recent_months(year)
        if months:
            cached(recent_name(year, months), lambda y=year, ms=months: cds_retrieve(DATASET, {**INPUTS, "year": [str(y)], "month": ms}))


def files() -> list[Path]:
    """Nov-Dec 2000, the history file, then each later year's newest file, oldest first."""
    out = [EARLY, HISTORY]
    for year in range(FIRST_RECENT, date.today().year + 1):
        have = sorted(RAW.glob(f"era5_land_{year}_*.nc"))
        out += have[-1:]
    return out


def main() -> None:
    fetch()
    read = [read_fields(p) for p in files()]
    fields, lats, lons = merge([f for f, _, _ in read]), read[0][1], read[0][2]
    assert all(r[1].shape == lats.shape and np.allclose(r[1], lats) and r[2].shape == lons.shape
               and np.allclose(r[2], lons) for r in read), "ERA5 files on different grids"
    months = sorted(fields)
    cells = map_cells(fields[months[0]]["sde"], lats, lons)
    rows = []
    for ym in months:
        means = {v: soum_means(fields[ym][v], cells) for v in VARS if v != "rsn"}
        means["rsn"] = depth_weighted(fields[ym]["rsn"], fields[ym]["sde"], cells)
        for pcode in cells:
            if all(means[v][pcode] is not None for v in VARS):
                means["t2m"][pcode] = to_celsius(means["t2m"][pcode])
                rows.append((pcode, ym, *(round(means[v][pcode], 5) for v in VARS)))
    with OUT.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["pcode", "yyyymm", *VARS.values()])
        w.writerows(rows)
    print(f"{len(months)} months, {len(cells)} soums, {len(rows)} rows -> {OUT}")


def load_era5(path: Path = OUT) -> dict[str, dict[str, dict[str, float]]]:
    """pcode -> variable (sde, rsn, snowc, t2m in °C) -> {yyyymm: value}."""
    out: dict[str, dict[str, dict[str, float]]] = {}
    with path.open(encoding="utf-8") as f:
        for r in csv.DictReader(f):
            series = out.setdefault(r["pcode"], {v: {} for v in VARS})
            for v, col in VARS.items():
                series[v][r["yyyymm"]] = float(r[col])
    return out


def check() -> None:
    import tempfile
    import urllib.error
    assert yyyymm(1704067200) == "202401"  # 2024-01-01 00:00 UTC
    assert files()[:2] == [EARLY, HISTORY], "winter 2000/01 needs Nov-Dec 2000, before the history file"
    assert EARLY_INPUTS["year"] == ["2000"] and EARLY_INPUTS["month"] == ["11", "12"]
    assert yyyymm(1701388800) == "202312"  # 2023-12-01 00:00 UTC
    assert yyyymm(1701385200) == "202311"  # 2023-11-30 23:00 UTC: Ulaanbaatar's local clock already reads December
    with tempfile.TemporaryDirectory() as d:
        p = Path(d) / "t.nc"
        with netCDF4.Dataset(p, "w") as nc:
            nc.createDimension("valid_time", 1)
            nc.createDimension("latitude", 2)
            nc.createDimension("longitude", 2)
            t = nc.createVariable("valid_time", "i8", ("valid_time",))
            t[:] = [1704067200]
            t.units = "seconds since 1970-01-01"
            nc.createVariable("latitude", "f8", ("latitude",))[:] = [50.0, 49.9]
            nc.createVariable("longitude", "f8", ("longitude",))[:] = [100.0, 100.1]
            for name, v in (("sde", 0.2), ("rsn", 150.0), ("snowc", 80.0), ("t2m", 250.0)):
                nc.createVariable(name, "f4", ("valid_time", "latitude", "longitude"))[:] = np.full((1, 2, 2), v)
        fields, lats, lons = read_fields(p)
    assert list(fields) == ["202401"], fields.keys()
    assert set(fields["202401"]) == {"sde", "rsn", "snowc", "t2m"}
    assert fields["202401"]["rsn"].shape == (2, 2) and float(fields["202401"]["sde"][0, 0]) == np.float32(0.2)
    assert list(lats) == [50.0, 49.9] and list(lons) == [100.0, 100.1]
    with tempfile.TemporaryDirectory() as d:
        p = Path(d) / "days.nc"
        with netCDF4.Dataset(p, "w") as nc:
            nc.createDimension("valid_time", 1)
            t = nc.createVariable("valid_time", "i8", ("valid_time",))
            t[:] = [19723]
            t.units = "days since 1970-01-01"
        try:
            read_fields(p)
            raise AssertionError("a file in days must not be read as seconds")
        except ValueError as e:
            assert "days since" in str(e), e
    rsn = np.ma.array([[100.0, 300.0], [100.0, 200.0]])
    sde = np.ma.array([[0.0, 0.3], [0.0, 0.1]])
    w = depth_weighted(rsn, sde, {"A": np.array([0, 1, 2, 3]), "bare": np.array([0, 2])})
    assert abs(w["A"] - 275.0) < 1e-9, w  # bare cells' nominal 100 left out: (300*0.3 + 200*0.1) / 0.4
    assert w["bare"] == 100.0, w  # no snow anywhere: the plain mean, which the 0.01 m gate ignores downstream
    def down(*a):
        raise urllib.error.URLError("CDS unreachable")
    assert recent_months(2026, down) == []
    def refused(*a):
        raise urllib.error.HTTPError("https://x", 400, "Bad Request", {}, None)
    try:
        recent_months(2026, refused)
        raise AssertionError("a 400 is a broken request, not an outage")
    except urllib.error.HTTPError:
        pass
    def no_rc(*a):
        raise FileNotFoundError("~/.cdsapirc")
    try:
        recent_months(2026, no_rc)
        raise AssertionError("a missing ~/.cdsapirc is not an outage")
    except FileNotFoundError:
        pass
    assert recent_months(2026, lambda *a: ["01", "02", "10"]) == ["01", "02"]
    assert to_celsius(273.15) == 0.0
    assert merge([{"202401": {"sde": 1}}, {"202401": {"sde": 2}, "202402": {"sde": 3}}]) == \
        {"202401": {"sde": 2}, "202402": {"sde": 3}}, "the newer file wins a month both hold"
    assert recent_name(2026, ["01", "02", "03", "10"]) == Path("data/raw/era5_land_2026_10.nc")
    print("era5 check: ok")


if __name__ == "__main__":
    if "--check" in sys.argv:
        check()
    elif "--fetch" in sys.argv:
        fetch()
    else:
        main()
