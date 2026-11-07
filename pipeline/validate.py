"""Compare a winter's risk scores with what happened: NSO adult losses over the previous census (spec 4.5)."""
import argparse
import csv
import json
from pathlib import Path

import numpy as np

from pipeline.boundaries import load_soums
from pipeline.indicators import out_path
from pipeline.nso import load_livestock, sheep_units


TOP_SHARE = 0.2


def _ranks(a: list[float]) -> np.ndarray:
    a = np.asarray(a, dtype=float)
    r = np.empty(len(a))
    r[a.argsort(kind="stable")] = np.arange(1, len(a) + 1)
    for v in np.unique(a):  # ties share their mean rank
        r[a == v] = r[a == v].mean()
    return r


def spearman(x: list[float], y: list[float]) -> float | None:
    """None where a rank correlation is undefined: fewer than 3 pairs, or a series with no spread."""
    if len(x) < 3 or len(set(x)) < 2 or len(set(y)) < 2:
        return None
    return float(np.corrcoef(_ranks(x), _ranks(y))[0, 1])


def mortality(herds: dict, pcode: str, year: int) -> float | None:
    """Adult losses in year+1 over the census of year, both in sheep units."""
    stock = sheep_units(herds.get((pcode, year, "stock"), {}))
    loss = sheep_units(herds.get((pcode, year + 1, "loss"), {}))
    if stock is None or loss is None or stock <= 0:
        return None
    return loss / stock


def top_quintile_hit(risk: list[float], mort: list[float]) -> float:
    """Share of the top-20 % risk soums that are also in the top-20 % mortality soums."""
    k = max(1, round(len(risk) * TOP_SHARE))
    top_r = set(np.argsort(risk, kind="stable")[-k:])
    top_m = set(np.argsort(mort, kind="stable")[-k:])
    return len(top_r & top_m) / k


def _r(v: float | None, d: int) -> float | None:
    return None if v is None else round(v, d)


def summarize(pairs: list[tuple], by_aimag: dict[str, list], dropped: dict[str, int]) -> dict:
    """The numbers the site shows; null wherever too few soums survive to compute one."""
    risk_s = [r for r, _ in pairs]
    mort_s = [m for _, m in pairs]
    a_risk = [sum(r * st for r, st, _ in v) / sum(st for _, st, _ in v) for v in by_aimag.values()]
    a_mort = [sum(l for _, _, l in v) / sum(st for _, st, _ in v) for v in by_aimag.values()]
    tot_stock = sum(st for v in by_aimag.values() for _, st, _ in v)
    tot_loss = sum(l for v in by_aimag.values() for _, _, l in v)
    return {
        "n": len(pairs),
        "n_dropped": sum(dropped.values()),
        "dropped_reasons": dropped,
        "spearman_soum": _r(spearman(risk_s, mort_s), 3),
        "n_aimag": len(by_aimag),
        "spearman_aimag": _r(spearman(a_risk, a_mort), 3),
        "top_quintile_hit": _r(top_quintile_hit(risk_s, mort_s), 3) if pairs else None,
        # over the validated soums only, Ulaanbaatar excluded
        "mortality_pct_validated": _r(100 * tot_loss / tot_stock, 2) if tot_stock else None,
    }


def out_path_json(year: int) -> Path:
    return Path(f"data/derived/validation_{year}.json")


def main(year: int) -> None:
    herds = load_livestock()
    soums = {s["pcode"]: s for s in load_soums() if not s["is_ub"]}
    with out_path(year).open() as f:
        scores = {r["pcode"]: float(r["risk"]) for r in csv.DictReader(f) if r["risk"]}
    pairs, dropped = [], {"unscored": len(soums) - len(scores), "no mortality": 0}
    by_aimag: dict[str, list] = {}
    for pcode, r in scores.items():
        m = mortality(herds, pcode, year)
        if m is None:
            dropped["no mortality"] += 1
            continue
        pairs.append((r, m))
        stock = sheep_units(herds[(pcode, year, "stock")])
        loss = sheep_units(herds[(pcode, year + 1, "loss")])
        by_aimag.setdefault(soums[pcode]["aimag_pcode"], []).append((r, stock, loss))
    result = {"winter": f"{year}/{(year + 1) % 100:02d}", "indicators_used": ["cold", "pressure"],
              **summarize(pairs, by_aimag, dropped)}
    out_path_json(year).write_text(json.dumps(result, indent=2, ensure_ascii=False, allow_nan=False))
    print(json.dumps(result, indent=2, ensure_ascii=False))


def check() -> None:
    assert abs(spearman([1, 2, 3, 4], [10, 20, 30, 40]) - 1.0) < 1e-12
    assert abs(spearman([1, 2, 3, 4], [4, 3, 2, 1]) + 1.0) < 1e-12
    assert round(spearman([1, 1, 2], [1, 2, 3]), 3) == 0.866
    full = {"camel": 0, "horse": 0, "cattle": 0, "sheep": 10.0, "goat": 0}
    herds = {("A", 2023, "stock"): full, ("A", 2024, "loss"): {**full, "sheep": 1.0},
             ("B", 2023, "stock"): {**full, "sheep": 0.0}, ("B", 2024, "loss"): full}
    assert mortality(herds, "A", 2023) == 0.1
    assert mortality(herds, "B", 2023) is None  # stock 0
    assert mortality(herds, "C", 2023) is None  # no census
    assert top_quintile_hit([1, 2, 3, 4, 5, 6, 7, 8, 9, 10], [1, 2, 3, 4, 5, 6, 7, 8, 10, 9]) == 1.0
    assert top_quintile_hit([1, 2, 3, 4, 5, 6, 7, 8, 9, 10], [10, 9, 8, 7, 6, 5, 4, 3, 2, 1]) == 0.0
    assert spearman([1, 2, 3], [5, 5, 5]) is None  # constant series has no rank correlation
    assert spearman([1, 2], [1, 2]) is None
    empty = summarize([], {}, {"unscored": 3, "no mortality": 0})
    assert empty["n"] == 0 and empty["spearman_soum"] is None and empty["n_dropped"] == 3
    json.dumps(empty, allow_nan=False)
    print("validate check: ok")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--winter", type=int, default=2023)
    a = ap.parse_args()
    check() if a.check else main(a.winter)
