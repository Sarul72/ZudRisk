"""The trend numbers quoted on the pitch deck's trend slide, recomputed from the repository's data.
uv run python docs/pitch/trend_facts.py   (from the repository root; reads data/derived and site/data, writes nothing)

Descriptive only: no new score, nothing here changes the site. Mann-Kendall is the standard test that goes with a
Theil-Sen slope (two-sided, normal approximation, no tie correction; the NDVI values carry four decimals)."""
import json
import math
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from pipeline.gldas import load_series  # noqa: E402
from pipeline.indicators import NDVI_CSV, summer  # noqa: E402
from pipeline.nso import load_livestock_aimag, sheep_units  # noqa: E402
from pipeline.trends import FIRST, greenness_trend, latest_summer  # noqa: E402


def mann_kendall_p(ys: list[float]) -> float:
    n = len(ys)
    s = sum((ys[j] > ys[i]) - (ys[j] < ys[i]) for i in range(n) for j in range(i + 1, n))
    var = n * (n - 1) * (2 * n + 5) / 18
    z = 0.0 if s == 0 else (s - (1 if s > 0 else -1)) / math.sqrt(var)
    return math.erfc(abs(z) / math.sqrt(2))


def main() -> None:
    ndvi = load_series(NDVI_CSV)
    through = latest_summer(ndvi)
    aimag_names = {f["properties"]["pcode"]: f["properties"].get("name_en") or f["properties"].get("name")
                   for f in json.loads(Path("site/data/aimags.geojson").read_text(encoding="utf-8"))["features"]}

    rows = []
    for pc, s in ndvi.items():
        ys = [v for y in range(FIRST, through + 1) if (v := summer(s, y)) is not None]
        t = greenness_trend(s, through)
        if t is None:
            continue
        rel = t * (through - FIRST) / 10 / statistics.mean(ys)  # change over the whole period, share of the mean
        rows.append((pc, t, rel, mann_kendall_p(ys)))
    n = len(rows)
    up = [r for r in rows if r[1] > 0]
    down = [r for r in rows if r[1] < 0]
    sig_up = [r for r in up if r[3] < 0.05]
    sig_down = [r for r in down if r[3] < 0.05]
    print(f"greenness {FIRST}-{through}: {n} soums; median {statistics.median(r[1] for r in rows):+.4f} NDVI/decade, "
          f"median change over the period {statistics.median(r[2] for r in rows):+.1%}")
    print(f"  greener {len(up)} ({len(up) / n:.0%}), significant p<0.05: {len(sig_up)} ({len(sig_up) / n:.0%})")
    print(f"  browner {len(down)}, significant p<0.05: {len(sig_down)}")
    by_aimag = {}
    for pc, *_ in down:
        by_aimag[aimag_names.get(pc[:4], pc[:4])] = by_aimag.get(aimag_names.get(pc[:4], pc[:4]), 0) + 1
    print("  browner soums by aimag:", dict(sorted(by_aimag.items(), key=lambda kv: -kv[1])))

    herds = load_livestock_aimag()
    su = {}
    for (ap, y, kind), by_type in herds.items():
        if kind == "stock" and ap != "MN11" and (v := sheep_units(by_type)) is not None:  # MN11 Ulaanbaatar, as the deck's losses chart
            su.setdefault(y, []).append(v)
    full = {y: sum(v) for y, v in su.items() if len(v) == max(len(x) for x in su.values())}
    y0, y1 = min(full), max(full)
    print(f"herd, all aimags excl. Ulaanbaatar, sheep units (thousand): {y0} {full[y0]:,.0f}, {y1} {full[y1]:,.0f}, "
          f"x{full[y1] / full[y0]:.2f}")


if __name__ == "__main__":
    main()
