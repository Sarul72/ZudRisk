"""Iron dzud from daily data (plan.md idea 5): thaw days on snow, Nov-Feb, per soum.

The monthly test (pipeline.ice) found nothing, maybe because a crust is a one-day thaw that a monthly mean hides.
Here a day counts at a grid cell when its maximum 2 m temperature is above 0 °C while snow lies on the ground
(daily maximum snow depth >= 1 cm). A soum's count for a day is the share of its land cells that thawed on snow, so
a winter's total is the mean over its cells of their thaw days. It is a z-score against 2001-2020, like the others.

Source: Copernicus CDS "ERA5-Land post-processed daily statistics", daily maximum from hourly data, days in Mongolian
time (UTC+8). One request per month, Nov-Feb of winters 2000/01-2024/25: 100 requests. CDS computes each on demand,
so the fetch takes hours; it resumes where it stopped.

    uv run python -m pipeline.thaw --fetch   # needs ~/.cdsapirc (README, "Run")
    uv run python -m pipeline.thaw           # data/derived/soum_thaw.csv, then the test below

The rule, fixed before the run (the one the monthly test used): kept only if, added to the learned model, the
held-out soum rho and AUC both rise over the current model's (0.372 and 0.745). The test also gives the plain
Spearman rho of thaw days against losses, soum-winters 2011/12-2024/25 and aimag-winters 2000/01-2024/25."""
import calendar
import csv
import io
import math
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path

import netCDF4
import numpy as np

from pipeline.era5 import INPUTS, RAW
from pipeline.gldas import map_cells, soum_means
from pipeline.indicators import BASELINE, SNOW_MIN_M
from pipeline.score import zscore

DATASET = "derived-era5-land-daily-statistics"
FIRST, LAST = 2000, 2024  # winters 2000/01 to 2024/25, the hindcast's
DIR = RAW / "era5_land_daily"
OUT = Path("data/derived/soum_thaw.csv")
THAW_K = 273.15
SNOW_MONTHS = ((0, 11), (0, 12), (1, 1), (1, 2))  # (year offset, month): Nov-Feb, March's thaw is every spring's


def winter_months(year: int) -> list[str]:
    return [f"{year + dy}{m:02d}" for dy, m in SNOW_MONTHS]


def request(ym: str) -> dict:
    y, m = int(ym[:4]), int(ym[4:])
    return {"variable": ["2m_temperature", "snow_depth"], "year": str(y), "month": f"{m:02d}",
            "day": [f"{d:02d}" for d in range(1, calendar.monthrange(y, m)[1] + 1)],
            "daily_statistic": "daily_maximum", "time_zone": "utc+08:00", "frequency": "1_hourly",
            "area": INPUTS["area"]}


def files(ym: str) -> list[Path]:
    return sorted(DIR.glob(f"era5_land_daily_{ym}_*.nc"))


def store(ym: str, body: bytes) -> list[Path]:
    """Save one month as era5_land_daily_<yyyymm>_<i>.nc. CDS may send a zip of NetCDF files (one per variable or
    one for all), which is unpacked. Written under a temporary name first, so a cut-off run leaves no month."""
    DIR.mkdir(parents=True, exist_ok=True)
    if body[:2] == b"PK":
        with zipfile.ZipFile(io.BytesIO(body)) as z:
            parts = [z.read(n) for n in sorted(z.namelist()) if n.endswith(".nc")]
    else:
        parts = [body]
    tmp = [DIR / f"era5_land_daily_{ym}_{i}.nc.part" for i in range(len(parts))]
    for t, b in zip(tmp, parts):
        t.write_bytes(b)
    out = [t.with_suffix("") for t in tmp]
    for t, o in zip(tmp, out):
        t.rename(o)
    return out


def have(ym: str) -> bool:
    return bool(files(ym))


def fetch() -> None:
    from pipeline.http import cds_retrieve
    todo = [ym for y in range(FIRST, LAST + 1) for ym in winter_months(y) if not have(ym)]
    print(f"thaw: {len(todo)} months to fetch")
    for i, ym in enumerate(todo, 1):
        store(ym, cds_retrieve(DATASET, request(ym), timeout_s=4 * 3600))
        print(f"  {i}/{len(todo)} {ym}", flush=True)


def _days(d: netCDF4.Dataset) -> list[str]:
    name = "valid_time" if "valid_time" in d.variables else "time"
    t = d[name]
    return [x.strftime("%Y%m%d") for x in netCDF4.num2date(t[:], t.units, only_use_cftime_datetimes=False,
                                                           only_use_python_datetimes=True)]


