# ZudRisk

An open, reproducible estimate of dzud (зуд) risk for every soum of Mongolia, built from public
data: NASA POWER winter temperature, NSO livestock counts and losses, OCHA COD-AB soum boundaries.
Research hindcast, not a warning. Design: `docs/superpowers/specs/2026-11-08-zudrisk-design.md`.

## Run

Needs `uv`. v0.1 sources are public. From v0.2 the snow (GLDAS) and NDVI (MODIS) steps need a free
NASA Earthdata Login in `~/.netrc` (`machine urs.earthdata.nasa.gov login ... password ...`, mode 600),
with the "NASA GESDISC DATA ARCHIVE" application approved in the Earthdata profile.

```bash
uv sync
uv run python -m pipeline.boundaries          # OCHA COD-AB soums -> data/derived/soums.geojson
uv run python -m pipeline.nso                 # NSO herds and losses -> data/derived/livestock.csv
uv run python -m pipeline.power               # NASA POWER T2M 2001-2024 -> data/derived/t2m_monthly.csv
uv run python -m pipeline.gldas               # GLDAS-2.1 snow depth, Nov-Mar 2001/02-2023/24 (Earthdata)
uv run python -m pipeline.ndvi                # MODIS MOD13C2 NDVI, Jul-Aug 2001-2023 (Earthdata)
uv run python -m pipeline.hindcast            # score, validate and export all six winters + pooled
python3 -m http.server -d site 8765           # open http://localhost:8765
```

Self-checks (no network): `uv run python -m pipeline.<step> --check` for every step except `score`,
which runs its check with no flag.
