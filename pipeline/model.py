"""A small learned model beside the fixed score: ridge logistic regression on soum-winters, asked which soums lose
heavily, validated leave-one-winter-out against the fixed score, then replayed over the last 20 winters' weather on
today's herds and pasture. The replay is structural vulnerability for research, not a forecast."""
import json
import math
import sys
from pathlib import Path

import numpy as np

from pipeline import indicators
from pipeline.export import SITE, label
from pipeline.gldas import load_series
from pipeline.nso import load_livestock, sheep_units
from pipeline.score import WEIGHTS
from pipeline.trends import greenness_trend, latest_summer
from pipeline.validate import _ranks, mortality, spearman

TRAIN = range(2011, 2025)  # every winter NSO has soum losses for (losses 2012-2025)
REPLAY = range(2006, 2026)  # the last 20 winters whose weather is all in, 2006/07 to 2025/26
NOW = 2025  # the newest census
HIGH_LOSS = 0.05  # the target, fixed before any fit: adult losses of 5 % of the herd or more
LAM = 1.0  # ridge penalty on standardised features; not tuned, so the held-out skill is not tuned either
CLIMATE = ["z_cold", "z_snow", "z_summer", "z_density"]  # what a replayed winter brings
FEATURES = CLIMATE + ["z_pressure", "greenness_trend", "herd_growth_5y", "past_mortality"]
OUT = Path("data/derived/model.json")


def auc(score: list[float], label_: list[float]) -> float | None:
    """Mann-Whitney: the chance a high-loss soum-winter outscores a calm one, ties half."""
    n1 = sum(1 for v in label_ if v)
    n0 = len(label_) - n1
    if not n1 or not n0:
        return None
    s1 = sum(r for r, v in zip(_ranks(score), label_) if v)
    return float((s1 - n1 * (n1 + 1) / 2) / (n1 * n0))


def fit(x, y, lam: float = LAM, iters: int = 50) -> tuple[np.ndarray, float]:
    """Ridge logistic regression by Newton steps; the intercept is not penalised."""
    a = np.column_stack([np.ones(len(x)), np.asarray(x, float)])
    y = np.asarray(y, float)
    pen = np.full(a.shape[1], lam)
    pen[0] = 0.0
    beta = np.zeros(a.shape[1])
    for _ in range(iters):
        p = 1 / (1 + np.exp(-a @ beta))
        step = np.linalg.solve((a * (p * (1 - p))[:, None]).T @ a + np.diag(pen), a.T @ (p - y) + pen * beta)
        beta -= step
        if np.abs(step).max() < 1e-10:
            break
    return beta[1:], float(beta[0])


def predict(x, w: np.ndarray, b: float) -> np.ndarray:
    return 1 / (1 + np.exp(-(np.asarray(x, float) @ w + b)))


def _scaler(train_x):
    """Standardise on the training rows only; a missing value becomes the training mean (0)."""
    x = np.asarray(train_x, float)
    mu, sd = np.nanmean(x, 0), np.nanstd(x, 0)
    sd[sd == 0] = 1.0
    return lambda v: np.nan_to_num((np.asarray(v, float) - mu) / sd)


def lowo(rows: list[dict], lam: float = LAM) -> dict:
    """Each winter predicted by a model fitted on every other winter: winter -> probabilities in row order."""
    out = {}
    for held in sorted({r["winter"] for r in rows}):
        train = [r for r in rows if r["winter"] != held]
        s = _scaler([r["x"] for r in train])
        w, b = fit(s([r["x"] for r in train]), [r["y"] for r in train], lam)
        out[held] = [float(p) for p in predict(s([r["x"] for r in rows if r["winter"] == held]), w, b)]
    return out


def growth(herds: dict, pcode: str, year: int) -> float | None:
    """log of the census herd over the herd five censuses before."""
    now = sheep_units(herds.get((pcode, year, "stock"), {}))
    then = sheep_units(herds.get((pcode, year - 5, "stock"), {}))
    return math.log(now / then) if now and then else None


def past_mortality(herds: dict, pcode: str, year: int) -> float | None:
    """Mean mortality over the soum's winters with losses before `year`; never `year` itself."""
    ms = [m for y in range(TRAIN.start, year) if (m := mortality(herds, pcode, y)) is not None]
    return sum(ms) / len(ms) if ms else None


def _x(climate_row: dict, now_row: dict, ndvi: dict, herds: dict, pcode: str, year: int, through: int) -> list[float]:
    vals = [climate_row[k] for k in CLIMATE] + [now_row["z_pressure"], greenness_trend(ndvi.get(pcode, {}), through),
                                              growth(herds, pcode, year), past_mortality(herds, pcode, year)]
    return [math.nan if v is None else v for v in vals]


def training_rows(herds: dict, ndvi: dict) -> list[dict]:
    rows = []
    for y in TRAIN:
        for pc, r in indicators.compute(y, indicators.winter_end(y)).items():
            m = mortality(herds, pc, y)
            if r["risk"] is None or m is None:
                continue
            rows.append({"winter": y, "pcode": pc, "x": _x(r, r, ndvi, herds, pc, y, y), "y": float(m >= HIGH_LOSS),
                         "m": m, "risk": r["risk"]})
    return rows


