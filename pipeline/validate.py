"""Compare a winter's risk scores with what happened: NSO adult losses over the previous census (spec 4.5)."""
import argparse
import csv
import json
from pathlib import Path

import numpy as np

from pipeline.boundaries import load_soums
from pipeline.indicators import out_path
from pipeline.nso import load_livestock, load_livestock_aimag, sheep_units


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


def out_path_json(year: int) -> Path:
    return Path(f"data/derived/validation_{year}.json")


def aimag_pairs(year: int, scores: dict[str, tuple[float, str]], herds: dict, aherds: dict) -> list[tuple]:
    """(aimag, herd-weighted risk of its soums, NSO's aimag mortality) for each aimag with both."""
    by_aimag: dict[str, list[tuple[float, float]]] = {}
    for pcode, (r, aimag) in scores.items():
        stock = sheep_units(herds.get((pcode, year, "stock"), {}))
        if stock:
            by_aimag.setdefault(aimag, []).append((r, stock))
    out = []
    for aimag, v in sorted(by_aimag.items()):
        am = mortality(aherds, aimag, year)
        if am is not None:
            out.append((aimag, sum(r * st for r, st in v) / sum(st for _, st in v), am))
    return out


def pooled_aimag(rows: list[tuple]) -> dict:
    """Spearman over every aimag-winter (winter, risk, mortality): the only test reaching back before soum losses."""
    return {"n": len(rows), "winters": sorted({y for y, _, _ in rows}),
            "spearman": spearman([r for _, r, _ in rows], [m for _, _, m in rows])}


def evaluate(year: int, scores: dict[str, tuple[float, str]], herds: dict, aherds: dict,
             normals: list[int]) -> dict:
    """Score against losses at soum level where NSO has soum losses, and always at aimag level from NSO's aimag rows."""
    pairs, excess_pairs, dropped, n_losses = [], [], {"no mortality": 0}, 0
    by_aimag: dict[str, list[tuple[float, float]]] = {}
    for pcode, (r, aimag) in scores.items():
        n_losses += (pcode, year + 1, "loss") in herds
        stock = sheep_units(herds.get((pcode, year, "stock"), {}))
        if stock:
            by_aimag.setdefault(aimag, []).append((r, stock))
        m = mortality(herds, pcode, year)
        if m is None:
            dropped["no mortality"] += 1
            continue
        pairs.append((r, m))
        normal = [x for x in (mortality(herds, pcode, n) for n in normals) if x is not None]
        if normal:
            excess_pairs.append((r, m - sum(normal) / len(normal)))
    pairs_a = aimag_pairs(year, scores, herds, aherds)
    a_risk, a_mort = [r for _, r, _ in pairs_a], [m for _, _, m in pairs_a]
    a_loss = sum(sheep_units(aherds.get((a, year + 1, "loss"), {})) or 0 for a in by_aimag)
    a_stock = sum(sheep_units(aherds.get((a, year, "stock"), {})) or 0 for a in by_aimag)
    risk_s, mort_s = [r for r, _ in pairs], [m for _, m in pairs]
    return {
        "validation_unit": "soum+aimag" if pairs else "aimag",
        "n": len(pairs),
        "n_soum_losses": n_losses,
        "n_dropped": sum(dropped.values()),
        "dropped_reasons": dropped,
        "spearman_soum": _r(spearman(risk_s, mort_s), 3),
        "excess_spearman_soum": _r(spearman(*map(list, zip(*excess_pairs))), 3) if excess_pairs else None,
        "top_quintile_hit": _r(top_quintile_hit(risk_s, mort_s), 3) if pairs else None,
        "n_aimag": len(a_risk),
        "spearman_aimag": _r(spearman(a_risk, a_mort), 3),
        # NSO aimag totals, Ulaanbaatar excluded
        "mortality_pct": _r(100 * a_loss / a_stock, 2) if a_stock else None,
    }


