"""The fixed score as a chance: P(adult losses >= 5 % of the herd) = 1 / (1 + exp(-(a * risk + b))), fitted per outlook
stage on the soum-winters with losses (2011/12-2024/25), each stage on the risk that stage would have shown. The
fit is checked leave-one-winter-out; a stage whose held-out Brier score is no better than the base rate shows no
chance at all, rather than a number with nothing behind it.

The aimag level is fitted the same way on its own: the soum fit does not carry over to a herd-weighted aimag mean,
which varies less. Its rows are the aimag-winters 2000/01-2024/25, NSO's aimag losses against the aimag's
herd-weighted risk (validate.aimag_pairs, the pairs of the aimag rho)."""
import json
import sys
from pathlib import Path

import numpy as np

from pipeline import indicators
from pipeline.asof import STAGES, stage_date
from pipeline.boundaries import load_soums
from pipeline.export import SITE
from pipeline.model import HIGH_LOSS, TRAIN, fit, lowo
from pipeline.nso import load_livestock, load_livestock_aimag
from pipeline.validate import aimag_pairs, mortality

AIMAG_YEARS = range(2000, 2025)  # hindcast.WINTERS, not imported: hindcast imports this module

BINS = 5
OUT = Path("data/derived/calibration.json")


def brier(p, y) -> float:
    return float(np.mean((np.asarray(p, float) - np.asarray(y, float)) ** 2))


def reliability(p, y, bins: int = BINS) -> list[list]:
    """Per equal-count bin of predicted chance: [mean predicted, observed rate, n]."""
    p, y = np.asarray(p, float), np.asarray(y, float)
    return [[round(float(p[i].mean()), 4), round(float(y[i].mean()), 4), len(i)]
            for i in np.array_split(np.argsort(p, kind="stable"), bins) if len(i)]


def climatology(rows: list[dict]) -> list[float]:
    """Each row's base rate from the other winters only: the forecast a chance must beat."""
    rate = {w: np.mean([r["y"] for r in rows if r["winter"] != w]) for w in {r["winter"] for r in rows}}
    return [float(rate[r["winter"]]) for r in rows]


def stage_rows(stage: str, herds: dict, years=TRAIN, compute=None) -> list[dict]:
    compute = compute or (lambda y: indicators.compute(y, stage_date(y, stage)))
    rows = []
    for y in years:
        for pc, r in compute(y).items():
            m = mortality(herds, pc, y)
            if r["risk"] is not None and m is not None:
                rows.append({"winter": y, "x": [r["risk"]], "y": float(m >= HIGH_LOSS)})
    return rows


def aimag_stage_rows(stage: str, herds: dict, aherds: dict, aimag_of: dict[str, str], years=AIMAG_YEARS,
                     compute=None) -> list[dict]:
    """The aimag-winters at a stage: the herd-weighted risk of the aimag's soums, labelled by NSO's aimag losses."""
    compute = compute or (lambda y: indicators.compute(y, stage_date(y, stage)))
    rows = []
    for y in years:
        scores = {pc: (r["risk"], aimag_of[pc]) for pc, r in compute(y).items() if r["risk"] is not None and pc in aimag_of}
        rows += [{"winter": y, "x": [risk], "y": float(m >= HIGH_LOSS)} for _, risk, m in aimag_pairs(y, scores, herds, aherds)]
    return rows


def calibrate(rows: list[dict]) -> dict:
    """The stage's a and b fitted on every winter, judged on chances each made without its own winter."""
    held = lowo(rows)
    order = [r for w in sorted(held) for r in rows if r["winter"] == w]
    p, y = [q for w in sorted(held) for q in held[w]], [r["y"] for r in order]
    b_model, b_clim = brier(p, y), brier(climatology(order), y)
    w, b = fit([r["x"] for r in rows], [r["y"] for r in rows])
    return {"a": round(float(w[0]), 4), "b": round(b, 4), "n": len(rows), "base_rate": round(float(np.mean(y)), 4),
            "brier": round(b_model, 4), "brier_clim": round(b_clim, 4), "bss": round(1 - b_model / b_clim, 3),
            "reliability": reliability(p, y)}


