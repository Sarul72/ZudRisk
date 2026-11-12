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
import sys

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
    print("decree286 check: ok")


if __name__ == "__main__":
    check() if "--check" in sys.argv else main()
