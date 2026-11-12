"""ECMWF SEAS5 seasonal forecasts (Copernicus CDS, system 51) issued 1 October, read as the coming winter's cold and
snow per soum, so the pre-winter outlook stage has a forecast where it otherwise has no weather at all.

Each member's forecast is turned into the same two indicators the score uses (mean 2 m temperature Nov-Feb, deepest
monthly snow Nov-Mar; SEAS5 snow is water equivalent, so it is standardised in its own units), and the ensemble mean
is standardised against the model's own 2001-2020 forecasts: z = (ensemble mean - climate mean) / member spread of
the climate. The ensemble mean of an uncertain forecast sits near the climate, so a forecast with little to say
moves the score little. The climate includes the scored winter, the exception ERA5-Land's baseline also makes."""
import csv
import sys
from pathlib import Path

import netCDF4
import numpy as np

from pipeline.gldas import map_cells
from pipeline.http import CDS_RC, _cds_call, cached, cds_config, cds_retrieve
from pipeline.indicators import BASELINE, score_row

DATASET = "seasonal-monthly-single-levels"
FIRST = 2000  # winter 2000/01, the first one hindcast
INIT = "10"  # issued 1 October, published about the 5th: before the oct stage's 31 October cut
LEADS = ["2", "3", "4", "5", "6"]  # forecastMonth 1 is October itself; 2-6 are November to March
COLD_LEADS = 4  # Nov-Feb, the months indicators.cold averages
INPUTS = {"originating_centre": "ecmwf", "system": "51", "variable": ["2m_temperature", "snow_depth"],
          "product_type": ["monthly_mean"], "month": [INIT], "leadtime_month": LEADS,
          "area": [52.2, 87.0, 41.5, 120.0], "data_format": "netcdf"}  # the ERA5-Land box
RAW = Path("data/raw")
OUT = Path("data/derived/soum_seas5.csv")


def raw_path(year: int) -> Path:
    return RAW / f"seas5_{year}_{INIT}.nc"


def published_years() -> list[int]:
    url, key = cds_config(CDS_RC.read_text(encoding="utf-8"))
    c = _cds_call(f"{url}/retrieve/v1/processes/{DATASET}/constraints", key,
                  {"inputs": {k: INPUTS[k] for k in ("originating_centre", "system", "month", "product_type")}}, timeout=60)
    return sorted(y for y in map(int, c.get("year", [])) if y >= FIRST)


def fetch(years: list[int]) -> None:
    RAW.mkdir(parents=True, exist_ok=True)

    for y in years:  # one at a time: six requests at once were each rejected, with no reason given
        cached(raw_path(y), lambda y=y: cds_retrieve(DATASET, {**INPUTS, "year": [str(y)]}, poll_s=10))


def read(path: Path) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """t2m (K) and sd (m water equivalent) as [member, lead, cell], with latitudes and longitudes. Members the
    archive pads (hindcasts have 25, forecasts 51) come masked and are dropped."""
    with netCDF4.Dataset(path) as d:
        months = list(d["forecastMonth"][:])
        if months != [int(m) for m in LEADS]:
            raise ValueError(f"{path}: forecastMonth {months}, expected {LEADS}")
        t2m, sd = (np.ma.filled(d[v][:, 0].astype(float), np.nan) for v in ("t2m", "sd"))
        lats, lons = d["latitude"][:].data, d["longitude"][:].data
    keep = ~np.isnan(t2m).all(axis=(1, 2, 3))
    n = keep.sum()
    return t2m[keep].reshape(n, len(LEADS), -1), sd[keep].reshape(n, len(LEADS), -1), lats, lons


def member_indicators(t2m: np.ndarray, sd: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Per member, from [member, lead] series: mean Nov-Feb temperature (deg C) and deepest Nov-Mar snow."""
    return t2m[:, :COLD_LEADS].mean(1) - 273.15, sd.max(1)


def standardise(by_year: dict[int, np.ndarray], baseline=BASELINE) -> dict[int, float]:
    """Each year's ensemble mean against the members of the baseline years: (mean - climate mean) / climate spread."""
    clim = np.concatenate([by_year[y] for y in baseline if y in by_year] or [np.empty(0)])
    if len(clim) < 2 or clim.std() == 0:  # a soum the model never snows on has no snow anomaly to give
        return {}
    return {y: float((v.mean() - clim.mean()) / clim.std()) for y, v in by_year.items()}


def with_forecast(rows: dict[str, dict], fc: dict[str, tuple[float, float]]) -> dict[str, dict]:
    """The stage's rows with a forecast z_cold and z_snow where the stage has none, re-scored; observed months win."""
    out = {}
    for pc, r in rows.items():
        r = dict(r)
        for k, v in zip(("z_cold", "z_snow"), fc.get(pc, (None, None))):
            if r[k] is None and v is not None:
                r[k] = v
        r.update(score_row({k: r[f"z_{k}"] for k in ("cold", "snow", "summer", "pressure")}, not r["no_herd"]))
        out[pc] = r
    return out


def main() -> None:
    years = sorted(int(p.stem.split("_")[1]) for p in RAW.glob(f"seas5_*_{INIT}.nc"))
    cold: dict[str, dict[int, np.ndarray]] = {}
    snow: dict[str, dict[int, np.ndarray]] = {}
    grid, members = None, {}
    for y in years:
        t2m, sd, lats, lons = read(raw_path(y))
        if grid is None:
            grid = (lats, lons, map_cells(np.ma.masked_invalid(t2m[0, 0].reshape(len(lats), len(lons))), lats, lons))
        assert np.array_equal(grid[0], lats) and np.array_equal(grid[1], lons), f"{y}: SEAS5 on a different grid"
        members[y] = len(t2m)
        for pc, idx in grid[2].items():
            c, s = member_indicators(t2m[:, :, idx].mean(-1), sd[:, :, idx].mean(-1))
            cold.setdefault(pc, {})[y], snow.setdefault(pc, {})[y] = c, s
    rows = []
    for pc in cold:
        zc, zs = standardise(cold[pc]), standardise(snow[pc])
        for y in years:
            c = None if y not in zc else -zc[y]  # colder is riskier, as indicators.z_cold
            rows.append((pc, y, "" if c is None else round(c, 4), round(zs[y], 4) if y in zs else "", members[y]))
    with OUT.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["pcode", "year", "z_cold_fc", "z_snow_fc", "members"])
        w.writerows(rows)
    print(f"SEAS5 {INIT}-init winters {years[0]}-{years[-1]} ({len(years)}), members {sorted(set(members.values()))}, "
          f"{len(cold)} soums -> {OUT}")


