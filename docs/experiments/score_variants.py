"""Run the pre-registered score variants (docs/experiments/2026-11-14-score-variants.md) on the published indicators.
uv run python docs/experiments/score_variants.py   (from the repository root; reads data/derived, writes nothing)"""
import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from pipeline import hindcast, validate  # noqa: E402
from pipeline.nso import load_livestock, sheep_units  # noqa: E402
from pipeline.score import WEIGHTS, zscore  # noqa: E402

YEARS = range(2011, 2025)                  # winters with soum losses
BASELINE = range(2001, 2021)               # winters 2001/02-2020/21, as indicators.BASELINE
W_NEW = 0.24                               # the smallest literature weight


def read(y):
    with Path(f"data/derived/indicators_{y}.csv").open(encoding="utf-8") as f:
        return {r["pcode"]: r for r in csv.DictReader(f)}


def num(v):
    return None if v in ("", None) else float(v)


def risk(z: dict, extra: float | None = None) -> float | None:
    used = {k: v for k, v in z.items() if v is not None}
    if not used:
        return None
    num_ = sum(WEIGHTS[k] * v for k, v in used.items())
    den = sum(WEIGHTS[k] for k in used)
    if extra is not None:
        num_, den = num_ + W_NEW * extra, den + W_NEW
    return num_ / den


def main():
    herds = load_livestock()
    normals = hindcast.normal_winters(herds)
    prereg = set(hindcast.DZUD + normals)
    rows = {y: read(y) for y in range(2001, 2025)}
    days_base = {}
    for y in BASELINE:
        for pc, r in rows[y].items():
            days_base.setdefault(pc, []).append(num(r["snow_days"]))

    out = {k: [] for k in ("published", "rebuilt", "E1", "E2")}
    stock = []
    for y in YEARS:
        for pc, r in rows[y].items():
            m = validate.mortality(herds, pc, y)
            pub = num(r["risk"])
            if m is None or pub is None:
                continue
            z = {"snow": num(r["z_snow"]), "cold": num(r["z_cold"]), "pressure": num(r["z_pressure"]), "summer": num(r["z_summer"])}
            zs, zm = z["snow"], z["summer"]
            x = None if zs is None or zm is None else min(3.0, max(zs, 0) * max(zm, 0))
            d = num(r["snow_days"])
            zd = None if d is None else zscore(d, [b for b in days_base.get(pc, []) if b is not None])
            for k, v in (("published", pub), ("rebuilt", risk(z)), ("E1", risk(z, x)), ("E2", risk(z, zd))):
                out[k].append((y, v, m))
            stock.append(sheep_units(herds.get((pc, y, "stock"), {})))

    def rho(pairs, keep=lambda i: True):
        sel = [(v, m) for i, (y, v, m) in enumerate(pairs) if keep(i)]
        return validate.spearman([v for v, _ in sel], [m for _, m in sel]), len(sel)

    def both(pairs, keep=lambda i: True):
        pre = rho(pairs, lambda i: pairs[i][0] in prereg and keep(i))
        every = rho(pairs, keep)
        return pre, every

    print(f"pre-registered winters {sorted(prereg)}")
    res = {k: both(v) for k, v in out.items()}
    for k, ((p, pn), (e, en)) in res.items():
        print(f"{k:9s} pre-registered {p:.3f} (n {pn})   every soum-winter {e:.3f} (n {en})")
    (p0, _), (e0, _) = res["published"]
    if round(p0, 3) != 0.600 or round(e0, 3) != 0.440:
        sys.exit("baseline not reproduced; stop")
    for k in ("E1", "E2"):
        (p, _), (e, _) = res[k]
        kept = round(p, 3) > 0.600 and round(e, 3) > 0.440
        print(f"{k}: {'KEPT' if kept else 'not used'} (pre-registered {p:.3f} vs 0.600, every {e:.3f} vs 0.440)")
    cut = sorted(s for s in stock if s is not None)[len(stock) // 10]
    big = lambda i: stock[i] is not None and stock[i] >= cut  # noqa: E731
    (p, pn), (e, en) = both(out["published"], big)
    print(f"E3 (herds >= {cut:,.0f} thousand sheep units, the smallest 10% left out): pre-registered {p:.3f} (n {pn}), every {e:.3f} (n {en})")


if __name__ == "__main__":
    main()
