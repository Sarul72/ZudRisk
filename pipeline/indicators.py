"""Indicators per soum and winter: winter cold and snow (ERA5-Land), summer pasture (MODIS NDVI)
and grazing pressure (NSO herds), each as a z-score where higher means riskier, then the score (spec 4.3-4.4).
GLDAS snow, snow-cover days and snow density are carried alongside for comparison and display, never scored."""
import argparse
import calendar
import functools
import csv
import math
from collections import Counter
from datetime import date, timedelta
from pathlib import Path

from pipeline.boundaries import is_aimag_centre, load_soums
from pipeline.era5 import load_era5
from pipeline.gldas import OUT as GLDAS_CSV, load_series
from pipeline.ndvi import OUT as NDVI_CSV
from pipeline.nso import load_livestock, sheep_units
from pipeline.score import risk, risk_class, zscore

BASELINE = range(2001, 2021)  # winters 2001/02 .. 2020/21, summers 2001 .. 2020
COLUMNS = ["pcode", "cold_c", "z_cold", "snow_m", "z_snow", "ndvi", "z_summer", "su_per_km2", "z_pressure",
           "n_indicators", "risk", "risk_class", "z_snow_gldas", "snow_days", "density_kgm3", "z_density"]


def out_path(year: int) -> Path:
    return Path(f"data/derived/indicators_{year}.csv")


def _months_over(months: list[tuple[int, int]], as_of: date) -> list[str]:
    out = []
    for y, m in months:
        last_day = date(y + (m == 12), m % 12 + 1, 1) - timedelta(days=1)
        if last_day <= as_of:
            out.append(f"{y}{m:02d}")
    return out


def winter_months(year: int, as_of: date) -> list[str]:
    """Nov-Feb of winter year/year+1, keeping only months already over on as_of."""
    return _months_over([(year, 11), (year, 12), (year + 1, 1), (year + 1, 2)], as_of)


def snow_months(year: int, as_of: date) -> list[str]:
    """Nov-Mar of winter year/year+1, keeping only months already over on as_of."""
    return _months_over([(year, 11), (year, 12), (year + 1, 1), (year + 1, 2), (year + 1, 3)], as_of)


def shift_as_of(as_of: date, years: int) -> date:
    """The same calendar day in another winter, so a baseline winter sees the same months as the scored one.
    A month's last day maps to that month's last day: 28 Feb 2023 is 29 Feb 2004, or a leap baseline loses February."""
    y = as_of.year + years
    last = calendar.monthrange(as_of.year, as_of.month)[1]
    day = calendar.monthrange(y, as_of.month)[1] if as_of.day == last else as_of.day
    return as_of.replace(year=y, day=day)


def cold(series: dict[str, float], year: int, as_of: date) -> float | None:
    """Mean of the soum's monthly 2 m air temperature over the winter months so far; None if any month is missing."""
    months = winter_months(year, as_of)
    if not months or any(m not in series for m in months):
        return None
    return sum(series[m] for m in months) / len(months)


def snow(series: dict[str, float], year: int, as_of: date) -> float | None:
    """Deepest monthly mean snow of the winter so far (m); None if any month is missing."""
    months = snow_months(year, as_of)
    if not months or any(m not in series for m in months):
        return None
    return max(series[m] for m in months)


SNOW_MIN_M = 0.01  # below a centimetre ERA5-Land still reports a nominal density over bare ground


def snow_days(cover_pct: dict[str, float], year: int, as_of: date) -> float | None:
    """Snow-covered days of the winter so far: each month's mean cover share times its length."""
    months = snow_months(year, as_of)
    if not months or any(m not in cover_pct for m in months):
        return None
    return sum(cover_pct[m] / 100 * calendar.monthrange(int(m[:4]), int(m[4:]))[1] for m in months)


def density(rsn: dict[str, float], depth: dict[str, float], year: int, as_of: date) -> float | None:
    """Densest monthly mean snow (kg/m3) of the winter so far, over months with real snow on the ground."""
    months = snow_months(year, as_of)
    if not months or any(m not in rsn or m not in depth for m in months):
        return None
    snowy = [rsn[m] for m in months if depth[m] >= SNOW_MIN_M]
    return max(snowy) if snowy else None


def summer(series: dict[str, float], year: int) -> float | None:
    """July-August mean NDVI of the summer before the winter."""
    months = [f"{year}07", f"{year}08"]
    if any(m not in series for m in months):
        return None
    return sum(series[m] for m in months) / 2


def pressure_raw(stock_by_type: dict[str, float], area_km2: float) -> float | None:
    """log of sheep units per km2; stock is in thousand head."""
    su = sheep_units(stock_by_type)
    if su is None or su <= 0 or area_km2 <= 0:
        return None
    return math.log(su * 1000 / area_km2)


