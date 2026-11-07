"""Stdlib HTTP helpers with a polite User-Agent and retry on rate limits and server errors."""
import json
import time
import urllib.error
import urllib.request
from pathlib import Path

USER_AGENT = "ZudRisk-research/0.1"
TRIES = 3
BACKOFF_S = 5


def _open(req: urllib.request.Request) -> bytes:
    for attempt in range(1, TRIES + 1):
        try:
            with urllib.request.urlopen(req, timeout=180) as resp:
                return resp.read()
        except urllib.error.HTTPError as e:
            if attempt == TRIES or not (e.code == 429 or e.code >= 500):
                raise
        except urllib.error.URLError:
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


def download(url: str, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(_open(urllib.request.Request(url, headers={"User-Agent": USER_AGENT})))
    return path
