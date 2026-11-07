"""The coming winter's outlook at its latest stage: refuses a stage whose data has not landed, and stays out of the
hindcast index (winters.json) so nothing validates it as an observed winter."""
import json
import sys
from collections import Counter
from datetime import date

from pipeline import aimags, indicators
from pipeline.asof import STAGES, stage_date
from pipeline.boundaries import load_soums
from pipeline.export import SITE, feature, label, props_for
from pipeline.nso import load_livestock

STAGE_OF_MONTH = {m: stage for stage, (_, m, _) in STAGES.items()}


def parse_through(through: str) -> tuple[int, str]:
    """'2026-10' -> (2026, 'oct'): the winter's first year and the stage named by its last data month."""
    try:
        y, m = map(int, through.split("-"))
    except ValueError:
        raise ValueError(f"{through}: expected YYYY-MM") from None
    if m not in STAGE_OF_MONTH:
        raise ValueError(f"{through}: an outlook stage ends in Oct-Mar")
    return (y if m >= 10 else y - 1), STAGE_OF_MONTH[m]


def available() -> dict[str, set]:
    soums, herds, era5, _, ndvi = indicators._inputs()
    era5_months = set.intersection(*(set(s["sde"]) & set(s["t2m"]) for s in era5.values()))
    return {"era5": era5_months, "ndvi": set().union(*map(set, ndvi.values())),
            "census": {y for (_, y, kind) in herds if kind == "stock"}}


def missing_months(year: int, stage: str, have: dict[str, set]) -> list[str]:
    """Each source month the stage needs that has not landed; empty means the stage can run."""
    as_of = stage_date(year, stage)
    out = [f"ERA5-Land {m}" for m in indicators.snow_months(year, as_of) if m not in have["era5"]]
    out += [f"MODIS NDVI {year}{m}" for m in ("07", "08") if f"{year}{m}" not in have["ndvi"]]
    census = indicators.census_year(year, as_of)
    return out + ([] if census in have["census"] else [f"NSO census {census}"])


def short_soums(rows: dict[str, dict], stage: str) -> list[str]:
    """Soums scored on fewer indicators than the stage's validation used: pre-winter has summer and pressure,
    every later stage all four."""
    need = 2 if stage == "oct" else 4
    return sorted(pc for pc, r in rows.items() if not r["no_herd"] and r["n_indicators"] < need)


def main(through: str) -> None:
    year, stage = parse_through(through)
    missing = missing_months(year, stage, available())
    if missing:
        sys.exit(f"{label(year)} stage {stage} cannot run yet; not published: {', '.join(missing)}")
    as_of = stage_date(year, stage)
    rows = indicators.compute(year, as_of)
    short = short_soums(rows, stage)
    if short:
        sys.exit(f"{label(year)} stage {stage}: {len(short)} soums lack indicators the stage's validation used: "
                 f"{', '.join(short[:10])}")
    extra = {"stage": stage, "data_through": through}
    feats = [feature(s["geom"], {**props_for(s, rows.get(s["pcode"], {})), **extra}) for s in load_soums()]
    (SITE / f"outlook_{label(year)}.geojson").write_text(
        json.dumps({"type": "FeatureCollection", "features": feats}, ensure_ascii=False, separators=(",", ":")))
    aimags.write_scores(label(year), rows, load_livestock(), indicators.census_year(year, as_of), site=SITE)
    (SITE / "outlook.json").write_text(json.dumps({"winter": label(year), "stage": stage, "data_through": through,
                                                   "as_of": as_of.isoformat(), "made": date.today().isoformat()}))
    hist = Counter(r["risk_class"] for r in rows.values())
    n = Counter(r["n_indicators"] for r in rows.values())
    print(f"outlook {label(year)} stage {stage} (data to {through}): indicators {dict(n)}, classes {dict(sorted(hist.items(), key=str))}")


def check() -> None:
    import shutil
    import tempfile
    from pathlib import Path
    from pipeline import compare
    global SITE
    assert parse_through("2026-10") == (2026, "oct") and parse_through("2027-02") == (2026, "feb")
    for bad in ("soon", "2026-05"):
        try:
            parse_through(bad)
            raise AssertionError(f"{bad} must be refused")
        except ValueError as e:
            assert bad in str(e), e
    have = {"era5": {"202611"}, "ndvi": {"202607", "202608"}, "census": {2025}}
    assert missing_months(2026, "oct", have) == []
    assert missing_months(2026, "dec", have) == ["ERA5-Land 202612"]
    assert missing_months(2026, "oct", {**have, "ndvi": {"202607"}}) == ["MODIS NDVI 202608"]
    assert missing_months(2026, "feb", have) == ["ERA5-Land 202612", "ERA5-Land 202701", "ERA5-Land 202702",
                                                 "NSO census 2026"]
    rows = {k: {"n_indicators": n, "no_herd": 0} for k, n in (("A", 2), ("B", 1), ("C", 4))}
    rows["D"] = {"n_indicators": 1, "no_herd": 1}  # a UB district with no herd is not scored, so not short
    assert short_soums(rows, "oct") == ["B"]
    assert short_soums(rows, "nov") == ["A", "B"]
    live_site = SITE
    live = live_site / "outlook.json"
    live_mtime = live.stat().st_mtime_ns if live.exists() else None
    with tempfile.TemporaryDirectory() as d:
        SITE = Path(d)  # the self-check writes a scratch site, never the published outlook
        try:
            shutil.copy(live_site / "winters.json", SITE / "winters.json")
            index = (SITE / "winters.json").read_bytes()
            try:
                main("2030-11")
                raise AssertionError("a stage with no data must refuse")
            except SystemExit as e:
                assert "ERA5-Land 203011" in str(e), e
            assert not (SITE / "outlook_2030-31.geojson").exists() and not (SITE / "outlook.json").exists()
            main("2026-10")
            assert (SITE / "aimag_2026-27.json").exists() and (SITE / "outlook.json").exists() and (SITE / "winters.json").read_bytes() == index, \
                "the outlook entered the hindcast index"
        finally:
            SITE = live_site
    compare.compare([2023])
    assert (live.stat().st_mtime_ns if live.exists() else None) == live_mtime, "the self-check overwrote the live outlook"
    print("outlook check: ok")


if __name__ == "__main__":
    if "--check" in sys.argv:
        check()
    elif "--through" not in sys.argv or sys.argv.index("--through") + 1 >= len(sys.argv):
        sys.exit("usage: python -m pipeline.outlook --through YYYY-MM   (Oct-Mar, e.g. 2026-11)")
    else:
        try:
            main(sys.argv[sys.argv.index("--through") + 1])
        except ValueError as e:
            sys.exit(f"--through {e}")
