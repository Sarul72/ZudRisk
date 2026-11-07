"""v0.1 indicators per soum and winter: winter cold (NASA POWER) and grazing pressure (NSO herds)."""
import argparse
import csv
import json
import math
from collections import Counter, defaultdict
from datetime import date, timedelta
from pathlib import Path

from pipeline.boundaries import load_soums
from pipeline.nso import load_livestock, sheep_units
from pipeline.power import CELLS, T2M
from pipeline.score import risk, risk_class, zscore

BASELINE = range(2001, 2021)  # winters 2001/02 .. 2020/21
COLUMNS = ["pcode", "cold_c", "z_cold", "su_per_km2", "z_pressure", "risk", "risk_class"]


def out_path(year: int) -> Path:
    return Path(f"data/derived/indicators_{year}.csv")


def winter_months(year: int, as_of: date) -> list[str]:
    """Nov-Feb of winter year/year+1, keeping only months already over on as_of."""
    months = [(year, 11), (year, 12), (year + 1, 1), (year + 1, 2)]
    out = []
    for y, m in months:
        last_day = date(y + (m == 12), m % 12 + 1, 1) - timedelta(days=1)
        if last_day <= as_of:
            out.append(f"{y}{m:02d}")
    return out


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


def pressure_raw(stock_by_type: dict[str, float], area_km2: float) -> float | None:
    """log of sheep units per km2; stock is in thousand head."""
    su = sheep_units(stock_by_type)
    if su is None or su <= 0 or area_km2 <= 0:
        return None
    return math.log(su * 1000 / area_km2)


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
    rows, why = {}, Counter()
    for s in soums:
        c = cold(cells[s["pcode"]], t2m, year, as_of)
        base = [b for b in (cold(cells[s["pcode"]], t2m, y, shift_as_of(as_of, y - year)) for y in BASELINE) if b is not None]
        z = zscore(c, base) if c is not None else None
        stock = herds.get((s["pcode"], year, "stock"), {})
        p = pressure_raw(stock, s["area_km2"])
        if c is None: why["no cold"] += 1
        if p is None: why["no herd"] += 1
        rows[s["pcode"]] = {"pcode": s["pcode"], "cold_c": c, "z_cold": None if z is None else -z,
                            "su_per_km2": None if p is None else math.exp(p), "p": p}
    ps = [r["p"] for r in rows.values() if r["p"] is not None]
    hist = Counter()
    for r in rows.values():
        r["z_pressure"] = zscore(r.pop("p"), ps) if r["su_per_km2"] is not None else None
        r["risk"] = risk({"cold": r["z_cold"], "pressure": r["z_pressure"]})
        r["risk_class"] = None if r["risk"] is None else risk_class(r["risk"])
        hist[r["risk_class"]] += 1
    with out_path(year).open("w", newline="") as f:
        w = csv.DictWriter(f, COLUMNS)
        w.writeheader()
        for r in rows.values():
            w.writerow({k: ("" if r[k] is None else round(r[k], 4) if isinstance(r[k], float) else r[k]) for k in COLUMNS})
    scored = sum(r["risk"] is not None for r in rows.values())
    print(f"{scored} scored, {len(all_soums) - len(soums)} UB skipped; unscored inputs {dict(why)}; classes {dict(sorted(hist.items(), key=str))}")


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
    print("indicators check: ok")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--winter", type=int, default=2023, help="Y of winter Y/Y+1")
    a = ap.parse_args()
    check() if a.check else main(a.winter)
