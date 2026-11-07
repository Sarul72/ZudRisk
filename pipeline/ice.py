"""Iron dzud (төмөр зуд) candidates from ERA5-Land monthly means: mid-winter snowmelt and rain on snow, Nov-Feb.
A thaw that refreezes, or rain that falls on the snowpack, seals the pasture under ice; the four scored indicators
see depth, density and cold but not a crust. These are tested against losses and in the model, not scored.

ERA5-Land's monthly means of accumulated fields are the mean daily accumulation (m of water); a month's total is
that times its days. March is left out: its melt is the spring thaw every winter has."""
import calendar
import csv
import sys
from pathlib import Path

import netCDF4

from pipeline.era5 import DATASET, INPUTS, RAW, load_era5, yyyymm
from pipeline.gldas import map_cells, soum_means
from pipeline.http import cached, cds_retrieve
from pipeline.indicators import BASELINE, SNOW_MIN_M
from pipeline.score import zscore

FIRST, LAST = 2000, 2024  # winters 2000/01 to 2024/25, the hindcast's
MONTHS = ["11", "12", "01", "02"]
PATH = RAW / f"era5_land_ice_{FIRST}_{LAST + 1}.nc"
FETCH = {**INPUTS, "variable": ["snowmelt", "total_precipitation", "snowfall"],
         "year": [str(y) for y in range(FIRST, LAST + 2)], "month": sorted(MONTHS)}
VARS = ("smlt", "tp", "sf")
OUT = Path("data/derived/soum_ice.csv")


def winter_months(year: int) -> list[str]:
    return [f"{year}11", f"{year}12", f"{year + 1}01", f"{year + 1}02"]


def days(ym: str) -> int:
    return calendar.monthrange(int(ym[:4]), int(ym[4:]))[1]


def winter_totals(s: dict[str, dict[str, float]], sde: dict[str, float], year: int) -> tuple[float | None, float | None]:
    """(snowmelt, rain on snow) over Nov-Feb in mm. Rain is precipitation less snowfall, counted only in months
    with snow on the ground; None when a month is missing."""
    ms = winter_months(year)
    melt = None if any(m not in s["smlt"] for m in ms) else 1000 * sum(s["smlt"][m] * days(m) for m in ms)
    if any(m not in s["tp"] or m not in s["sf"] or m not in sde for m in ms):
        return melt, None
    return melt, 1000 * sum(max(s["tp"][m] - s["sf"][m], 0.0) * days(m) for m in ms if sde[m] >= SNOW_MIN_M)


def main() -> None:
    with netCDF4.Dataset(PATH) as d:
        times = [yyyymm(t) for t in d["valid_time"][:]]
        grids = {v: d[v][:] for v in VARS}
        lats, lons = d["latitude"][:].data, d["longitude"][:].data
    cells = map_cells(grids["smlt"][0], lats, lons)
    series: dict[str, dict[str, dict[str, float]]] = {pc: {v: {} for v in VARS} for pc in cells}
    for i, ym in enumerate(times):
        for v in VARS:
            for pc, x in soum_means(grids[v][i], cells).items():
                if x is not None:
                    series[pc][v][ym] = x
    era5 = load_era5()
    rows = []
    for pc, s in series.items():
        sde = era5.get(pc, {}).get("sde", {})
        tot = {y: winter_totals(s, sde, y) for y in range(FIRST, LAST + 1)}
        base = [[tot[y][k] for y in BASELINE if tot[y][k] is not None] for k in (0, 1)]
        for y, (melt, ros) in tot.items():
            z = [None if x is None else zscore(x, b) for x, b in zip((melt, ros), base)]
            rows.append((pc, y, *("" if v is None else round(v, 4) for v in (melt, ros, *z))))
    with OUT.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["pcode", "winter", "melt_mm", "ros_mm", "z_melt", "z_ros"])
        w.writerows(rows)
    print(f"ice: {len(cells)} soums, winters {FIRST}-{LAST}, {len(rows)} rows -> {OUT}")


def load(path: Path = OUT) -> dict[tuple[str, int], dict[str, float | None]]:
    """(pcode, winter) -> {"z_melt", "z_ros"}."""
    with path.open() as f:
        return {(r["pcode"], int(r["winter"])): {k: float(r[k]) if r[k] else None for k in ("z_melt", "z_ros")}
                for r in csv.DictReader(f)}


def check() -> None:
    w = winter_months(2003)
    assert w == ["200311", "200312", "200401", "200402"] and days("200402") == 29
    s = {"smlt": {m: 0.001 for m in w}, "tp": {m: 0.002 for m in w}, "sf": {m: 0.0015 for m in w}}
    s["smlt"]["200403"] = 0.5  # the spring thaw, never counted
    sde = {"200311": 0.0, "200312": 0.05, "200401": 0.2, "200402": SNOW_MIN_M}
    melt, ros = winter_totals(s, sde, 2003)
    assert abs(melt - 1.0 * (30 + 31 + 31 + 29)) < 1e-9, melt  # 1 mm a day over Nov-Feb of a leap winter
    assert abs(ros - 0.5 * (31 + 31 + 29)) < 1e-9, ros  # November's rain fell on bare ground
    s["sf"]["200401"] = 0.003  # more snow than precipitation: rounding in the archive, not negative rain
    assert abs(winter_totals(s, sde, 2003)[1] - 0.5 * (31 + 29)) < 1e-9
    del s["tp"]["200312"]
    assert winter_totals(s, sde, 2003) == (melt, None), "a missing month is no rain, not zero rain"
    print("ice check: ok")


if __name__ == "__main__":
    if "--check" in sys.argv:
        check()
    elif "--fetch" in sys.argv:
        cached(PATH, lambda: cds_retrieve(DATASET, FETCH))
    else:
        main()
