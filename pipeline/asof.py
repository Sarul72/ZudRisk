"""As-of hindcasts: the past winters re-scored at each outlook stage with only the data that stage holds,
so an outlook can show how well its own stage did before (spec 4.5, "Hindcast vs outlook")."""
import calendar
import json
import sys
from datetime import date
from pathlib import Path

from pipeline import indicators
from pipeline.boundaries import load_soums
from pipeline.export import SITE, label
from pipeline.nso import load_livestock, load_livestock_aimag
from pipeline.validate import evaluate, pooled, pooled_rows, rounded

# stage -> (year offset from the winter's first year, month, day; -1 = the month's last day), named by its last data month
STAGES = {"oct": (0, 10, 31), "nov": (0, 11, 30), "dec": (0, 12, 31), "jan": (1, 1, 31), "feb": (1, 2, -1), "mar": (1, 3, 31)}
OUT = Path("data/derived/asof_validation.json")


def stage_date(year: int, stage: str) -> date:
    dy, m, d = STAGES[stage]
    y = year + dy
    return date(y, m, calendar.monthrange(y, m)[1] if d == -1 else d)


def main(winters: list[int], normals: list[int]) -> dict:
    herds, aherds = load_livestock(), load_livestock_aimag()
    aimag = {s["pcode"]: s["aimag_pcode"] for s in load_soums()}
    out = {}
    for stage in STAGES:
        per, rows = {}, []
        for y in winters:
            risk = {pc: r["risk"] for pc, r in indicators.compute(y, stage_date(y, stage)).items() if r["risk"] is not None}
            v = evaluate(y, {pc: (r, aimag[pc]) for pc, r in risk.items()}, herds, aherds, normals)
            per[label(y)] = {k: v[k] for k in ("validation_unit", "n", "spearman_soum", "excess_spearman_soum",
                                               "n_aimag", "spearman_aimag")}
            rows += pooled_rows(y, risk, herds, normals)
        out[stage] = {"winters": per, "pooled": rounded(pooled(rows))}
    text = json.dumps(out, indent=2, allow_nan=False)
    OUT.write_text(text)
    (SITE / "asof_validation.json").write_text(text)
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
