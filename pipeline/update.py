"""The monthly outlook update, safe to run every day: refresh ERA5-Land and the NSO census, then publish the newest
outlook stage whose data has landed. Out of season, or with that stage already published, it does nothing.

A month's ERA5-Land lands about five days after it ends, so the stage named by last month is tried first, and the
one before it if last month has not landed yet."""
import json
import sys
from datetime import date

from pipeline.export import SITE
from pipeline.outlook import STAGE_OF_MONTH

STAGE_MONTHS = sorted(STAGE_OF_MONTH)  # 1, 2, 3, 10, 11, 12


def candidates(today: date, published: str | None) -> list[str]:
    """Stages ('YYYY-MM' of their last data month) worth trying today, newest first: the last two months that end
    an outlook stage, newer than the published one."""
    out = []
    for back in (1, 2):
        y, m = divmod(today.year * 12 + today.month - 1 - back, 12)
        through = f"{y}-{m + 1:02d}"
        if m + 1 in STAGE_MONTHS and (published is None or through > published):
            out.append(through)
    return out


def published() -> str | None:
    path = SITE / "outlook.json"
    return json.loads(path.read_text())["data_through"] if path.exists() else None


def main(today: date | None = None) -> None:
    today = today or date.today()
    todo = candidates(today, published())
    if not todo:
        print(f"{today}: nothing to update (published {published()})")
        return
    from pipeline import era5, nso, outlook  # imported here so an off-season run touches no data
    era5.main()
    nso.main()
    have = outlook.available()
    for through in todo:
        missing = outlook.missing_months(*outlook.parse_through(through), have)
        if missing:
            print(f"{today}: {through} not ready; not published: {', '.join(missing)}")
            continue
        outlook.main(through)
        print(f"{today}: published the outlook through {through}")
        return


def check() -> None:
    assert candidates(date(2026, 12, 7), "2026-10") == ["2026-11"], "October's stage is out already"
    assert candidates(date(2026, 12, 2), "2026-10") == ["2026-11"]
    assert candidates(date(2026, 11, 8), "2026-10") == [], "nothing newer than what is out"
    assert candidates(date(2026, 11, 2), "2026-03") == ["2026-10"], "a new winter starts at its October stage"
    assert candidates(date(2027, 1, 3), "2026-11") == ["2026-12"]
    assert candidates(date(2027, 1, 3), "2026-10") == ["2026-12", "2026-11"], "a late month still leaves the one before"
    assert candidates(date(2027, 4, 6), "2027-02") == ["2027-03"]
    assert candidates(date(2027, 5, 6), "2027-03") == [], "April ends no stage"
    assert candidates(date(2026, 10, 3), "2026-03") == [], "September ends no stage"
    assert candidates(date(2026, 11, 2), None) == ["2026-10"]
    print("update check: ok")


if __name__ == "__main__":
    check() if "--check" in sys.argv else main()
