"""Turn indicator values into a dzud risk score and one of five classes (spec section 4.4)."""
import sys

# Literature correlations with livestock mortality, fixed before validation
# (Nandintsetseg et al. 2018, Sci. Rep. 8:14769, Table 1; summer from its June-August precipitation term).
WEIGHTS = {"snow": 0.41, "cold": 0.35, "pressure": 0.29, "summer": 0.24}
Z_CLIP = 3.0
MIN_BASELINE = 10
# Lower bounds of classes 1..4 on the weighted mean z: very low < -1 <= low < -0.5 <= medium < 0.5 <= high < 1 <= very high
CUTS = (-1.0, -0.5, 0.5, 1.0)


def zscore(x: float, baseline: list[float]) -> float | None:
    """Population z of x against the baseline, clipped; None when the baseline cannot define a spread."""
    if len(baseline) < MIN_BASELINE:
        return None
    mean = sum(baseline) / len(baseline)
    std = (sum((b - mean) ** 2 for b in baseline) / len(baseline)) ** 0.5
    if std == 0:
        return None
    return max(-Z_CLIP, min(Z_CLIP, (x - mean) / std))


def risk(z: dict[str, float | None]) -> float | None:
    """Weighted mean of the indicators present; an absent indicator drops out of the denominator too."""
    used = {k: v for k, v in z.items() if v is not None}
    if not used:
        return None
    return sum(WEIGHTS[k] * v for k, v in used.items()) / sum(WEIGHTS[k] for k in used)


def risk_class(r: float) -> int:
    return sum(r >= c for c in CUTS)


def check() -> None:
    assert zscore(12, [10] * 5 + [12] * 5) == 1.0
    assert zscore(20, [10] * 5 + [12] * 5) == 3.0
    assert zscore(-20, [10] * 5 + [12] * 5) == -3.0
    assert zscore(1, [1] * 12) is None
    assert zscore(1, [1, 2, 3]) is None
    assert abs(risk({"cold": 1.0, "pressure": 0.0, "snow": None, "summer": None}) - 0.35 / 0.64) < 1e-12
    assert risk({"cold": None, "pressure": None}) is None
    assert [risk_class(r) for r in (-1.2, -0.7, 0.0, 0.7, 1.2)] == [0, 1, 2, 3, 4]
    assert risk_class(0.5) == 3 and risk_class(1.0) == 4 and risk_class(-1.0) == 1
    print("score check: ok")


if __name__ == "__main__":
    check()
