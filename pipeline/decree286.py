"""Resolution 286 (2015), annex 5 ("Ган, зудын байдалд үнэлгээ хийх журам"): its main dzud criteria per soum and
month, from ERA5-Land monthly means. Spec: docs/superpowers/specs/2026-11-13-resolution-286-criteria-design.md.

  white dzud (3.3.1): mean snow depth above the zone's dzud threshold, and the month at least 3.0 °C colder than its
      2001-2020 mean or more than one standard deviation colder. The 0.25 g/cm³ density criterion is not assessed:
      ERA5-Land's soum means never reach 0.20.
  white, moderate (3.3.2): depth above the zone's moderate threshold (density not assessed either).
  black dzud (3.3.3): the summer before was drought or near-drought, no snow (< 1 cm), and at least 3.0 °C colder.
  black, moderate (3.3.4): drought or near-drought summer, little snow (1 cm up to the moderate threshold), and at
      least 2.0 °C colder.
  summer (2.2), May-August as a season: drought is precipitation at most 50 % of its mean with temperature 2.0 °C or
      more above its mean (or more than 2σ); near-drought is any other summer at most 80 % of its mean that is 1.0 °C
      or more above it (or more than 1σ). The procedure's near-drought reads 51-80 % and 1.0-1.9 °C; read literally,
      a summer drier than 50 % but only 1-1.9 °C hot would be neither, so it counts as near-drought here.
Not assessed: snow density, the auxiliary criteria (daily minimum temperature, windy days), the dekad step, and
hoof, storm and iron dzud."""
import csv
import json
import sys
from collections import Counter
from datetime import date
from pathlib import Path

THRESHOLDS = {  # ZudRisk zone -> snow depth (cm) above which: dzud, moderate (annex 5, 3.3.1 and 3.3.2)
    "mountain": (25.0, 16.0),
    "taiga": (25.0, 16.0),  # not named in the procedure; taken as high mountain and forest steppe
    "forest_steppe": (25.0, 16.0),
    "steppe": (22.0, 11.0),
    "desert": (12.0, 5.0),  # gobi and desert; ZudRisk counts desert steppe here (pipeline.zones)
}
NO_SNOW_CM = 1.0  # indicators.SNOW_MIN_M
UNASSESSED = "unassessed"
ORDER = ["black", "white", "black_moderate", "white_moderate"]  # most severe first; black before white only fixes an order


def zone_thresholds(zone: str) -> tuple[float, float]:
    if zone not in THRESHOLDS:
        raise KeyError(f"no Resolution 286 snow thresholds for zone {zone!r}")
    return THRESHOLDS[zone]


def summer_drought(precip_share: float | None, t_anom: float | None, t_sd: float | None) -> str | None:
    """"drought", "near", None (neither) or UNASSESSED, for a May-August season against its 2001-2020 mean."""
    if precip_share is None or t_anom is None:
        return UNASSESSED
    sd = t_sd or 0.0
    if precip_share <= 0.50 and (t_anom >= 2.0 or (sd > 0 and t_anom > 2 * sd)):
        return "drought"
    if precip_share <= 0.80 and (t_anom >= 1.0 or (sd > 0 and t_anom > sd)):
        return "near"
    return None


def month_flags(depth_cm: float | None, t_anom: float | None, t_sd: float | None, zone: str,
                summer: str | None) -> set[str] | None:
    """The types whose main criteria a soum's month meets; None when depth or temperature is missing."""
    if depth_cm is None or t_anom is None:
        return None
    dzud, moderate = zone_thresholds(zone)
    sd = t_sd or 0.0
    out = set()
    if depth_cm > dzud and (t_anom <= -3.0 or (sd > 0 and t_anom < -sd)):
        out.add("white")
    if depth_cm > moderate:
        out.add("white_moderate")
    if summer in ("drought", "near"):
        if depth_cm < NO_SNOW_CM and t_anom <= -3.0:
            out.add("black")
        if NO_SNOW_CM <= depth_cm <= moderate and t_anom <= -2.0:
            out.add("black_moderate")
    return out


def winter_status(months: dict[str, set[str] | None]) -> tuple[str, list[str]]:
    """The most severe type met in any month and the months it was met in; "none" if every assessed month met
    nothing; UNASSESSED if no month was assessed."""
    assessed = {m: f for m, f in months.items() if f is not None}
    if not assessed:
        return UNASSESSED, []
    for t in ORDER:
        hit = sorted(m for m, f in assessed.items() if t in f)
        if hit:
            return t, hit
    return "none", []


BASE_YEARS = range(2001, 2021)  # calendar years of the long-term mean, every month: 2001-2020, ZudRisk's baseline
SUMMER = ("05", "06", "07", "08")
DERIVED = Path("data/derived")


def _mean_sd(xs: list[float]) -> tuple[float, float]:
    m = sum(xs) / len(xs)
    return m, (sum((x - m) ** 2 for x in xs) / len(xs)) ** 0.5


