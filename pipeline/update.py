"""The monthly outlook update, safe to run every day: refresh ERA5-Land and the NSO census, then publish the newest
outlook stage whose data has landed. Out of season, or with that stage already published, it does nothing.

A month's ERA5-Land lands about five days after it ends, so the stage named by last month is tried first, and the
one before it if last month has not landed yet.

After it publishes a stage it commits site/data and pushes it, so GitHub Pages serves the new stage. --no-push
skips that. A folder that is not a git checkout, or has no remote, is left alone."""
import json
import subprocess
import sys
from datetime import date
from pathlib import Path

from pipeline.export import SITE
from pipeline.outlook import STAGE_OF_MONTH

STAGE_MONTHS = sorted(STAGE_OF_MONTH)  # 1, 2, 3, 10, 11, 12
# the sources refreshed before a stage, each a pipeline module with main(); summer is the May-August before the
# winter, which Resolution 286's black dzud needs (fetched once a year, when its file name changes)
REFRESH = ("era5", "summer", "nso")


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
    return json.loads(path.read_text(encoding="utf-8"))["data_through"] if path.exists() else None


def git(*args: str, cwd: Path = Path(".")) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, encoding="utf-8")


def push_site(message: str, cwd: Path = Path("."), push: bool = True) -> str:
    """Commit only site/data and push it. Returns what happened, in a few words."""
    if git("rev-parse", "--is-inside-work-tree", cwd=cwd).returncode != 0:
        return "not a git checkout; nothing committed"
    git("add", "--", "site/data", cwd=cwd)
    if git("diff", "--cached", "--quiet", "--", "site/data", cwd=cwd).returncode == 0:
        return "site/data unchanged; nothing committed"
    done = git("commit", "-m", message, "--", "site/data", cwd=cwd)
    if done.returncode != 0:
        raise RuntimeError(f"git commit failed: {done.stderr.strip()}")
    if not push:
        return "committed; not pushed (--no-push)"
    if not git("remote", cwd=cwd).stdout.strip():
        return "committed; no remote to push to"
    sent = git("push", cwd=cwd)
    if sent.returncode != 0:
        raise RuntimeError(f"git push failed: {sent.stderr.strip()}")
    return "committed and pushed"


def main(today: date | None = None, push: bool = True) -> None:
    today = today or date.today()
    todo = candidates(today, published())
    if not todo:
        print(f"{today}: nothing to update (published {published()})")
        return
    import importlib
    from pipeline import outlook  # imported here so an off-season run touches no data
    for name in REFRESH:
        importlib.import_module(f"pipeline.{name}").main()
    have = outlook.available()
    for through in todo:
        missing = outlook.missing_months(*outlook.parse_through(through), have)
        if missing:
            print(f"{today}: {through} not ready; not published: {', '.join(missing)}")
            continue
        outlook.main(through)
        print(f"{today}: published the outlook through {through}")
        print(f"{today}: {push_site(f'Outlook through {through}', push=push)}")
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
    assert REFRESH == ("era5", "summer", "nso"), "the summer before the winter feeds Resolution 286's black dzud"
    check_push()
    print("update check: ok")


def check_push() -> None:
    """push_site in a throwaway repository with a bare remote: only site/data is committed, and it reaches the remote."""
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        root, remote = Path(tmp) / "work", Path(tmp) / "remote.git"
        assert push_site("x", cwd=Path(tmp)) == "not a git checkout; nothing committed"
        git("init", "-q", "--bare", str(remote), cwd=Path(tmp))
        git("init", "-q", "-b", "main", str(root), cwd=Path(tmp))
        for k, v in (("user.name", "check"), ("user.email", "check@example.invalid")):
            git("config", k, v, cwd=root)
        (root / "site/data").mkdir(parents=True)
        (root / "site/data/outlook.json").write_text("{}", encoding="utf-8")
        (root / "other.txt").write_text("not mine to commit", encoding="utf-8")
        assert push_site("first", cwd=root, push=False) == "committed; not pushed (--no-push)"
        assert git("ls-files", cwd=root).stdout.split() == ["site/data/outlook.json"], "only site/data is committed"
        assert push_site("again", cwd=root) == "site/data unchanged; nothing committed"
        (root / "site/data/outlook.json").write_text('{"data_through": "2026-11"}', encoding="utf-8")
        assert push_site("second", cwd=root) == "committed; no remote to push to"
        git("remote", "add", "origin", str(remote), cwd=root)
        git("push", "-q", "-u", "origin", "main", cwd=root)
        (root / "site/data/outlook.json").write_text('{"data_through": "2026-12"}', encoding="utf-8")
        assert push_site("third", cwd=root) == "committed and pushed"
        assert git("log", "-1", "--format=%s", "main", cwd=remote).stdout.strip() == "third", "the remote has it"


if __name__ == "__main__":
    check() if "--check" in sys.argv else main(push="--no-push" not in sys.argv)
