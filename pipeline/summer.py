"""ERA5-Land May-August precipitation and 2 m temperature per soum, for Resolution 286's summer drought (annex 5,
2.2-2.3: precipitation against its long-term mean and temperature against its own, over the growing season).
One file holds every summer from 2000 (the summer before winter 2000/01) to the last one whose August is in.
In the monthly means, total precipitation is a mean daily amount in metres; a month's total is that times its days."""
import calendar
import csv
import sys
from datetime import date
from pathlib import Path

import netCDF4
import numpy as np

from pipeline import era5
from pipeline.gldas import map_cells, soum_means
from pipeline.http import cached, cds_retrieve

FIRST = 2000
# ERA5-Land monthly means come about two months late: August is in by November
LAST = date.today().year if date.today().month >= 11 else date.today().year - 1
DATASET = era5.DATASET
INPUTS = {**era5.INPUTS, "variable": ["total_precipitation", "2m_temperature"], "month": ["05", "06", "07", "08"],
          "year": [str(y) for y in range(FIRST, LAST + 1)]}
RAW = era5.RAW / f"era5_land_summer_{FIRST}_{LAST}.nc"
OUT = Path("data/derived/soum_summer.csv")
COLS = {"tp": "tp_mm", "t2m": "t2m_c"}


def monthly_total_mm(rate_m: float, yyyymm: str) -> float:
    """A month's precipitation in mm from ERA5-Land's mean daily amount in metres."""
    days = calendar.monthrange(int(yyyymm[:4]), int(yyyymm[4:]))[1]
    return round(rate_m * days * 1000, 1)


def main() -> None:
    RAW.parent.mkdir(parents=True, exist_ok=True)
    cached(RAW, lambda: cds_retrieve(DATASET, INPUTS))
    with netCDF4.Dataset(RAW) as d:
        times = [era5.yyyymm(t) for t in d["valid_time"][:]]
        grids = {v: d[v][:] for v in COLS}
        lats, lons = d["latitude"][:].data, d["longitude"][:].data
    cells = map_cells(grids["t2m"][0], lats, lons)
    rows = []
    for i, ym in enumerate(times):
        tp, t2m = soum_means(grids["tp"][i], cells), soum_means(grids["t2m"][i], cells)
        for pcode in cells:
            if tp[pcode] is not None and t2m[pcode] is not None:
                rows.append((pcode, ym, monthly_total_mm(tp[pcode], ym), round(era5.to_celsius(t2m[pcode]), 3)))
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["pcode", "yyyymm", *COLS.values()])
        w.writerows(rows)
    print(f"{len(times)} months, {len(cells)} soums, {len(rows)} rows -> {OUT}")


def load_summer(path: Path = OUT) -> dict[str, dict[str, dict[str, float]]]:
    """pcode -> {"tp_mm": {yyyymm: mm}, "t2m_c": {yyyymm: °C}}."""
    out: dict[str, dict[str, dict[str, float]]] = {}
    with path.open(encoding="utf-8") as f:
        for r in csv.DictReader(f):
            s = out.setdefault(r["pcode"], {c: {} for c in COLS.values()})
            for c in COLS.values():
                s[c][r["yyyymm"]] = float(r[c])
    return out


def check() -> None:
    assert monthly_total_mm(0.002, "202407") == 62.0          # 2 mm a day, 31 days
    assert monthly_total_mm(0.001, "202406") == 30.0          # 30 days
    assert INPUTS["month"] == ["05", "06", "07", "08"]
    assert INPUTS["variable"] == ["total_precipitation", "2m_temperature"]
    assert INPUTS["year"][0] == "2000" and INPUTS["area"] == era5.INPUTS["area"]
    print("summer check: ok")


if __name__ == "__main__":
    check() if "--check" in sys.argv else main()
