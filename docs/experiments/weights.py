"""Held-out tests of the indicator weights, as pre-registered in docs/experiments/2026-11-14-weights.md.
uv run python docs/experiments/weights.py   (from the repository root; reads data/derived, writes nothing)"""
import csv
import itertools
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from pipeline import hindcast, validate  # noqa: E402
from pipeline.nso import load_livestock  # noqa: E402

KEYS = ["snow", "cold", "pressure", "summer"]
W0 = np.array([0.41, 0.35, 0.29, 0.24])
W1 = np.full(4, 0.25)
YEARS = list(range(2011, 2025))
GRID = np.array([w for w in itertools.product(range(21), repeat=4) if sum(w) == 20], dtype=float) / 20  # 1,771 sets


def load():
    herds = load_livestock()
    yr, Z, M, mort = [], [], [], []
    for y in YEARS:
        with Path(f"data/derived/indicators_{y}.csv").open(encoding="utf-8") as f:
            for r in csv.DictReader(f):
                m = validate.mortality(herds, r["pcode"], y)
                if m is None or not r["risk"]:
                    continue
                z = [r[f"z_{k}"] for k in KEYS]
                yr.append(y)
                Z.append([float(v) if v else 0.0 for v in z])
                M.append([1.0 if v else 0.0 for v in z])
                mort.append(m)
    return np.array(yr), np.array(Z), np.array(M), np.array(mort), herds


def scores(Z, M, W):
    """Scores for weight sets W (G x 4): the weighted mean of the indicators present, as pipeline.score.risk."""
    W = np.atleast_2d(W)
    den = M @ W.T
    return np.where(den > 0, (Z @ W.T) / np.where(den > 0, den, 1), 0.0)


def rank_cols(S):
    r = np.empty_like(S)
    idx = np.argsort(S, axis=0, kind="stable")
    np.put_along_axis(r, idx, np.arange(1, S.shape[0] + 1)[:, None].repeat(S.shape[1], 1).astype(float), axis=0)
    return r


def rho_cols(S, mrank):
    r = rank_cols(S)
    r = r - r.mean(0)
    m = mrank - mrank.mean()
    return (r * m[:, None]).sum(0) / np.sqrt((r ** 2).sum(0) * (m ** 2).sum())


def rho(s, m):
    return validate.spearman(list(s), list(m))


def fit(Z, M, mort):
    mrank = validate._ranks(mort)
    return GRID[int(np.argmax(rho_cols(scores(Z, M, GRID), mrank)))]


def main():
    yr, Z, M, mort, herds = load()
    prereg = np.isin(yr, sorted(set(hindcast.DZUD + hindcast.normal_winters(herds))))
    base = scores(Z, M, W0)[:, 0]
    print(f"n {len(yr)}; W0 every {rho(base, mort):.3f}, pre-registered {rho(base[prereg], mort[prereg]):.3f}")

    # T1: leave one winter out
    held = {k: np.zeros(len(yr)) for k in ("W2", "W3")}
    fitted = []
    for y in YEARS:
        tr, te = yr != y, yr == y
        w2 = fit(Z[tr], M[tr], mort[tr])
        fitted.append(w2)
        held["W2"][te] = scores(Z[te], M[te], w2)[:, 0]
        held["W3"][te] = scores(Z[te], M[te], 0.5 * W0 + 0.5 * w2)[:, 0]
    t1 = {"W0": base, "W1": scores(Z, M, W1)[:, 0], **held}
    print("T1 leave one winter out (held-out scores pooled):")
    for k, s in t1.items():
        print(f"  {k}: every {rho(s, mort):.3f}   pre-registered {rho(s[prereg], mort[prereg]):.3f}")
    f = np.array(fitted)
    print("  W2 weights fitted per fold (snow, cold, pressure, summer): mean", np.round(f.mean(0), 2),
          "min", np.round(f.min(0), 2), "max", np.round(f.max(0), 2))

    # T2: time split
    tr, te = yr <= 2017, yr >= 2018
    w2 = fit(Z[tr], M[tr], mort[tr])
    t2 = {"W0": W0, "W1": W1, "W2": w2, "W3": 0.5 * W0 + 0.5 * w2}
    print(f"T2 fit 2011/12-2017/18 (n {tr.sum()}), test 2018/19-2024/25 (n {te.sum()}); W2 = {np.round(w2, 2)}")
    res2 = {}
    for k, w in t2.items():
        res2[k] = rho(scores(Z[te], M[te], w)[:, 0], mort[te])
        print(f"  {k}: test {res2[k]:.3f}")

    t1r = {k: rho(s, mort) for k, s in t1.items()}
    for k in ("W1", "W2", "W3"):
        a, b = t1r[k] - t1r["W0"], res2[k] - res2["W0"]
        ok = a >= 0.01 and b >= 0.01
        print(f"{k}: T1 {a:+.3f}, T2 {b:+.3f} -> {'REPLACES literature' if ok else 'literature stays'}")


if __name__ == "__main__":
    main()