def skill(prob: list[float], rows: list[dict]) -> dict:
    m, y, risk = [r["m"] for r in rows], [r["y"] for r in rows], [r["risk"] for r in rows]
    rd = lambda v: None if v is None else round(v, 3)  # noqa: E731
    return {"n": len(rows), "high_loss": int(sum(y)), "rho_model": rd(spearman(prob, m)),
            "rho_fixed": rd(spearman(risk, m)), "auc_model": rd(auc(prob, y)), "auc_fixed": rd(auc(risk, y))}


def main() -> dict:
    herds, ndvi = load_livestock(), load_series(indicators.NDVI_CSV)
    rows = training_rows(herds, ndvi)
    held = lowo(rows)
    per = {label(y): skill(held[y], [r for r in rows if r["winter"] == y]) for y in held}
    order = [r for y in held for r in rows if r["winter"] == y]
    pooled_ = skill([p for y in held for p in held[y]], order)
    s = _scaler([r["x"] for r in rows])
    w, b = fit(s([r["x"] for r in rows]), [r["y"] for r in rows])
    now = indicators.compute(NOW, indicators.winter_end(NOW))
    through = latest_summer(ndvi)
    weather = {c: (now if c == NOW else indicators.compute(c, indicators.winter_end(c))) for c in REPLAY}
    vuln = {}
    for pc, r in now.items():
        if r["su_per_km2"] is None:
            continue  # no herd, no risk
        xs = [_x(weather[c][pc], r, ndvi, herds, pc, NOW, through) for c in REPLAY]
        vuln[pc] = round(float(predict(s(xs), w, b).mean()), 4)
    out = {"target": f"adult losses >= {HIGH_LOSS:.0%} of the herd in sheep units", "lam": LAM, "features": FEATURES,
           "weights": {f: round(float(v), 3) for f, v in zip(FEATURES, w)}, "intercept": round(b, 3),
           "fixed_weights": WEIGHTS, "train": [label(y) for y in TRAIN], "lowo": per, "pooled": pooled_,
           "replay": [label(REPLAY.start), label(REPLAY.stop - 1)], "census": NOW, "greenness_through": through,
           "vulnerability": vuln}
    text = json.dumps(out, allow_nan=False)
    OUT.write_text(text)
    (SITE / "model.json").write_text(text)
    v = sorted(vuln.values())
    print(f"model: {len(rows)} soum-winters, {int(sum(r['y'] for r in rows))} high-loss; held-out pooled {pooled_}; "
          f"weights {out['weights']}; vulnerability {len(v)} soums, median {v[len(v) // 2]}, max {v[-1]}")
    return out


def check() -> None:
    assert auc([0.1, 0.4, 0.35, 0.8], [0, 0, 1, 1]) == 0.75
    assert auc([0.5, 0.5], [0, 1]) == 0.5, "a tie is half a win"
    assert auc([0.1, 0.2], [0, 0]) is None, "no positive, no AUC"

    rng = np.random.default_rng(0)
    x = rng.normal(size=(400, 2))
    y = (x[:, 0] + 0.3 * rng.normal(size=400) > 0.5).astype(float)
    w, b = fit(x, y, lam=1.0)
    assert w[0] > 2 and abs(w[1]) < 0.5, (w, b)
    p = predict(x, w, b)
    assert ((p > 0) & (p < 1)).all() and auc(list(p), list(y)) > 0.9
    w_ridge, _ = fit(x, y, lam=1e4)
    assert abs(w_ridge[0]) < abs(w[0]) / 5, "the penalty shrinks"

    full = {"camel": 0, "horse": 0, "cattle": 0, "goat": 0}
    herds = {("A", y_, "stock"): {**full, "sheep": 100.0 * (1.1 ** (y_ - 2010))} for y_ in range(2010, 2026)}
    herds |= {("A", y_ + 1, "loss"): {**full, "sheep": {2011: 10.0, 2012: 2.0}.get(y_, 50.0)} for y_ in range(2010, 2025)}
    assert abs(growth(herds, "A", 2020) - 5 * math.log(1.1)) < 1e-12
    assert growth(herds, "A", 2012) is None, "no census five years back"
    assert past_mortality(herds, "A", 2011) is None, "nothing before the first winter with soum losses"
    before = past_mortality(herds, "A", 2013)
    assert abs(before - (10 / 110 + 2 / 121) / 2) < 1e-12, before
    herds[("A", 2014, "loss")] = {**full, "sheep": 999.0}
    assert past_mortality(herds, "A", 2013) == before, "winter Y's own loss never enters its feature"

    rows = [{"winter": wi, "x": [float(v)], "y": float(v > 0)} for wi in (1, 2, 3) for v in (-2, -1, 1, 2)]
    held = lowo(rows)
    flipped = [{**r, "y": 1 - r["y"]} if r["winter"] == 2 else r for r in rows]
    assert lowo(flipped)[2] == held[2], "a held-out winter's labels never reach its own prediction"
    print("model check: ok")


if __name__ == "__main__":
    check() if "--check" in sys.argv else main()