def anomaly(series: dict[str, float], month: str, year: int, years=BASE_YEARS) -> tuple[float | None, float | None]:
    """A month's value less that calendar month's 2001-2020 mean, and the baseline's population σ."""
    v = series.get(f"{year}{month}")
    base = [series[f"{y}{month}"] for y in years if f"{y}{month}" in series]
    if v is None or len(base) < len(years) // 2:
        return None, None
    m, sd = _mean_sd(base)
    return round(v - m, 3), round(sd, 3)


def summer_share(series_tp: dict[str, float], series_t: dict[str, float], year: int,
                 years=BASE_YEARS) -> tuple[float | None, float | None, float | None]:
    """May-August precipitation as a share of its 2001-2020 mean, the season's temperature anomaly and its σ."""
    def season(y):
        p = [series_tp.get(f"{y}{m}") for m in SUMMER]
        t = [series_t.get(f"{y}{m}") for m in SUMMER]
        return (None, None) if None in p or None in t else (sum(p), sum(t) / len(t))
    now = season(year)
    base = [season(y) for y in years]
    base = [b for b in base if b[0] is not None]
    if now[0] is None or len(base) < len(years) // 2:
        return None, None, None
    p_mean, _ = _mean_sd([b[0] for b in base])
    t_mean, t_sd = _mean_sd([b[1] for b in base])
    share = round(now[0] / p_mean, 3) if p_mean > 0 else None
    return share, round(now[1] - t_mean, 3), round(t_sd, 3)