def pressure_by_soum(soums: list[dict], herds: dict, census: int) -> dict[str, float | None]:
    """log sheep units per km2. An aimag centre is a town: the herds registered there graze the aimag, so it takes
    the aimag's density rather than a town's 5,000-13,000 per km2, which clipped every centre at z = 3."""
    su = {s["pcode"]: sheep_units(herds.get((s["pcode"], census, "stock"), {})) for s in soums}
    aimag: dict[str, list[float]] = {}
    for s in soums:
        if su[s["pcode"]] is not None:
            tot = aimag.setdefault(s["aimag_pcode"], [0.0, 0.0])
            tot[0], tot[1] = tot[0] + su[s["pcode"]], tot[1] + s["area_km2"]
    out = {}
    for s in soums:
        pc = s["pcode"]
        if is_aimag_centre(s) and su[pc] is not None:
            a_su, a_km2 = aimag[s["aimag_pcode"]]
            out[pc] = math.log(a_su * 1000 / a_km2) if a_su > 0 else None
        else:
            out[pc] = pressure_raw(herds.get((pc, census, "stock"), {}), s["area_km2"])
    return out


def score_row(z: dict[str, float | None]) -> dict:
    r = risk(z)
    return {"n_indicators": sum(v is not None for v in z.values()), "risk": r,
            "risk_class": None if r is None else risk_class(r)}


def _anomaly(x: float | None, baseline: list) -> float | None:
    return None if x is None else zscore(x, [b for b in baseline if b is not None])


def _neg(z: float | None) -> float | None:
    return None if z is None else -z


def census_year(year: int, as_of: date) -> int:
    """The newest census out by as_of. Census Y is counted in December Y; taken as published from 1 Feb Y+1
    (NSO's date is unverified, and the later date can only understate an early stage, never leak)."""
    return year if as_of >= date(year + 1, 2, 1) else year - 1


@functools.cache
def _inputs() -> tuple:
    soums = [s for s in load_soums() if not s["is_ub"]]
    return soums, load_livestock(), load_era5(), load_series(GLDAS_CSV), load_series(NDVI_CSV)


def compute(year: int, as_of: date) -> dict[str, dict]:
    """Every soum's indicators and score for winter year/year+1, from what was published by as_of."""
    soums, herds, era5, gldas_s, ndvi_s = _inputs()
    census = census_year(year, as_of)
    pressure = pressure_by_soum(soums, herds, census)
    rows = {}
    for s in soums:
        pc = s["pcode"]
        then = {y: shift_as_of(as_of, y - year) for y in BASELINE}
        e5 = era5.get(pc, {"sde": {}, "rsn": {}, "snowc": {}, "t2m": {}})
        sde, gl = e5["sde"], gldas_s.get(pc, {})
        c = cold(e5["t2m"], year, as_of)
        sn = snow(sde, year, as_of)
        dn = density(e5["rsn"], sde, year, as_of)
        nd = summer(ndvi_s.get(pc, {}), year)
        p = pressure[pc]
        rows[pc] = {
            "pcode": pc, "cold_c": c, "snow_m": sn, "ndvi": nd,
            "z_cold": _neg(_anomaly(c, [cold(e5["t2m"], y, then[y]) for y in BASELINE])),
            "z_snow": _anomaly(sn, [snow(sde, y, then[y]) for y in BASELINE]),
            "z_snow_gldas": _anomaly(snow(gl, year, as_of), [snow(gl, y, then[y]) for y in BASELINE]),
            "snow_days": snow_days(e5["snowc"], year, as_of), "density_kgm3": dn,
            "z_density": _anomaly(dn, [density(e5["rsn"], sde, y, then[y]) for y in BASELINE]),
            "z_summer": _neg(_anomaly(nd, [summer(ndvi_s.get(pc, {}), y) for y in BASELINE])),
            "su_per_km2": None if p is None else math.exp(p), "p": p,
        }
    ps = [r["p"] for r in rows.values() if r["p"] is not None]
    for r in rows.values():
        p = r.pop("p")
        r["z_pressure"] = None if p is None else zscore(p, ps)
        r.update(score_row({k: r[f"z_{k}"] for k in ("cold", "snow", "summer", "pressure")}))
    return rows


def main(year: int, as_of: date | None = None) -> None:
    rows = compute(year, as_of or date(year + 1, 3, 31))
    missing = Counter(k for r in rows.values() for k in ("cold", "snow", "summer", "pressure") if r[f"z_{k}"] is None)
    hist = Counter(r["risk_class"] for r in rows.values())
    with out_path(year).open("w", newline="") as f:
        w = csv.DictWriter(f, COLUMNS)
        w.writeheader()
        for r in rows.values():
            w.writerow({k: ("" if r[k] is None else round(r[k], 4) if isinstance(r[k], float) else r[k]) for k in COLUMNS})
    scored = sum(r["risk"] is not None for r in rows.values())
    n4 = sum(r["n_indicators"] == 4 for r in rows.values())
    print(f"{year}/{(year + 1) % 100:02d}: {scored} scored ({n4} on all four), UB skipped; "
          f"missing {dict(missing)}; classes {dict(sorted(hist.items(), key=str))}")


