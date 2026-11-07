"""Indicators per soum and winter: winter cold (NASA POWER), snow (GLDAS), summer pasture (MODIS NDVI)
and grazing pressure (NSO herds), each as a z-score where higher means riskier, then the score (spec 4.3-4.4)."""
import argparse
import csv
import json
import math
from collections import Counter, defaultdict
from datetime import date, timedelta
from pathlib import Path

from pipeline.boundaries import load_soums
from pipeline.gldas import OUT as SNOW_CSV, load_series
from pipeline.ndvi import OUT as NDVI_CSV
from pipeline.nso import load_livestock, sheep_units
from pipeline.power import CELLS, T2M
from pipeline.score import risk, risk_class, zscore

BASELINE = range(2001, 2021)  # winters 2001/02 .. 2020/21, summers 2001 .. 2020
COLUMNS = ["pcode", "cold_c", "z_cold", "snow_m", "z_snow", "ndvi", "z_summer", "su_per_km2", "z_pressure",
           "n_indicators", "risk", "risk_class"]


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
    """The same calendar day in another winter, so a baseline winter sees the same months as the scored one."""
    try:
        return as_of.replace(year=as_of.year + years)
    except ValueError:  # 29 February in a non-leap year
        return as_of.replace(year=as_of.year + years, day=28)


def cold(cells: list, t2m: dict, year: int, as_of: date) -> float | None:
    """Mean 2 m air temperature over the soum's grid points and the winter months; None if any value is missing."""
    months = winter_months(year, as_of)
    if not months:
        return None
    values = []
    for p in cells:
        series = t2m.get(tuple(p), {})
        for m in months:
            if m not in series:
                return None
            values.append(series[m])
    return sum(values) / len(values)


def snow(series: dict[str, float], year: int, as_of: date) -> float | None:
    """Deepest monthly mean snow of the winter so far (m); None if any month is missing."""
    months = snow_months(year, as_of)
    if not months or any(m not in series for m in months):
        return None
    return max(series[m] for m in months)


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


def score_row(z: dict[str, float | None]) -> dict:
    r = risk(z)
    return {"n_indicators": sum(v is not None for v in z.values()), "risk": r,
            "risk_class": None if r is None else risk_class(r)}


def _anomaly(x: float | None, baseline: list) -> float | None:
    return None if x is None else zscore(x, [b for b in baseline if b is not None])


def _neg(z: float | None) -> float | None:
    return None if z is None else -z


def load_t2m() -> dict:
    t2m: dict = defaultdict(dict)
    with T2M.open() as f:
        for r in csv.DictReader(f):
            t2m[(float(r["lon"]), float(r["lat"]))][r["yyyymm"]] = float(r["t2m"])
    return t2m


def main(year: int, as_of: date | None = None) -> None:
    as_of = as_of or date(year + 1, 3, 31)
    all_soums = load_soums()
    soums = [s for s in all_soums if not s["is_ub"]]
    herds = load_livestock()
    t2m = load_t2m()
    cells = json.loads(CELLS.read_text())
    snow_s, ndvi_s = load_series(SNOW_CSV), load_series(NDVI_CSV)
    rows, missing = {}, Counter()
    for s in soums:
        pc = s["pcode"]
        then = {y: shift_as_of(as_of, y - year) for y in BASELINE}
        c = cold(cells[pc], t2m, year, as_of)
        sn = snow(snow_s.get(pc, {}), year, as_of)
        nd = summer(ndvi_s.get(pc, {}), year)
        p = pressure_raw(herds.get((pc, year, "stock"), {}), s["area_km2"])
        rows[pc] = {
            "pcode": pc, "cold_c": c, "snow_m": sn, "ndvi": nd,
            "z_cold": _neg(_anomaly(c, [cold(cells[pc], t2m, y, then[y]) for y in BASELINE])),
            "z_snow": _anomaly(sn, [snow(snow_s.get(pc, {}), y, then[y]) for y in BASELINE]),
            "z_summer": _neg(_anomaly(nd, [summer(ndvi_s.get(pc, {}), y) for y in BASELINE])),
            "su_per_km2": None if p is None else math.exp(p), "p": p,
        }
    ps = [r["p"] for r in rows.values() if r["p"] is not None]
    hist = Counter()
    for r in rows.values():
        p = r.pop("p")
        r["z_pressure"] = None if p is None else zscore(p, ps)
        z = {"cold": r["z_cold"], "snow": r["z_snow"], "summer": r["z_summer"], "pressure": r["z_pressure"]}
        missing.update(k for k, v in z.items() if v is None)
        r.update(score_row(z))
        hist[r["risk_class"]] += 1
    with out_path(year).open("w", newline="") as f:
        w = csv.DictWriter(f, COLUMNS)
        w.writeheader()
        for r in rows.values():
            w.writerow({k: ("" if r[k] is None else round(r[k], 4) if isinstance(r[k], float) else r[k]) for k in COLUMNS})
    scored = sum(r["risk"] is not None for r in rows.values())
    n4 = sum(r["n_indicators"] == 4 for r in rows.values())
    print(f"{year}/{(year + 1) % 100:02d}: {scored} scored ({n4} on all four), {len(all_soums) - len(soums)} UB skipped; "
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
    t2m = {(1, 2): {"202311": -10.0, "202312": -20.0, "202401": -30.0, "202402": -20.0},
           (3, 4): {"202311": -12.0, "202312": -22.0, "202401": -32.0}}  # Feb fill value was dropped
    assert cold([(1, 2)], t2m, 2023, date(2024, 3, 31)) == -20.0
    assert cold([(1, 2), (3, 4)], t2m, 2023, date(2024, 3, 31)) is None
    assert cold([(1, 2)], t2m, 2023, date(2023, 11, 1)) is None
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
    row = score_row({"cold": 1.0, "pressure": 0.0, "snow": None, "summer": None})
    assert row["n_indicators"] == 2 and abs(row["risk"] - 0.35 / 0.64) < 1e-12
    print("indicators check: ok")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--winter", type=int, default=2023, help="Y of winter Y/Y+1")
    a = ap.parse_args()
    check() if a.check else main(a.winter)
