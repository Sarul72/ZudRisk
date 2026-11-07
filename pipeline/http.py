"""Stdlib HTTP helpers with a polite User-Agent and retry on rate limits and server errors."""
import http.cookiejar
import json
import netrc
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

USER_AGENT = "ZudRisk-research/0.1"
TRIES = 3
BACKOFF_S = 5


EDL_HOST = "urs.earthdata.nasa.gov"
_edl_opener = None


def _open(req: urllib.request.Request, opener=None) -> bytes:
    return _open_typed(req, opener)[0]


def _open_typed(req: urllib.request.Request, opener=None) -> tuple[bytes, str]:
    for attempt in range(1, TRIES + 1):
        try:
            with (opener or urllib.request.build_opener()).open(req, timeout=180) as resp:
                return resp.read(), resp.headers.get("Content-Type", "")
        except urllib.error.HTTPError as e:
            if attempt == TRIES or not (e.code == 429 or e.code >= 500):
                raise
        except (urllib.error.URLError, TimeoutError):
            if attempt == TRIES:
                raise
        time.sleep(BACKOFF_S)
    raise AssertionError("unreachable")


def get_json(url: str) -> dict:
    return json.loads(_open(urllib.request.Request(url, headers={"User-Agent": USER_AGENT})))


def post_json(url: str, body: dict) -> dict:
    req = urllib.request.Request(
        url,
        data=json.dumps(body).encode(),
        headers={"User-Agent": USER_AGENT, "Content-Type": "application/json"},
    )
    return json.loads(_open(req))


def check_payload(body: bytes, content_type: str, url: str) -> bytes:
    """Earthdata answers a failed login with an HTML page; never let it pass as a data file."""
    if content_type.startswith("text/html"):
        host = urllib.parse.urlparse(url).hostname
        raise RuntimeError(f"Earthdata login failed for {host}: check ~/.netrc and approved applications")
    return body


def _edl() -> urllib.request.OpenerDirector:
    """Opener that answers the Earthdata Login redirect with the ~/.netrc credentials and keeps its cookies."""
    global _edl_opener
    if _edl_opener is None:
        auth = netrc.netrc().authenticators(EDL_HOST)
        if auth is None:
            raise RuntimeError(f"no {EDL_HOST} entry in ~/.netrc")
        mgr = urllib.request.HTTPPasswordMgrWithDefaultRealm()
        mgr.add_password(None, f"https://{EDL_HOST}", auth[0], auth[2])
        _edl_opener = urllib.request.build_opener(
            urllib.request.HTTPBasicAuthHandler(mgr),
            urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()),
        )
    return _edl_opener


def get_bytes_auth(url: str, opener=None) -> bytes:
    try:
        body, ctype = _open_typed(urllib.request.Request(url, headers={"User-Agent": USER_AGENT}), opener or _edl())
    except urllib.error.HTTPError as e:
        if e.code in (401, 403):
            raise RuntimeError(f"Earthdata login failed for {EDL_HOST} (HTTP {e.code} on {url}): "
                               "check ~/.netrc and approved applications") from e
        raise
    return check_payload(body, ctype, url)


def cached(path: Path, get) -> Path:
    """Fetch once into path; a download cut short leaves no file, so a later run never trusts half a granule."""
    if not path.exists():
        part = path.with_name(path.name + ".part")
        try:
            part.write_bytes(get())
            part.rename(path)
        finally:
            part.unlink(missing_ok=True)
    return path


def download(url: str, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(_open(urllib.request.Request(url, headers={"User-Agent": USER_AGENT})))
    return path


def check() -> None:
    try:
        check_payload(b"<html>Earthdata Login</html>", "text/html; charset=utf-8", "https://x.nasa.gov/a.nc4")
        raise AssertionError("an HTML login page must not pass as data")
    except RuntimeError as e:
        assert "~/.netrc" in str(e) and "x.nasa.gov" in str(e), e
    assert check_payload(b"\x89HDF", "application/x-netcdf4", "https://x/a.nc4") == b"\x89HDF"
    class Refused:
        def open(self, req, timeout=None):
            raise urllib.error.HTTPError(req.full_url, 401, "Unauthorized", {}, None)
    try:
        get_bytes_auth("https://data.gesdisc.earthdata.nasa.gov/x.nc4", opener=Refused())
        raise AssertionError("a 401 must name ~/.netrc")
    except RuntimeError as e:
        assert "~/.netrc" in str(e), e
    import tempfile
    with tempfile.TemporaryDirectory() as d:
        target = Path(d) / "a.nc4"
        def broken() -> bytes:
            raise TimeoutError("cut mid-download")
        try:
            cached(target, broken)
        except TimeoutError:
            pass
        assert not target.exists() and not list(Path(d).iterdir()), list(Path(d).iterdir())
        assert cached(target, lambda: b"\x89HDF").read_bytes() == b"\x89HDF"
    print("http check: ok")


if __name__ == "__main__":
    import sys
    if "--check" in sys.argv:
        check()
