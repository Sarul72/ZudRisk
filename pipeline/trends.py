"""Greenness trend: the Theil-Sen slope of each soum's July-August NDVI, per decade. A desertification proxy (pasture
greening or browning since 2001), not the official desertification map."""
import json
import statistics
import sys

from pipeline.export import SITE
from pipeline.gldas import load_series
from pipeline.indicators import NDVI_CSV, summer

FIRST = 2001
MIN_SUMMERS = 10  # under ten points a median slope is mostly the two wettest summers


def theil_sen(xs: list[float], ys: list[float]) -> float:
    return statistics.median((ys[j] - ys[i]) / (xs[j] - xs[i])
                             for i in range(len(xs)) for j in range(i + 1, len(xs)) if xs[j] != xs[i])


def greenness_trend(series: dict[str, float], through: int) -> float | None:
    """NDVI change per decade over the summers FIRST..through; None under MIN_SUMMERS summers."""
    pts = [(y, v) for y in range(FIRST, through + 1) if (v := summer(series, y)) is not None]
    if len(pts) < MIN_SUMMERS:
        return None
    return 10 * theil_sen([y for y, _ in pts], [v for _, v in pts])


def latest_summer(ndvi: dict[str, dict[str, float]]) -> int:
    return max(int(m[:4]) for s in ndvi.values() for m in s if m.endswith("08"))


def main() -> None:
    ndvi = load_series(NDVI_CSV)
    through = latest_summer(ndvi)
    trend = {pc: round(t, 4) for pc, s in ndvi.items() if (t := greenness_trend(s, through)) is not None}
    (SITE / "greenness.json").write_text(json.dumps({"from": FIRST, "through": through, "per_decade": trend}), encoding="utf-8")
    v = sorted(trend.values())
    print(f"greenness {FIRST}-{through}: {len(trend)} soums, median {v[len(v) // 2]:+.4f}/decade, "
          f"{sum(x < 0 for x in v)} browning, range {v[0]:+.3f} to {v[-1]:+.3f}")


def check() -> None:
    xs = list(range(2001, 2013))
    line = {x: 0.3 + 0.002 * (x - 2001) for x in xs}
    assert abs(theil_sen(list(line), list(line.values())) - 0.002) < 1e-12
    spiked = {**line, 2005: 0.9}  # one wet summer moves least squares, not the median slope
    assert abs(theil_sen(list(spiked), list(spiked.values())) - 0.002) < 1e-12
    series = {f"{x}{m}": v for x, v in line.items() for m in ("07", "08")}
    assert abs(greenness_trend(series, 2012) - 0.02) < 1e-12, "per decade"
    late = {**series, "201307": 0.0, "201308": 0.0}
    assert greenness_trend(late, 2012) == greenness_trend(series, 2012), "a summer after `through` is never read"
    short = {k: v for k, v in series.items() if k < "2010"}
    assert greenness_trend(short, 2012) is None, f"fewer than {MIN_SUMMERS} summers is no trend"
    print("trends check: ok")


if __name__ == "__main__":
    check() if "--check" in sys.argv else main()