def main() -> dict:
    herds, aherds = load_livestock(), load_livestock_aimag()
    aimag_of = {s["pcode"]: s["aimag_pcode"] for s in load_soums()}
    out, out_aimag = {}, {}
    for stage in STAGES:
        cache: dict[int, dict] = {}  # one compute per winter serves both levels
        compute = lambda y: cache.setdefault(y, indicators.compute(y, stage_date(y, stage)))  # noqa: E731
        out[stage] = calibrate(stage_rows(stage, herds, compute=compute))
        out_aimag[stage] = calibrate(aimag_stage_rows(stage, herds, aherds, aimag_of, compute=compute))
    text = json.dumps({"target": f"adult losses >= {HIGH_LOSS:.0%} of the herd", "stages": out,
                       "aimag_stages": out_aimag}, allow_nan=False)
    OUT.write_text(text)
    (SITE / "calibration.json").write_text(text)
    for name, res in (("soum", out), ("aimag", out_aimag)):
        print(f"calibration, {name}: " + "; ".join(f"{s} a {c['a']} b {c['b']} n {c['n']} bss {c['bss']}" for s, c in res.items()))
    return out


def check() -> None:
    assert brier([0.0, 1.0], [0, 1]) == 0.0 and brier([0.5, 0.5], [0, 1]) == 0.25
    rel = reliability([0.1, 0.1, 0.2, 0.2, 0.9, 0.9], [0, 0, 0, 1, 1, 1], bins=3)
    assert rel == [[0.1, 0.0, 2], [0.2, 0.5, 2], [0.9, 1.0, 2]], rel

    rows = [{"winter": w, "x": [0.0], "y": v} for w, v in ((1, 1.0), (1, 0.0), (2, 0.0), (2, 0.0), (3, 1.0), (3, 1.0))]
    assert climatology(rows) == [0.5, 0.5, 0.75, 0.75, 0.25, 0.25], "a winter's own losses never set its base rate"

    rng = np.random.default_rng(1)
    rows = []
    for w in range(8):
        risk = rng.normal(size=300)
        p_true = 1 / (1 + np.exp(-(1.5 * risk - 2.0)))
        rows += [{"winter": w, "x": [float(r)], "y": float(u < p)} for r, p, u in zip(risk, p_true, rng.random(300))]
    c = calibrate(rows)
    assert abs(c["a"] - 1.5) < 0.3 and abs(c["b"] + 2.0) < 0.3, c  # the chance it learns is the one that made the data
    assert c["bss"] > 0.1 and c["brier"] < c["brier_clim"], c
    noise = [{**r, "x": [float(rng.normal())]} for r in rows]
    assert calibrate(noise)["bss"] <= 0, "a risk unrelated to losses must not beat the base rate"

    herds = {("A", 2011, "stock"): {"camel": 0, "horse": 0, "cattle": 0, "goat": 0, "sheep": 100.0},
             ("A", 2012, "loss"): {"camel": 0, "horse": 0, "cattle": 0, "goat": 0, "sheep": 6.0}}
    got = stage_rows("oct", herds, [2011], compute=lambda y: {"A": {"risk": 0.4}, "B": {"risk": 1.0}, "C": {"risk": None}})
    assert got == [{"winter": 2011, "x": [0.4], "y": 1.0}], got  # B has no losses, C no risk

    aherds = {("X", 2011, "stock"): {"camel": 0, "horse": 0, "cattle": 0, "goat": 0, "sheep": 1000.0},
              ("X", 2012, "loss"): {"camel": 0, "horse": 0, "cattle": 0, "goat": 0, "sheep": 20.0}}
    herds[("B", 2011, "stock")] = {"camel": 0, "horse": 0, "cattle": 0, "goat": 0, "sheep": 300.0}
    got = aimag_stage_rows("oct", herds, aherds, {"A": "X", "B": "X", "C": "X"}, [2011],
                           compute=lambda y: {"A": {"risk": 0.4}, "B": {"risk": 1.0}, "C": {"risk": None}})
    assert len(got) == 1 and abs(got[0]["x"][0] - 0.85) < 1e-12 and got[0]["y"] == 0.0, got  # (100*.4+300*1)/400; 2 % lost
    print("calibrate check: ok")


if __name__ == "__main__":
    check() if "--check" in sys.argv else main()
