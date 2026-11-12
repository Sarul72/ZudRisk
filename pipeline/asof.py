"""As-of hindcasts: the past winters re-scored at each outlook stage with only the data that stage holds,
so an outlook can show how well its own stage did before (spec 4.5, "Hindcast vs outlook")."""
import calendar
import json
import sys
from datetime import date
from pathlib import Path

from pipeline import indicators, seasonal
from pipeline.boundaries import load_soums
from pipeline.export import SITE, label
from pipeline.nso import load_livestock, load_livestock_aimag
from pipeline.validate import aimag_pairs, evaluate, pooled, pooled_aimag, pooled_rows, rounded

# stage -> (year offset from the winter's first year, month, day; -1 = the month's last day), named by its last data month
STAGES = {"oct": (0, 10, 31), "nov": (0, 11, 30), "dec": (0, 12, 31), "jan": (1, 1, 31), "feb": (1, 2, -1), "mar": (1, 3, 31)}
SEAS5 = "oct_seas5"  # the oct stage plus the 1 October seasonal forecast
OUT = Path("data/derived/asof_validation.json")


def stage_date(year: int, stage: str) -> date:
    dy, m, d = STAGES[stage]
    y = year + dy
    return date(y, m, calendar.monthrange(y, m)[1] if d == -1 else d)


def rows_at(year: int, stage: str, fc: dict) -> dict[str, dict]:
    """A winter's rows at a stage; SEAS5 is the oct stage with that winter's 1 October forecast filled in."""
    if stage == SEAS5:
        return seasonal.with_forecast(indicators.compute(year, stage_date(year, "oct")), fc.get(year, {}))
    return indicators.compute(year, stage_date(year, stage))


def main(winters: list[int], normals: list[int], aimag_winters: list[int] = ()) -> dict:
    """Each stage over the pre-registered winters at soum level; the oct stage with and without the forecast also
    over every aimag-winter, the only test that reaches the 2000/01 and 2009/10 dzuds."""
    herds, aherds = load_livestock(), load_livestock_aimag()
    aimag = {s["pcode"]: s["aimag_pcode"] for s in load_soums()}
    fc = seasonal.load() if seasonal.OUT.exists() else {}
    out = {}
    for stage in list(STAGES) + ([SEAS5] if fc else []):
        per, rows, by_aimag = {}, [], []
        for y in sorted(set(winters) | (set(aimag_winters) if stage in ("oct", SEAS5) else set())):
            risk = {pc: r["risk"] for pc, r in rows_at(y, stage, fc).items() if r["risk"] is not None}
            scores = {pc: (r, aimag[pc]) for pc, r in risk.items()}
            by_aimag += [(y, r, m) for _, r, m in aimag_pairs(y, scores, herds, aherds)]
            if y not in winters:
                continue
            v = evaluate(y, scores, herds, aherds, normals)
            per[label(y)] = {k: v[k] for k in ("validation_unit", "n", "spearman_soum", "excess_spearman_soum",
                                               "n_aimag", "spearman_aimag")}
            rows += pooled_rows(y, risk, herds, normals)
        out[stage] = {"winters": per, "pooled": rounded(pooled(rows))}
        if stage in ("oct", SEAS5) and aimag_winters:
            out[stage]["pooled_aimag"] = rounded(pooled_aimag(by_aimag))
    text = json.dumps(out, indent=2, allow_nan=False)
    OUT.write_text(text, encoding="utf-8")
    (SITE / "asof_validation.json").write_text(text, encoding="utf-8")
    return out


def check() -> None:
    from pipeline import indicators
    assert stage_date(2023, "feb") == date(2024, 2, 29)
    assert stage_date(2022, "feb") == date(2023, 2, 28)
    assert stage_date(2023, "oct") == date(2023, 10, 31)
    assert list(STAGES) == ["oct", "nov", "dec", "jan", "feb", "mar"]
    pre = indicators.compute(2023, stage_date(2023, "oct"))
    assert all(r["z_cold"] is None and r["z_snow"] is None for r in pre.values())
    herd = [r for r in pre.values() if not r["no_herd"]]
    assert {r["n_indicators"] for r in herd} == {2}, {r["n_indicators"] for r in herd}
    assert all(r["risk"] is None for r in pre.values() if r["no_herd"]), "no herd, no risk"
    full = indicators.compute(2023, stage_date(2023, "mar"))
    hindcast = indicators.read_risk(2023)
    assert {pc: round(r["risk"], 4) for pc, r in full.items() if r["risk"] is not None} == hindcast, \
        "the mar stage must be the hindcast"
    print("asof check: ok")


if __name__ == "__main__":
    if "--check" in sys.argv:
        check()
    else:
        from pipeline.hindcast import DZUD, normal_winters  # hindcast imports asof; the reverse only here
        normals = normal_winters(load_livestock())
        main(sorted(DZUD + normals), normals)