def main(year: int, as_of: date | None = None, site: Path | None = None, derived: Path | None = None) -> dict[str, dict]:
    """Every soum's status for winter year/year+1 from the months over by as_of; writes the CSV (to derived) and the
    site file (to site). Both default to the live folders."""
    from pipeline import era5, export, indicators, summer, zones
    site, derived = site or export.SITE, derived or DERIVED
    as_of = as_of or indicators.winter_end(year)
    months = indicators.snow_months(year, as_of)
    e5, sm, zone_of = era5.load_era5(), summer.load_summer(), zones.soum_zone()
    out = {}
    for pcode in sorted(zone_of):
        z, e, s = zone_of[pcode], e5.get(pcode), sm.get(pcode)
        summer_cls = summer_drought(*summer_share(s["tp_mm"], s["t2m_c"], year)) if s else UNASSESSED
        by_month, inputs = {}, {}
        for ym in months:
            depth = e["sde"].get(ym) if e else None
            t_anom, t_sd = anomaly(e["t2m"], ym[4:], int(ym[:4])) if e else (None, None)
            depth_cm = None if depth is None else round(depth * 100, 1)
            f = month_flags(depth_cm, t_anom, t_sd, z, summer_cls)
            by_month[ym] = None if f is None else sorted(f, key=ORDER.index)
            inputs[ym] = {"depth_cm": depth_cm, "t_anom": t_anom, "t_sd": t_sd}
        status, hit = winter_status({m: (None if f is None else set(f)) for m, f in by_month.items()})
        out[pcode] = {"status": status, "months": hit, "summer": summer_cls, "by_month": by_month, "inputs": inputs, "zone": z}
    derived.mkdir(parents=True, exist_ok=True)
    with (derived / f"decree286_{year}.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["pcode", "zone", "summer", "status", "months", *months])
        for pc, r in out.items():
            w.writerow([pc, r["zone"], r["summer"] or "", r["status"], " ".join(r["months"]),
                        *("" if r["by_month"][m] is None else " ".join(r["by_month"][m]) or "-" for m in months)])
    (site / f"decree286_{export.label(year)}.json").write_text(
        json.dumps({"as_of": as_of.isoformat(), "months": months, "soums": out}, separators=(",", ":")), encoding="utf-8")
    counts = Counter(r["status"] for r in out.values())
    print(f"{export.label(year)} (to {as_of}): " + ", ".join(f"{k} {counts[k]}" for k in [*ORDER, "none", UNASSESSED] if counts[k]))
    return out


def validate(years: list[int]) -> dict:
    """How the statuses line up with recorded losses (soum-winters with losses, 2011/12 on) and with the official
    lists (pipeline.official), snapshot by snapshot; writes site/data/decree286_validation.json."""
    from pipeline import export, indicators, official
    from pipeline.nso import load_livestock
    from pipeline.score import risk_class
    from pipeline.validate import mortality
    herds = load_livestock()
    tally: dict[str, list[int]] = {}

    def add(key, m):
        t = tally.setdefault(key, [0, 0])
        t[0] += 1
        t[1] += m >= 0.05
    for y in years:
        if y < 2011:
            continue
        rows = json.loads((export.SITE / f"decree286_{export.label(y)}.json").read_text(encoding="utf-8"))["soums"]
        risk = indicators.read_risk(y)
        for pc, r in rows.items():
            m = mortality(herds, pc, y)
            if m is None:
                continue
            add(r["status"], m)
            add("all", m)
            if pc in risk and risk_class(risk[pc]) == 4:
                add("risk_class_4", m)
    res = {k: {"n": n, "loss5": round(h / n, 3)} for k, (n, h) in sorted(tally.items())}
    snaps: dict[tuple, set] = {}
    with official.OUT.open(encoding="utf-8") as f:
        for r in csv.DictReader(f):
            if r["pcode"] and r["category"] != "iron":
                snaps.setdefault((r["winter"], r["as_of"], r["category"]), set()).add(r["pcode"])
    res["official"] = []
    for (w, d, cat), named in sorted(snaps.items()):
        path = export.SITE / f"decree286_{w}.json"
        if not path.exists():
            continue
        ym = d[:4] + d[5:7]
        soums = json.loads(path.read_text(encoding="utf-8"))["soums"]
        want = set(ORDER) if cat == "dzud_any" else {cat}
        flagged = {pc for pc, r in soums.items() if set(r["by_month"].get(ym) or []) & want}
        both = len(named & flagged)
        # white dzud named officially and flagged here as white or moderate: the depth part alone, since NAMEM's
        # white dzud seems not to need the -3 °C month and uses snow measured on pasture
        wide = {pc for pc, r in soums.items() if set(r["by_month"].get(ym) or []) & ({"white", "white_moderate"} if cat == "white" else want)}
        res["official"].append({"winter": w, "as_of": d, "category": cat, "named": len(named), "flagged": len(flagged),
                                "both": both, "both_any": len(named & wide), "recall": round(both / len(named), 3) if named else None,
                                "precision": round(both / len(flagged), 3) if flagged else None})
    (export.SITE / "decree286_validation.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    return res


def check() -> None:
    assert zone_thresholds("taiga") == (25.0, 16.0) and zone_thresholds("desert") == (12.0, 5.0)
    try:
        zone_thresholds("tundra")
        raise AssertionError
    except KeyError as e:
        assert "tundra" in str(e)
    assert summer_drought(0.50, 2.0, 5.0) == "drought" and summer_drought(0.50, 1.0, 5.0) == "near"
    assert summer_drought(0.80, 0.5, 0.4) == "near" and summer_drought(0.81, 3.0, 1.0) is None
    assert summer_drought(0.6, 0.5, 1.0) is None and summer_drought(None, 1.0, 1.0) == UNASSESSED
    assert month_flags(25.0, -3.0, 1.0, "mountain", None) == {"white_moderate"}   # 25 is not above 25
    assert month_flags(25.1, -3.0, 1.0, "mountain", None) == {"white", "white_moderate"}
    assert month_flags(25.1, -1.5, 1.0, "mountain", None) == {"white", "white_moderate"}  # below −1σ
    assert month_flags(0.5, -3.0, 1.0, "steppe", "near") == {"black"}
    assert month_flags(5.0, -2.0, 1.0, "desert", "drought") == {"black_moderate"}      # 1 ≤ depth ≤ 5
    assert month_flags(0.5, -3.0, 1.0, "steppe", None) == set()
    assert month_flags(30.0, -4.0, 1.0, "steppe", UNASSESSED) == {"white", "white_moderate"}
    assert month_flags(None, -4.0, 1.0, "steppe", None) is None
    assert winter_status({}) == (UNASSESSED, [])
    assert winter_status({"202512": {"white_moderate"}, "202601": {"black", "white_moderate"}}) == ("black", ["202601"])
    assert winter_status({"202512": set(), "202601": None}) == ("none", [])
    assert winter_status({"202512": None}) == (UNASSESSED, [])
    s = {f"{y}12": -20.0 for y in range(2001, 2021)}
    s["202512"] = -24.0
    assert anomaly(s, "12", 2025) == (-4.0, 0.0)            # constant baseline: σ 0, −3 °C rule still applies
    assert month_flags(30.0, -4.0, 0.0, "steppe", None) == {"white", "white_moderate"}
    tp = {f"{y}{m}": 25.0 for y in range(2001, 2021) for m in ("05", "06", "07", "08")}
    tp.update({f"2025{m}": 10.0 for m in ("05", "06", "07", "08")})
    t = {k: 15.0 for k in tp}
    t.update({f"2025{m}": 17.5 for m in ("05", "06", "07", "08")})
    share, ta, sd = summer_share(tp, t, 2025)
    assert share == 0.4 and ta == 2.5 and summer_drought(share, ta, sd) == "drought"
    print("decree286 check: ok")


def run_all() -> None:
    from pipeline import hindcast
    for y in hindcast.shown():
        main(y)
    print(json.dumps(validate(hindcast.WINTERS), indent=1, ensure_ascii=False))


if __name__ == "__main__":
    check() if "--check" in sys.argv else run_all()