def pooled(rows: list[tuple]) -> dict:
    """Spearman over every soum-winter: asks whether scores rise in dzud years, which one winter cannot show."""
    ex = [(r, e) for _, _, r, _, e in rows if e is not None]
    return {
        "n": len(rows),
        "winters": sorted({y for _, y, _, _, _ in rows}),
        "spearman": spearman([r for _, _, r, _, _ in rows], [m for _, _, _, m, _ in rows]),
        "n_excess": len(ex),
        "spearman_excess": spearman([r for r, _ in ex], [e for _, e in ex]),
    }


def pooled_rows(year: int, risk: dict[str, float], herds: dict, normals: list[int]) -> list[tuple]:
    """(pcode, winter, risk, mortality, excess) for each scored soum with losses; excess is None without a normal winter."""
    rows = []
    for pcode, r in risk.items():
        m = mortality(herds, pcode, year)
        if m is None:
            continue
        normal = [x for x in (mortality(herds, pcode, n) for n in normals) if x is not None]
        rows.append((pcode, year, r, m, m - sum(normal) / len(normal) if normal else None))
    return rows


def rounded(d: dict) -> dict:
    return {k: (round(v, 3) if isinstance(v, float) else v) for k, v in d.items()}


def main(year: int, normals: list[int] = ()) -> dict:
    herds, aherds = load_livestock(), load_livestock_aimag()
    soums = {s["pcode"]: s for s in load_soums()}
    with out_path(year).open(encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    scores = {r["pcode"]: (float(r["risk"]), soums[r["pcode"]]["aimag_pcode"]) for r in rows if r["risk"]}
    used = sorted({k for r in rows for k in ("cold", "snow", "summer", "pressure") if r[f"z_{k}"]})
    result = {"winter": f"{year}/{(year + 1) % 100:02d}", "indicators_used": used, "normal_winters": list(normals),
              "n_unscored": len(soums) - len(scores), **evaluate(year, scores, herds, aherds, list(normals))}
    out_path_json(year).write_text(json.dumps(result, indent=2, ensure_ascii=False, allow_nan=False), encoding="utf-8")
    return result


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
    st = {**full, "sheep": 100.0}
    herds09 = {(p, 2009, "stock"): st for p in "ABC"}  # 2009 census, no 2010 soum losses
    aherds = {}
    for a, lost in (("X", 1.0), ("Y", 5.0), ("Z", 9.0)):
        aherds[(a, 2009, "stock")], aherds[(a, 2010, "loss")] = st, {**full, "sheep": lost}
    res = evaluate(2009, {"A": (0.1, "X"), "B": (0.5, "Y"), "C": (0.9, "Z")}, herds09, aherds, [])
    assert res["spearman_soum"] is None and res["validation_unit"] == "aimag" and res["n_soum_losses"] == 0, res
    assert res["spearman_aimag"] == 1.0 and res["n_aimag"] == 3 and res["mortality_pct"] == 5.0, res
    json.dumps(res, allow_nan=False)
    pairs = aimag_pairs(2009, {"A": (0.1, "X"), "B": (0.5, "Y"), "C": (0.9, "Z")}, herds09, aherds)
    assert pairs == [("X", 0.1, 0.01), ("Y", 0.5, 0.05), ("Z", 0.9, 0.09)], pairs
    rows = [(2009, r, m) for _, r, m in pairs] + [(2010, 0.2, 0.09), (2010, 0.3, 0.01)]
    pa = pooled_aimag(rows)
    assert pa["n"] == 5 and pa["winters"] == [2009, 2010] and pa["spearman"] == spearman([.1, .5, .9, .2, .3], [.01, .05, .09, .09, .01]), pa
    print("validate check: ok")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--winter", type=int, default=2023)
    a = ap.parse_args()
    check() if a.check else print(json.dumps(main(a.winter), indent=2, ensure_ascii=False))