def read_month(ym: str) -> tuple[dict[str, dict[str, np.ma.MaskedArray]], np.ndarray, np.ndarray]:
    """{"t2m"|"sde": {yyyymmdd: grid}} and the grid's latitudes and longitudes. More than one step a day (hourly
    output in place of the daily maximum) is reduced to the day's maximum here."""
    out: dict[str, dict[str, np.ma.MaskedArray]] = {}
    lats = lons = None
    for f in files(ym):
        with netCDF4.Dataset(f) as d:
            days = _days(d)
            lats, lons = d["latitude"][:].data, d["longitude"][:].data
            for v in ("t2m", "sde"):
                if v not in d.variables:
                    continue
                g = d[v][:]
                for day in sorted(set(days)):
                    idx = [i for i, x in enumerate(days) if x == day]
                    out.setdefault(v, {})[day] = g[idx].max(axis=0)
    return out, lats, lons


def thaw_share(t2m: np.ma.MaskedArray, sde: np.ma.MaskedArray) -> np.ma.MaskedArray:
    """1 where the day thawed on snow, 0 where it did not; masked over water."""
    mask = np.ma.getmaskarray(t2m) | np.ma.getmaskarray(sde)
    hit = (np.ma.filled(t2m, 0) > THAW_K) & (np.ma.filled(sde, 0) >= SNOW_MIN_M)
    return np.ma.array(hit.astype(float), mask=mask)


def winter_thaw(by_month: dict[str, dict[str, float]], year: int) -> float | None:
    """Thaw days on snow over Nov-Feb; None if any month is missing (no data is not no thaw)."""
    ms = winter_months(year)
    return None if any(m not in by_month for m in ms) else sum(by_month[m] for m in ms)


def main() -> dict:
    per: dict[str, dict[str, float]] = {}  # pcode -> yyyymm -> thaw days
    cells = None
    for y in range(FIRST, LAST + 1):
        for ym in winter_months(y):
            if not have(ym):
                continue
            grids, lats, lons = read_month(ym)
            if cells is None:
                cells = map_cells(next(iter(grids["t2m"].values())), lats, lons)
            total: dict[str, float] = {}
            for day, t in grids["t2m"].items():
                for pc, v in soum_means(thaw_share(t, grids["sde"][day]), cells).items():
                    if v is not None:
                        total[pc] = total.get(pc, 0.0) + v
            for pc, v in total.items():
                per.setdefault(pc, {})[ym] = v
    if not per:
        raise SystemExit("thaw: no daily files; run `uv run python -m pipeline.thaw --fetch` first")
    rows = []
    for pc, s in sorted(per.items()):
        tot = {y: winter_thaw(s, y) for y in range(FIRST, LAST + 1)}
        base = [tot[y] for y in BASELINE if tot[y] is not None]
        for y, v in tot.items():
            z = None if v is None else zscore(v, base)
            rows.append((pc, y, "" if v is None else round(v, 3), "" if z is None else round(z, 4)))
    with OUT.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["pcode", "winter", "thaw_days", "z_thaw"])
        w.writerows(rows)
    print(f"thaw: {len(per)} soums, {len(rows)} soum-winters -> {OUT}")
    return test()


def load(p: Path | None = None) -> dict[tuple[str, int], float | None]:
    with (p or OUT).open(encoding="utf-8") as f:
        return {(r["pcode"], int(r["winter"])): float(r["z_thaw"]) if r["z_thaw"] else None for r in csv.DictReader(f)}


def test() -> dict:
    """Spearman of thaw days against losses, then the model with z_thaw added, every winter held out in turn."""
    from pipeline import indicators
    from pipeline import model as M
    from pipeline.boundaries import load_soums
    from pipeline.gldas import load_series
    from pipeline.nso import load_hay, load_livestock, load_livestock_aimag, sheep_units
    from pipeline.validate import aimag_pairs, mortality, spearman

    z = load()
    herds, aherds = load_livestock(), load_livestock_aimag()
    soums, hay, ndvi = load_soums(), load_hay(), load_series(indicators.NDVI_CSV)
    aimag_of = {s["pcode"]: s["aimag_pcode"] for s in soums}
    pairs = [(v, m) for (pc, y), v in z.items() if v is not None and y in M.TRAIN and (m := mortality(herds, pc, y)) is not None]
    apairs = []
    for y in range(FIRST, LAST + 1):
        apairs += [(r, m) for _, r, m in aimag_pairs(y, {pc: (v, aimag_of[pc]) for (pc, yy), v in z.items()
                                                         if yy == y and v is not None and pc in aimag_of}, herds, aherds)]
    rho = {"soum": round(spearman(*zip(*pairs)), 3), "n_soum": len(pairs),
           "aimag": round(spearman(*zip(*apairs)), 3), "n_aimag": len(apairs)}

    soum_rows = M.training_rows(herds, ndvi, M.hay_per_su(hay, herds, soums))
    aimag_rows = M.aimag_rows(soums, herds, aherds, ndvi, hay)

    def aimag_z(a: str, y: int) -> float | None:
        parts = [(v, st) for pc, aa in aimag_of.items() if aa == a and (v := z.get((pc, y))) is not None
                 and (st := sheep_units(herds.get((pc, y, "stock"), {})))]
        return sum(v * w for v, w in parts) / sum(w for _, w in parts) if parts else None

    def add(r: dict, v: float | None) -> dict:
        return {**r, "x": r["x"][:-1] + [math.nan if v is None else v] + r["x"][-1:]}  # past_mortality stays last

    def held(rows):
        h = M.lowo(rows)
        return M.skill([p for y in M.TRAIN for p in h[y]], [r for y in M.TRAIN for r in rows if r["winter"] == y])

    base = held(soum_rows + aimag_rows)
    new = held([add(r, z.get((r["pcode"], r["winter"]))) for r in soum_rows] +
               [add(r, aimag_z(r["pcode"], r["winter"])) for r in aimag_rows])
    kept = new["rho_model"] > base["rho_model"] and new["auc_model"] > base["auc_model"]
    print(f"thaw days vs losses: rho soum {rho['soum']} (n {rho['n_soum']}), aimag {rho['aimag']} (n {rho['n_aimag']})")
    print(f"model + z_thaw, held-out soum: rho {base['rho_model']} -> {new['rho_model']}, AUC {base['auc_model']} -> {new['auc_model']}")
    print(f"thaw: {'KEPT: add z_thaw to pipeline.model FEATURES' if kept else 'not used'} (rule: both soum figures must rise)")
    return {"rho": rho, "base": base, "with_thaw": new, "kept": kept,
            "run": datetime.now(timezone.utc).strftime("%Y-%m-%d")}


