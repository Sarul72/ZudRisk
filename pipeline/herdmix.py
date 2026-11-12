"""Herd composition as model features, tested and not used (plan.md idea 3).

Each species' share of the census herd, in sheep units, joins the learned model (pipeline.model) as four features:
camel, horse, cattle and goat, with sheep the reference since the shares sum to 1. Soum rows take the soum census
of the winter's year, aimag rows (2000/01-2010/11) the aimag census.

The rule, fixed before the run: kept only if the held-out soum rho and AUC both rise over the current model's
(0.372 and 0.745). Run 2026-11-12, every winter held out in turn:
  soum-winters (n 4688):  rho 0.372 -> 0.352, AUC 0.745 -> 0.732
  aimag-winters (n 231):  rho 0.523 -> 0.538, AUC 0.755 -> 0.766
Both soum figures fell, so the model keeps its features. Like the iron-dzud test, the aimag rows gained a little."""
import math
import sys

from pipeline import indicators
from pipeline import model as M
from pipeline.boundaries import load_soums
from pipeline.gldas import load_series
from pipeline.nso import SHEEP_UNITS, load_hay, load_livestock, load_livestock_aimag, sheep_units

SPECIES = ["camel", "horse", "cattle", "goat"]  # sheep is the reference: the five shares sum to 1


def shares(by_type: dict[str, float]) -> list[float]:
    """Each species' share of the herd in sheep units; NaN (the training mean, after scaling) with no herd."""
    su = sheep_units(by_type or {})
    if not su:
        return [math.nan] * len(SPECIES)
    return [SHEEP_UNITS[s] * by_type[s] / su for s in SPECIES]


def with_shares(row: dict, herds: dict) -> dict:
    """The row with its census shares inserted before past_mortality, which _fold_x needs last."""
    sh = shares(herds.get((row["pcode"], row["winter"], "stock"), {}))
    return {**row, "x": row["x"][:-1] + sh + row["x"][-1:]}


def held_out(rows: list[dict]) -> tuple[dict, dict]:
    held = M.lowo(rows)
    pick = lambda years: M.skill([p for y in years for p in held[y]], [r for y in years for r in rows if r["winter"] == y])  # noqa: E731
    return pick(M.TRAIN), pick(M.AIMAG_TRAIN)


def keep(base: dict, new: dict) -> bool:
    return new["rho_model"] > base["rho_model"] and new["auc_model"] > base["auc_model"]


def main() -> dict:
    herds, aherds, ndvi = load_livestock(), load_livestock_aimag(), load_series(indicators.NDVI_CSV)
    soums, hay = load_soums(), load_hay()
    soum_rows = M.training_rows(herds, ndvi, M.hay_per_su(hay, herds, soums))
    aimag_rows = M.aimag_rows(soums, herds, aherds, ndvi, hay)
    base = held_out(soum_rows + aimag_rows)
    new = held_out([with_shares(r, herds) for r in soum_rows] + [with_shares(r, aherds) for r in aimag_rows])
    verdict = "kept" if keep(base[0], new[0]) else "not used"
    for name, b, n in (("soum", base[0], new[0]), ("aimag", base[1], new[1])):
        print(f"herd mix, {name} (n {n['n']}): rho {b['rho_model']} -> {n['rho_model']}, AUC {b['auc_model']} -> {n['auc_model']}")
    print(f"herd mix: {verdict} (rule: both soum figures must rise)")
    return {"base": base, "herd_mix": new, "verdict": verdict}


def check() -> None:
    by = {"camel": 2.0, "horse": 1.0, "cattle": 1.0, "sheep": 10.0, "goat": 10.0}  # 10 + 7 + 6 + 10 + 9 = 42 SU
    got = shares(by)
    assert [round(v * 42, 9) for v in got] == [10.0, 7.0, 6.0, 9.0], got
    assert all(math.isnan(v) for v in shares({})), "no census, no shares"
    assert all(math.isnan(v) for v in shares({k: 0.0 for k in SHEEP_UNITS})), "an empty herd has no mix"
    row = {"pcode": "A", "winter": 2015, "x": [1.0, 2.0, 0.3]}
    out = with_shares(row, {("A", 2015, "stock"): by})
    assert out["x"][:2] == [1.0, 2.0] and out["x"][-1] == 0.3 and len(out["x"]) == 7, out  # past losses stay last
    assert row["x"] == [1.0, 2.0, 0.3], "the source row is not changed"
    base = {"rho_model": 0.372, "auc_model": 0.745}
    assert keep(base, {"rho_model": 0.38, "auc_model": 0.75})
    assert not keep(base, {"rho_model": 0.38, "auc_model": 0.74}), "both must rise"
    assert not keep(base, {"rho_model": 0.372, "auc_model": 0.75}), "equal is not a rise"
    print("herdmix check: ok")


if __name__ == "__main__":
    check() if "--check" in sys.argv else main()