def read_risk(year: int) -> dict[str, float]:
    with out_path(year).open() as f:
        return {r["pcode"]: float(r["risk"]) for r in csv.DictReader(f) if r["risk"]}


def check() -> None:
    assert winter_months(2023, date(2024, 1, 15)) == ["202311", "202312"]
    assert winter_months(2023, date(2024, 3, 31)) == ["202311", "202312", "202401", "202402"]
    assert winter_months(2023, date(2023, 11, 29)) == []
    assert shift_as_of(date(2024, 1, 15), -18) == date(2006, 1, 15)
    assert shift_as_of(date(2024, 2, 29), -1) == date(2023, 2, 28)
    assert shift_as_of(date(2023, 2, 28), -19) == date(2004, 2, 29), "a month's last day stays its last day"
    assert len(winter_months(2003, shift_as_of(date(2023, 2, 28), -19))) == 4
    t2m = {"202311": -10.0, "202312": -20.0, "202401": -30.0, "202402": -20.0}
    assert cold(t2m, 2023, date(2024, 3, 31)) == -20.0
    assert cold({k: v for k, v in t2m.items() if k != "202402"}, 2023, date(2024, 3, 31)) is None
    assert cold(t2m, 2023, date(2023, 11, 1)) is None
    full = {"camel": 0, "horse": 0, "cattle": 0, "sheep": 0, "goat": 0}
    assert pressure_raw(full, 100.0) is None
    assert pressure_raw({**full, "sheep": 1.0}, 1000.0) == 0.0  # 1 thousand sheep units on 1000 km2
    assert pressure_raw({"sheep": 1.0}, 1000.0) is None
    sn = {"202311": .1, "202312": .3, "202401": .2, "202402": .25, "202403": .05}
    assert snow(sn, 2023, date(2024, 3, 31)) == .3
    assert snow(sn, 2023, date(2023, 12, 31)) == .3
    assert snow({k: v for k, v in sn.items() if k != "202401"}, 2023, date(2024, 3, 31)) is None
    assert snow_months(2023, date(2024, 3, 31))[-1] == "202403"
    assert abs(summer({"202307": .4, "202308": .3}, 2023) - .35) < 1e-12
    assert summer({"202307": .4}, 2023) is None
    end = date(2024, 3, 31)
    cover = {"202311": 50, "202312": 100, "202401": 100, "202402": 100, "202403": 0}
    assert snow_days(cover, 2023, end) == 0.5 * 30 + 31 + 31 + 29
    assert snow_days({k: v for k, v in cover.items() if k != "202402"}, 2023, end) is None
    depth = {"202311": 0.0, "202312": 0.005, "202401": 0.2, "202402": 0.1, "202403": 0.0}
    rsn = {"202311": 400.0, "202312": 380.0, "202401": 300.0, "202402": 250.0, "202403": 100.0}
    assert density(rsn, depth, 2023, end) == 300.0  # bare-ground months carry a nominal density, never counted
    assert density(rsn, {k: 0.0 for k in depth}, 2023, end) is None
    assert census_year(2023, date(2024, 1, 31)) == 2022  # census 2023 is not out before 1 Feb 2024
    assert census_year(2023, date(2024, 2, 29)) == 2023
    assert census_year(2023, date(2023, 10, 31)) == 2022
    town = {"pcode": "MN4601", "aimag_pcode": "MN46", "area_km2": 10.0, "is_ub": False}
    rural = {"pcode": "MN4616", "aimag_pcode": "MN46", "area_km2": 990.0, "is_ub": False}
    herds = {("MN4601", 2025, "stock"): {**full, "sheep": 0.1}, ("MN4616", 2025, "stock"): {**full, "sheep": 0.9}}
    pr = pressure_by_soum([town, rural], herds, 2025)
    assert pr["MN4601"] == 0.0, "an aimag centre's herd grazes the aimag: 1000 sheep on 1000 km2"
    assert abs(pr["MN4616"] - math.log(900 / 990)) < 1e-12
    row = score_row({"cold": 1.0, "pressure": 0.0, "snow": None, "summer": None})
    assert row["n_indicators"] == 2 and abs(row["risk"] - 0.35 / 0.64) < 1e-12
    print("indicators check: ok")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--winter", type=int, default=2023, help="Y of winter Y/Y+1")
    a = ap.parse_args()
    check() if a.check else main(a.winter)
