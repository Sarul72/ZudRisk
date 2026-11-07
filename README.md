# ZudRisk

An open, reproducible estimate of dzud (зуд) risk for every soum of Mongolia, built from public
data: NASA POWER winter temperature, NSO livestock counts and losses, OCHA COD-AB soum boundaries.
Research hindcast, not a warning. Design: `docs/superpowers/specs/2026-11-08-zudrisk-design.md`.

## Run

Needs `uv`. No account or key: every v0.1 source is public.

```bash
uv sync
uv run python -m pipeline.boundaries          # OCHA COD-AB soums -> data/derived/soums.geojson
uv run python -m pipeline.nso                 # NSO herds and losses -> data/derived/livestock.csv
uv run python -m pipeline.power               # NASA POWER T2M 2001-2024 -> data/derived/t2m_monthly.csv
uv run python -m pipeline.indicators --winter 2023
uv run python -m pipeline.validate --winter 2023
uv run python -m pipeline.export --winter 2023
python3 -m http.server -d site 8765           # open http://localhost:8765
```

Self-checks (no network): `uv run python -m pipeline.<step> --check` for every step except `score`,
which runs its check with no flag.
