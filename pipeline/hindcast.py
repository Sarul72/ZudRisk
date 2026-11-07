"""Score and validate every hindcast winter, then the pooled test across them (spec 4.5)."""
import json
import sys
from pathlib import Path

from pipeline import aimags, asof, compare, export, indicators, validate
from pipeline.nso import load_livestock, sheep_units
from pipeline.validate import pooled, pooled_rows, rounded

DZUD = [2009, 2015, 2022, 2023]
NORMAL_FROM, NORMAL_TO = 2011, 2023  # soum-level losses start in 2012; kept to 2023 so the normals stay the pre-registered pair
WINTERS = [2009] + list(range(2011, 2025))  # every winter NSO has soum losses for (2012-2025), plus the 2009/10 dzud
POOLED = Path("data/derived/pooled.json")


def national_mortality(herds: dict, year: int) -> float | None:
    """Over soums with a complete census and complete losses only: a soum counted for losses but not stock inflates it."""
    stock = loss = 0.0
    for (pcode, y, kind), by_type in herds.items():
        if y != year or kind != "stock":
            continue
        st, lo = sheep_units(by_type), sheep_units(herds.get((pcode, year + 1, "loss"), {}))
        if st and lo is not None:
            stock, loss = stock + st, loss + lo
    return loss / stock if stock else None


def normal_winters(herds: dict) -> list[int]:
    """The two calmest non-dzud winters with soum-level losses, fixed by rule before any scoring."""
    m = {y: national_mortality(herds, y) for y in range(NORMAL_FROM, NORMAL_TO + 1) if y not in DZUD}
    return sorted(sorted((y for y in m if m[y] is not None), key=m.get)[:2])


def main() -> None:
    herds = load_livestock()
    normals = normal_winters(herds)
    winters = sorted(DZUD + normals)  # the pre-registered test; every other winter is scored and shown, not pooled
    print(f"winters {WINTERS}, pooled test {winters} (normal: {normals})")
    rows, every = [], []
    for y in WINTERS:
        indicators.main(y)
        v = validate.main(y, normals)
        export.main(y)
        print(f"  {v['winter']}: unit {v['validation_unit']}, n {v['n']}, rho soum {v['spearman_soum']}, "
              f"excess {v['excess_spearman_soum']}, rho aimag {v['spearman_aimag']} (n={v['n_aimag']}), "
              f"mortality {v['mortality_pct']}%")
        r = pooled_rows(y, indicators.read_risk(y), herds, normals)
        every += r
        rows += r if y in winters else []
    res = {**rounded(pooled(rows)), "every_winter": rounded(pooled(every))}
    POOLED.write_text(json.dumps(res, indent=2))
    (export.SITE / "pooled.json").write_text(json.dumps(res, indent=2))
    export.write_index(WINTERS)
    aimags.write_shapes()
    print(f"pooled: {res}")
    snow = compare.main(winters)
    print(f"snow comparison -> {compare.PAGE}: pooled {snow['pooled']}")
    stages = asof.main(winters, normals)
    print("as-of pooled rho by stage: " + ", ".join(f"{k} {v['pooled']['spearman']}" for k, v in stages.items()))


def check() -> None:
    full = {"camel": 0, "horse": 0, "cattle": 0, "goat": 0}
    herds = {}
    for y in range(2011, 2024):
        lost = {2013: 1.0, 2021: 2.0}.get(y, 10.0)
        herds[("A", y, "stock")] = {**full, "sheep": 100.0}
        herds[("A", y + 1, "loss")] = {**full, "sheep": lost}
    assert normal_winters(herds) == [2013, 2021]
    assert WINTERS == [2009] + list(range(2011, 2025)), WINTERS  # every winter NSO has soum losses for, plus 2009/10
    rows = [("A", 2013, 0.1, 0.01, 0.0), ("B", 2013, 0.2, 0.02, 0.01), ("A", 2023, 0.9, 0.3, 0.29), ("B", 2023, 0.5, 0.1, 0.09)]
    res = pooled(rows)
    assert res["spearman"] == 1.0 and res["n"] == 4 and res["winters"] == [2013, 2023], res
    partial = {("A", 2013, "stock"): {**full, "sheep": 100.0}, ("A", 2014, "loss"): {**full, "sheep": 1.0},
               ("B", 2013, "stock"): {"sheep": 100.0}, ("B", 2014, "loss"): {**full, "sheep": 50.0}}
    assert national_mortality(partial, 2013) == 0.01, national_mortality(partial, 2013)
    print("hindcast check: ok")


if __name__ == "__main__":
    check() if "--check" in sys.argv else main()