def check() -> None:
    import tempfile
    assert winter_months(2003) == ["200311", "200312", "200401", "200402"]
    r = request("200402")
    assert r["day"][-1] == "29" and r["month"] == "02" and r["year"] == "2004" and r["time_zone"] == "utc+08:00", r
    assert len(request("200311")["day"]) == 30

    t = np.ma.array([[THAW_K + 1, THAW_K + 1, THAW_K - 5], [THAW_K + 2, 0.0, 0.0]], mask=[[0, 0, 0], [0, 1, 0]])
    s = np.ma.array([[0.05, 0.0, 0.3], [SNOW_MIN_M, 0.2, 0.2]], mask=[[0, 0, 0], [0, 1, 0]])
    got = thaw_share(t, s)
    assert got.tolist() == [[1.0, 0.0, 0.0], [1.0, None, 0.0]], got  # warm on snow; warm on bare ground; cold on snow
    by = {"200311": 1.0, "200312": 0.0, "200401": 2.5, "200402": 0.5}
    assert winter_thaw(by, 2003) == 4.0
    assert winter_thaw({k: v for k, v in by.items() if k != "200401"}, 2003) is None, "a missing month is not zero"

    with tempfile.TemporaryDirectory() as tmp:  # a month as CDS sends it: hourly steps reduce to the day's maximum
        global DIR
        keep_dir, DIR = DIR, Path(tmp)
        try:
            f = Path(tmp) / "x.nc"
            with netCDF4.Dataset(f, "w") as d:
                d.createDimension("valid_time", 3), d.createDimension("latitude", 1), d.createDimension("longitude", 2)
                vt = d.createVariable("valid_time", "i8", ("valid_time",))
                vt.units = "seconds since 1970-01-01"
                day = int(datetime(2004, 1, 1, tzinfo=timezone.utc).timestamp())
                vt[:] = [day, day + 3600, day + 86400]
                d.createVariable("latitude", "f4", ("latitude",))[:] = [47.0]
                d.createVariable("longitude", "f4", ("longitude",))[:] = [100.0, 100.1]
                d.createVariable("t2m", "f4", ("valid_time", "latitude", "longitude"))[:] = [[[270, 260]], [[274, 261]], [[250, 250]]]
                d.createVariable("sde", "f4", ("valid_time", "latitude", "longitude"))[:] = [[[0.1, 0.1]], [[0.1, 0.1]], [[0.1, 0.1]]]
            buf = io.BytesIO()
            with zipfile.ZipFile(buf, "w") as z:
                z.writestr("data_stream-oper_stepType-max.nc", f.read_bytes())
            assert not have("200401")
            store("200401", f.read_bytes())
            grids, lats, lons = read_month("200401")
            assert sorted(grids["t2m"]) == ["20040101", "20040102"] and float(grids["t2m"]["20040101"][0, 0]) == 274.0, grids
            assert thaw_share(grids["t2m"]["20040101"], grids["sde"]["20040101"]).tolist() == [[1.0, 0.0]]
            for x in files("200401"):
                x.unlink()
            store("200401", buf.getvalue())
            assert have("200401") and sorted(read_month("200401")[0]["sde"]) == ["20040101", "20040102"], "a zip is unpacked"
        finally:
            DIR = keep_dir
    print("thaw check: ok")


if __name__ == "__main__":
    if "--check" in sys.argv:
        check()
    elif "--fetch" in sys.argv:
        fetch()
    elif "--test" in sys.argv:
        test()
    else:
        main()
