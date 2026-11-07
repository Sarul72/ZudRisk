"""The coming winter's outlook at its latest stage: refuses a stage whose data has not landed, and stays out of the
hindcast index (winters.json) so nothing validates it as an observed winter."""
import json
import sys
from collections import Counter
from datetime import date

from pipeline import indicators
from pipeline.asof import STAGES, stage_date
from pipeline.boundaries import load_soums
from pipeline.export import SITE, feature, label, props_for

STAGE_OF_MONTH = {m: stage for stage, (_, m, _) in STAGES.items()}


def parse_through(through: str) -> tuple[int, str]:
    """'2026-10' -> (2026, 'oct'): the winter's first year and the stage named by its last data month."""
    y, m = map(int, through.split("-"))
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


def main(through: str) -> None:
    year, stage = parse_through(through)
    missing = missing_months(year, stage, available())
    if missing:
        sys.exit(f"{label(year)} stage {stage} cannot run yet; not published: {', '.join(missing)}")
    as_of = stage_date(year, stage)
    rows = indicators.compute(year, as_of)
    extra = {"stage": stage, "data_through": through}
    feats = [feature(s["geom"], {**props_for(s, rows.get(s["pcode"], {})), **extra}) for s in load_soums()]
    (SITE / f"outlook_{label(year)}.geojson").write_text(
        json.dumps({"type": "FeatureCollection", "features": feats}, ensure_ascii=False, separators=(",", ":")))
    (SITE / "outlook.json").write_text(json.dumps({"winter": label(year), "stage": stage, "data_through": through,
                                                   "as_of": as_of.isoformat(), "made": date.today().isoformat()}))
    hist = Counter(r["risk_class"] for r in rows.values())
    n = Counter(r["n_indicators"] for r in rows.values())
    print(f"outlook {label(year)} stage {stage} (data to {through}): indicators {dict(n)}, classes {dict(sorted(hist.items(), key=str))}")


def check() -> None:
    from pipeline import compare
    from pipeline.export import SITE
    assert parse_through("2026-10") == (2026, "oct") and parse_through("2027-02") == (2026, "feb")
    have = {"era5": {"202611"}, "ndvi": {"202607", "202608"}, "census": {2025}}
    assert missing_months(2026, "oct", have) == []
    assert missing_months(2026, "dec", have) == ["ERA5-Land 202612"]
    assert missing_months(2026, "oct", {**have, "ndvi": {"202607"}}) == ["MODIS NDVI 202608"]
    assert missing_months(2026, "feb", have) == ["ERA5-Land 202612", "ERA5-Land 202701", "ERA5-Land 202702",
                                                 "NSO census 2026"]
    index = (SITE / "winters.json").read_bytes()
    try:
        main("2030-11")
        raise AssertionError("a stage with no data must refuse")
    except SystemExit as e:
        assert "ERA5-Land 203011" in str(e), e
    assert not (SITE / "outlook_2030-31.geojson").exists()
    main("2026-10")
    assert (SITE / "winters.json").read_bytes() == index, "the outlook entered the hindcast index"
    compare.compare([2023])
    print("outlook check: ok")


if __name__ == "__main__":
    if "--check" in sys.argv:
        check()
    else:
        main(sys.argv[sys.argv.index("--through") + 1])