def load(path: Path = OUT) -> dict[int, dict[str, tuple[float | None, float | None]]]:
    """winter -> pcode -> (z_cold, z_snow) from that winter's 1 October forecast."""
    out: dict[int, dict[str, tuple]] = {}
    with path.open(encoding="utf-8") as f:
        for r in csv.DictReader(f):
            out.setdefault(int(r["year"]), {})[r["pcode"]] = tuple(float(r[k]) if r[k] else None
                                                                   for k in ("z_cold_fc", "z_snow_fc"))
    return out


def check() -> None:
    import tempfile
    with tempfile.TemporaryDirectory() as d:
        p = Path(d) / "s.nc"
        with netCDF4.Dataset(p, "w") as nc:
            for dim, n in (("number", 3), ("forecast_reference_time", 1), ("forecastMonth", 5), ("latitude", 2), ("longitude", 2)):
                nc.createDimension(dim, n)
            nc.createVariable("forecastMonth", "i4", ("forecastMonth",))[:] = [2, 3, 4, 5, 6]
            nc.createVariable("latitude", "f8", ("latitude",))[:] = [50.0, 49.0]
            nc.createVariable("longitude", "f8", ("longitude",))[:] = [100.0, 101.0]
            dims = ("number", "forecast_reference_time", "forecastMonth", "latitude", "longitude")
            for name, v in (("t2m", 260.0), ("sd", 0.02)):
                var = nc.createVariable(name, "f4", dims, fill_value=np.float32(9.96921e36))
                var[:2] = np.full((2, 1, 5, 2, 2), v)  # member 3 never written: the archive's padding
        t2m, sd, lats, lons = read(p)
    assert t2m.shape == (2, 5, 4) and sd.shape == (2, 5, 4), t2m.shape
    assert np.allclose(t2m, 260.0) and np.allclose(sd, 0.02) and list(lats) == [50.0, 49.0]

    t = np.array([[250.0, 260.0, 262.0, 268.0, 999.0], [270.0, 270.0, 270.0, 270.0, 0.0]])
    s = np.array([[0.01, 0.03, 0.02, 0.0, 0.05], [0.0, 0.0, 0.0, 0.0, 0.0]])
    cold, snow = member_indicators(t, s)
    assert np.allclose(cold, [260.0 - 273.15, 270.0 - 273.15]), "Nov-Feb only: March is not winter cold"
    assert np.allclose(snow, [0.05, 0.0]), "the deepest month, March included"

    by = {2001: np.array([0.0, 2.0]), 2002: np.array([2.0, 4.0]), 2030: np.array([5.0, 5.0, 5.0])}
    z = standardise(by, baseline=range(2001, 2003))
    assert set(z) == {2001, 2002, 2030}
    assert abs(z[2030] - (5.0 - 2.0) / np.std([0.0, 2.0, 2.0, 4.0])) < 1e-12, z  # climate: the four baseline members
    assert abs(z[2001] + z[2002]) < 1e-12, "a symmetric climate centres on zero"
    assert standardise({2030: np.array([1.0])}, baseline=range(2001, 2003)) == {}, "no climate, no z"

    rows = {"A": {"z_cold": None, "z_snow": None, "z_summer": 1.0, "z_pressure": 0.0, "no_herd": 0},
            "B": {"z_cold": -0.5, "z_snow": 0.2, "z_summer": 0.0, "z_pressure": 0.0, "no_herd": 0},
            "C": {"z_cold": None, "z_snow": None, "z_summer": 1.0, "z_pressure": 0.0, "no_herd": 1}}
    out = with_forecast(rows, {"A": (1.0, 2.0), "B": (3.0, 3.0), "C": (1.0, 1.0)})
    assert out["A"]["z_cold"] == 1.0 and out["A"]["z_snow"] == 2.0 and out["A"]["n_indicators"] == 4
    assert out["A"]["risk"] == score_row({"cold": 1.0, "snow": 2.0, "summer": 1.0, "pressure": 0.0})["risk"]
    assert out["B"]["z_cold"] == -0.5 and out["B"]["z_snow"] == 0.2, "an observed month is never overwritten"
    assert out["C"]["risk"] is None, "no herd, no risk, forecast or not"
    assert rows["A"]["z_cold"] is None, "the stage's own rows are left as they were"
    assert with_forecast(rows, {})["A"]["z_cold"] is None, "a soum the forecast misses keeps what it had"
    print("seasonal check: ok")


if __name__ == "__main__":
    if "--check" in sys.argv:
        check()
    elif "--fetch" in sys.argv:
        fetch(published_years())
    else:
        main()
